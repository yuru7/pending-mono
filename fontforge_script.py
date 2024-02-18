#!fontforge --lang=py -script

import configparser
import math
import os
import shutil
import sys

import fontforge
import psMat

# iniファイルを読み込む
settings = configparser.ConfigParser()
settings.read("build.ini", encoding="utf-8")

VERSION = settings.get("DEFAULT", "VERSION")
FONT_NAME = settings.get("DEFAULT", "FONT_NAME")
JP_FONT = settings.get("DEFAULT", "JP_FONT")
ENG_FONT = settings.get("DEFAULT", "ENG_FONT")
SOURCE_FONTS_DIR = settings.get("DEFAULT", "SOURCE_FONTS_DIR")
BUILD_FONTS_DIR = settings.get("DEFAULT", "BUILD_FONTS_DIR")
VENDER_NAME = settings.get("DEFAULT", "VENDER_NAME")
FONTFORGE_PREFIX = settings.get("DEFAULT", "FONTFORGE_PREFIX")
IDEOGRAPHIC_SPACE = settings.get("DEFAULT", "IDEOGRAPHIC_SPACE")
HALF_WIDTH_STR = settings.get("DEFAULT", "HALF_WIDTH_STR")
INVISIBLE_ZENKAKU_SPACE_STR = settings.get("DEFAULT", "INVISIBLE_ZENKAKU_SPACE_STR")
JPDOC_STR = settings.get("DEFAULT", "JPDOC_STR")
NERD_FONTS_STR = settings.get("DEFAULT", "NERD_FONTS_STR")
# SLASHED_ZERO_STR = settings.get("DEFAULT", "SLASHED_ZERO_STR")
EM_ASCENT = int(settings.get("DEFAULT", "EM_ASCENT"))
EM_DESCENT = int(settings.get("DEFAULT", "EM_DESCENT"))
OS2_ASCENT = int(settings.get("DEFAULT", "OS2_ASCENT"))
OS2_DESCENT = int(settings.get("DEFAULT", "OS2_DESCENT"))
HALF_WIDTH_12 = int(settings.get("DEFAULT", "HALF_WIDTH_12"))
FULL_WIDTH_35 = int(settings.get("DEFAULT", "FULL_WIDTH_35"))

COPYRIGHT = """[Commit Mono]
Copyright (c) Eigil Nikolajsen https://github.com/eigilnikolajsen/commit-mono

[BIZ UDGothic]
Copyright 2022 The BIZ UDGothic Project Authors https://github.com/googlefonts/morisawa-biz-ud-gothic

[Pending Mono]
Copyright 2022 Yuko Otawara
"""  # noqa: E501

options = {}
nerd_font = None


def main():
    # オプション判定
    get_options()
    if options.get("unknown-option"):
        usage()
        return

    # buildディレクトリを作成する
    if os.path.exists(BUILD_FONTS_DIR) and not options.get("do-not-delete-build-dir"):
        shutil.rmtree(BUILD_FONTS_DIR)
        os.mkdir(BUILD_FONTS_DIR)
    if not os.path.exists(BUILD_FONTS_DIR):
        os.mkdir(BUILD_FONTS_DIR)

    generate_font("Regular", "400-Regular", "Regular")
    generate_font("Bold", "700-Regular", "Bold")
    generate_font("Regular", "400-Italic", "Italic", italic=True)
    generate_font("Bold", "700-Italic", "BoldItalic", italic=True)


def get_options():
    """オプションを取得する"""

    global options

    # オプションなしの場合は何もしない
    if len(sys.argv) == 1:
        return

    for arg in sys.argv[1:]:
        # オプション判定
        if arg == "--do-not-delete-build-dir":
            options["do-not-delete-build-dir"] = True
        elif arg == "--invisible-zenkaku-space":
            options["invisible-zenkaku-space"] = True
        elif arg == "--half-width":
            options["half-width"] = True
        elif arg == "--jpdoc":
            options["jpdoc"] = True
        elif arg == "--nerd-font":
            options["nerd-font"] = True
        else:
            options["unknown-option"] = True
            return


def usage():
    print(
        f"Usage: {sys.argv[0]} "
        "[--invisible-zenkaku-space] [--half-width] [--jpdoc] [--nerd-font]"
    )


def generate_font(jp_style, eng_style, merged_style, italic=False):
    print(f"=== Generate {merged_style} ===")

    # 合成するフォントを開く
    jp_font, eng_font = open_fonts(jp_style, eng_style)

    # fonttools merge エラー対処
    altuni_to_entity(jp_font)

    # 日本語文書に頻出する記号を英語フォントから削除する
    if options.get("jpdoc"):
        remove_jpdoc_symbols(eng_font)

    # 重複するグリフを削除する
    delete_duplicate_glyphs(jp_font, eng_font)

    # フォントのEMを1000に変換する
    # jp_font は既に1000なので eng_font のみ変換する
    em_1000(jp_font)

    # いくつかのグリフ形状に調整を加える
    adjust_some_glyph(jp_font)

    # 日本語グリフの斜体を生成する
    if italic:
        transform_italic_glyphs(jp_font)

    # jp_fontで半角幅(500)のグリフの幅を3:5になるよう調整する
    width_600_or_1000(jp_font)

    # 3:5幅版との差分を調整する
    if options.get("half-width"):
        # 1:2 幅にする
        transform_half_width(jp_font, eng_font)

    # GSUBテーブルを削除する (ひらがな等の全角文字が含まれる行でリガチャが解除される対策)
    remove_lookups(jp_font)

    # 全角スペースを可視化する
    if not options.get("invisible-zenkaku-space"):
        visualize_zenkaku_space(jp_font, eng_font)

    # Nerd Fontのグリフを追加する
    if options.get("nerd-font"):
        add_nerd_font_glyphs(jp_font, eng_font)

    # オプション毎の修飾子を追加する
    variant = HALF_WIDTH_STR if options.get("half-width") else ""
    variant += (
        INVISIBLE_ZENKAKU_SPACE_STR if options.get("invisible-zenkaku-space") else ""
    )
    variant += JPDOC_STR if options.get("jpdoc") else ""
    variant += NERD_FONTS_STR if options.get("nerd-font") else ""
    # variant += SLASHED_ZERO_STR if options.get("slashed-zero") else ""

    # メタデータを編集する
    edit_meta_data(eng_font, merged_style, variant)
    edit_meta_data(jp_font, merged_style, variant)

    # ttfファイルに保存
    generate_filename_part = f"{BUILD_FONTS_DIR}/{FONTFORGE_PREFIX}{FONT_NAME.replace(' ', '')}{variant}-{merged_style}"
    eng_font.generate(f"{generate_filename_part}-eng.ttf")
    jp_font.generate(f"{generate_filename_part}-jp.ttf")

    # ttfを閉じる
    jp_font.close()
    eng_font.close()


def open_fonts(jp_style: str, eng_style: str):
    """フォントを開く"""
    jp_font = fontforge.open(
        f"{SOURCE_FONTS_DIR}/{JP_FONT.replace('{style}', jp_style)}"
    )
    eng_font = fontforge.open(
        f"{SOURCE_FONTS_DIR}/{ENG_FONT.replace('{style}', eng_style)}"
    )
    # フォント参照を解除する
    jp_font.unlinkReferences()
    eng_font.unlinkReferences()
    return jp_font, eng_font


def altuni_to_entity(jp_font):
    """Alternate Unicodeで透過的に参照して表示している箇所を実体のあるグリフに変換する"""
    for glyph in jp_font.glyphs():
        if glyph.altuni is not None:
            # 以下形式のタプルで返ってくる
            # (unicode-value, variation-selector, reserved-field)
            # 第3フィールドは常に0なので無視
            altunis = glyph.altuni

            # variation-selectorがなく (-1)、透過的にグリフを参照しているものは実体のグリフに変換する
            before_altuni = ""
            for altuni in altunis:
                # 直前のaltuniと同じ場合はスキップ
                if altuni[1] == -1 and before_altuni != ",".join(map(str, altuni)):
                    glyph.altuni = None
                    copy_target_unicode = altuni[0]
                    try:
                        copy_target_glyph = jp_font.createChar(
                            copy_target_unicode,
                            f"uni{hex(copy_target_unicode).replace('0x', '').upper()}copy",
                        )
                    except Exception:
                        copy_target_glyph = jp_font[copy_target_unicode]
                    copy_target_glyph.clear()
                    copy_target_glyph.width = glyph.width
                    # copy_target_glyph.addReference(glyph.glyphname)
                    jp_font.selection.select(glyph.glyphname)
                    jp_font.copy()
                    jp_font.selection.select(copy_target_glyph.glyphname)
                    jp_font.paste()
                before_altuni = ",".join(map(str, altuni))

    return jp_font


def adjust_some_glyph(jp_font):
    """いくつかのグリフ形状に調整を加える"""
    # 全角括弧の開きを広くする
    full_width = jp_font[0x3042].width
    adjust_length = round(full_width / 6)
    for glyph_name in [0xFF08, 0xFF3B, 0xFF5B]:
        glyph = jp_font[glyph_name]
        glyph.transform(psMat.translate(-adjust_length, 0))
        glyph.width = full_width
    for glyph_name in [0xFF09, 0xFF3D, 0xFF5D]:
        glyph = jp_font[glyph_name]
        glyph.transform(psMat.translate(adjust_length, 0))
        glyph.width = full_width


def em_1000(font):
    """フォントのEMを1000に変換する"""
    font.em = EM_ASCENT + EM_DESCENT


def delete_duplicate_glyphs(jp_font, eng_font):
    """jp_fontとeng_fontのグリフを比較し、重複するグリフを削除する"""

    eng_font.selection.none()
    jp_font.selection.none()

    for glyph in jp_font.glyphs("encoding"):
        try:
            if glyph.isWorthOutputting() and glyph.unicode > 0:
                eng_font.selection.select(("more", "unicode"), glyph.unicode)
        except ValueError:
            # Encoding is out of range のときは継続する
            continue
    for glyph in eng_font.selection.byGlyphs:
        # if glyph.isWorthOutputting():
        jp_font.selection.select(("more", "unicode"), glyph.unicode)
    for glyph in jp_font.selection.byGlyphs:
        glyph.clear()

    jp_font.selection.none()
    eng_font.selection.none()


def remove_lookups(font):
    """GSUB, GPOSテーブルを削除する"""
    for lookup in list(font.gsub_lookups) + list(font.gpos_lookups):
        font.removeLookup(lookup)


def transform_italic_glyphs(font):
    # 斜体の傾き
    ITALIC_SLOPE = 9
    # 傾きを設定する
    font.italicangle = -ITALIC_SLOPE
    # 全グリフを斜体に変換
    for glyph in font.glyphs():
        glyph.transform(psMat.skew(ITALIC_SLOPE * math.pi / 180))


def remove_jpdoc_symbols(eng_font):
    """日本語文書に頻出する記号を削除する"""
    eng_font.selection.none()
    # § (U+00A7)
    eng_font.selection.select(("more", "unicode"), 0x00A7)
    # ± (U+00B1)
    eng_font.selection.select(("more", "unicode"), 0x00B1)
    # ¶ (U+00B6)
    eng_font.selection.select(("more", "unicode"), 0x00B6)
    # ÷ (U+00F7)
    eng_font.selection.select(("more", "unicode"), 0x00F7)
    # × (U+00D7)
    eng_font.selection.select(("more", "unicode"), 0x00D7)
    # ⇒ (U+21D2)
    eng_font.selection.select(("more", "unicode"), 0x21D2)
    # ⇔ (U+21D4)
    eng_font.selection.select(("more", "unicode"), 0x21D4)
    # ■-□ (U+25A0-U+25A1)
    eng_font.selection.select(("more", "ranges"), 0x25A0, 0x25A1)
    # ▲-△ (U+25B2-U+25B3)
    eng_font.selection.select(("more", "ranges"), 0x25A0, 0x25B3)
    # ▼-▽ (U+25BC-U+25BD)
    eng_font.selection.select(("more", "ranges"), 0x25BC, 0x25BD)
    # ◆-◇ (U+25C6-U+25C7)
    eng_font.selection.select(("more", "ranges"), 0x25C6, 0x25C7)
    # ○ (U+25CB)
    eng_font.selection.select(("more", "unicode"), 0x25CB)
    # ◎-● (U+25CE-U+25CF)
    eng_font.selection.select(("more", "ranges"), 0x25CE, 0x25CF)
    # ◥ (U+25E5)
    eng_font.selection.select(("more", "unicode"), 0x25E5)
    # ◯ (U+25EF)
    eng_font.selection.select(("more", "unicode"), 0x25EF)
    # √ (U+221A)
    eng_font.selection.select(("more", "unicode"), 0x221A)
    # ∞ (U+221E)
    eng_font.selection.select(("more", "unicode"), 0x221E)
    # ‐ (U+2010)
    eng_font.selection.select(("more", "unicode"), 0x2010)
    # ‘-‚ (U+2018-U+201A)
    eng_font.selection.select(("more", "ranges"), 0x2018, 0x201A)
    # “-„ (U+201C-U+201E)
    eng_font.selection.select(("more", "ranges"), 0x201C, 0x201E)
    # †-‡ (U+2020-U+2021)
    eng_font.selection.select(("more", "ranges"), 0x2020, 0x2021)
    # … (U+2026)
    eng_font.selection.select(("more", "unicode"), 0x2026)
    # ‰ (U+2030)
    eng_font.selection.select(("more", "unicode"), 0x2030)
    # ←-↓ (U+2190-U+2193)
    eng_font.selection.select(("more", "ranges"), 0x2190, 0x2193)
    # ∀ (U+2200)
    eng_font.selection.select(("more", "unicode"), 0x2200)
    # ∂-∃ (U+2202-U+2203)
    eng_font.selection.select(("more", "ranges"), 0x2202, 0x2203)
    # ∈ (U+2208)
    eng_font.selection.select(("more", "unicode"), 0x2208)
    # ∋ (U+220B)
    eng_font.selection.select(("more", "unicode"), 0x220B)
    # ∑ (U+2211)
    eng_font.selection.select(("more", "unicode"), 0x2211)
    # ∥ (U+2225)
    eng_font.selection.select(("more", "unicode"), 0x2225)
    # ∧-∬ (U+2227-U+222C)
    eng_font.selection.select(("more", "ranges"), 0x2227, 0x222C)
    # ≠-≡ (U+2260-U+2261)
    eng_font.selection.select(("more", "ranges"), 0x2260, 0x2261)
    # ⊂-⊃ (U+2282-U+2283)
    eng_font.selection.select(("more", "ranges"), 0x2282, 0x2283)
    # ⊆-⊇ (U+2286-U+2287)
    eng_font.selection.select(("more", "ranges"), 0x2286, 0x2287)
    # ─-╿ (Box Drawing) (U+2500-U+257F)
    eng_font.selection.select(("more", "ranges"), 0x2500, 0x257F)
    for glyph in eng_font.selection.byGlyphs:
        if glyph.isWorthOutputting():
            glyph.clear()
    eng_font.selection.none()


def width_600_or_1000(jp_font):
    """半角幅か全角幅になるように変換する。"""
    half_width = 600
    full_width = 1000
    for glyph in jp_font.glyphs():
        if 0 < glyph.width <= half_width + 20:
            # グリフ位置を調整してから幅を設定
            glyph.transform(psMat.translate((half_width - glyph.width) / 2, 0))
            glyph.width = half_width
        elif half_width < glyph.width < full_width:
            # グリフ位置を調整してから幅を設定
            glyph.transform(psMat.translate((full_width - glyph.width) / 2, 0))
            glyph.width = full_width
        # 600の場合はそのまま


def transform_half_width(jp_font, eng_font):
    """1:2幅になるように変換する。既に3:5幅になっていることを前提とする。"""
    before_width_eng = eng_font[0x0030].width
    after_width_eng = HALF_WIDTH_12
    # グリフそのものは 540 幅相当で縮小し、最終的に HALF_WIDTH_12 の幅を設定する
    x_scale = 540 / before_width_eng
    for glyph in eng_font.glyphs():
        if glyph.width > 0:
            # リガチャ考慮
            after_width_eng_multiply = after_width_eng * round(glyph.width / 600)
            # 縮小
            glyph.transform(psMat.scale(x_scale, 1))
            # 幅を設定
            glyph.transform(
                psMat.translate((after_width_eng_multiply - glyph.width) / 2, 0)
            )
            glyph.width = after_width_eng_multiply

    for glyph in jp_font.glyphs():
        if glyph.width == 600:
            # 英数字グリフと同じ幅にする
            glyph.transform(psMat.translate((after_width_eng - glyph.width) / 2, 0))
            glyph.width = after_width_eng
        elif glyph.width == 1000:
            # 全角は after_width_eng の倍の幅にする
            glyph.transform(psMat.translate((after_width_eng * 2 - glyph.width) / 2, 0))
            glyph.width = after_width_eng * 2


def visualize_zenkaku_space(jp_font, eng_font):
    """全角スペースを可視化する"""
    # 全角スペースの差し替え
    jp_font[0x3000].clear()
    jp_font.mergeFonts(fontforge.open(f"{SOURCE_FONTS_DIR}/{IDEOGRAPHIC_SPACE}"))


def add_nerd_font_glyphs(jp_font, eng_font):
    """Nerd Fontのグリフを追加する"""
    global nerd_font
    # Nerd Fontのグリフを追加する
    if nerd_font is None:
        nerd_font = fontforge.open(
            f"{SOURCE_FONTS_DIR}/nerd-fonts/SymbolsNerdFont-Regular.ttf"
        )
        nerd_font.em = EM_ASCENT + EM_DESCENT
        glyph_names = set()
        for nerd_glyph in nerd_font.glyphs():
            # postテーブルでのグリフ名重複対策
            # fonttools merge で合成した後、MacOSで `'post'テーブルの使用性` エラーが発生することへの対処
            if nerd_glyph.glyphname in glyph_names:
                nerd_glyph.glyphname = f"{nerd_glyph.glyphname}-{nerd_glyph.encoding}"
            glyph_names.add(nerd_glyph.glyphname)
            half_width = eng_font[0x0030].width
            # Powerline Symbols の調整
            if 0xE0B0 <= nerd_glyph.unicode <= 0xE0D4:
                # なぜかズレている右付きグリフの個別調整 (EM 1000 に変更した後を想定して調整)
                original_width = nerd_glyph.width
                if nerd_glyph.unicode == 0xE0B2:
                    nerd_glyph.transform(psMat.translate(-353, 0))
                elif nerd_glyph.unicode == 0xE0B6:
                    nerd_glyph.transform(psMat.translate(-414, 0))
                elif nerd_glyph.unicode == 0xE0C5:
                    nerd_glyph.transform(psMat.translate(-137, 0))
                elif nerd_glyph.unicode == 0xE0C7:
                    nerd_glyph.transform(psMat.translate(-214, 0))
                elif nerd_glyph.unicode == 0xE0D4:
                    nerd_glyph.transform(psMat.translate(-314, 0))
                nerd_glyph.width = original_width
                # 位置と幅合わせ
                if nerd_glyph.width < half_width:
                    # 幅が狭いグリフは中央寄せとみなして調整する
                    nerd_glyph.transform(
                        psMat.translate((half_width - nerd_glyph.width) / 2, 0)
                    )
                elif nerd_glyph.width > half_width:
                    # 幅が広いグリフは縮小して調整する
                    nerd_glyph.transform(psMat.scale(half_width / nerd_glyph.width, 1))
                # グリフの高さ・位置を調整する
                nerd_glyph.transform(psMat.scale(1, 1.21))
                nerd_glyph.transform(psMat.translate(0, -24))
            elif nerd_glyph.width < 600:
                # 幅が狭いグリフは中央寄せとみなして調整する
                nerd_glyph.transform(
                    psMat.translate((half_width - nerd_glyph.width) / 2, 0)
                )
            # 幅を設定
            nerd_glyph.width = half_width
    # 日本語フォントにマージするため、既に存在する場合は削除する
    for nerd_glyph in nerd_font.glyphs():
        if nerd_glyph.unicode != -1:
            # 既に存在する場合は削除する
            try:
                jp_font[nerd_glyph.unicode].clear()
            except Exception:
                pass
            try:
                eng_font[nerd_glyph.unicode].clear()
            except Exception:
                pass
    jp_font.mergeFonts(nerd_font)


def edit_meta_data(font, weight: str, variant: str):
    """フォント内のメタデータを編集する"""
    font.ascent = EM_ASCENT
    font.descent = EM_DESCENT

    if NERD_FONTS_STR in variant:
        # Nerd Fonts の場合は typoascent, typodescent を EM ascent, EM descent よりも大きくする
        font.os2_typoascent = OS2_ASCENT
        font.os2_typodescent = -OS2_DESCENT
    else:
        font.os2_typoascent = EM_ASCENT
        font.os2_typodescent = -EM_DESCENT
    font.os2_typolinegap = 0
    font.os2_winascent = OS2_ASCENT
    font.os2_windescent = OS2_DESCENT

    font.hhea_ascent = OS2_ASCENT
    font.hhea_descent = -OS2_DESCENT
    font.hhea_linegap = 0

    font.sfnt_names = (
        (
            "English (US)",
            "License",
            """This Font Software is licensed under the SIL Open Font License,
Version 1.1. This license is available with a FAQ
at: http://scripts.sil.org/OFL""",
        ),
        ("English (US)", "License URL", "http://scripts.sil.org/OFL"),
        ("English (US)", "Version", VERSION),
    )
    font.familyname = f"{FONT_NAME} {variant}".strip()
    font.fontname = f"{FONT_NAME.replace(' ', '')}{variant}-{weight}"
    font.fullname = f"{FONT_NAME} {variant}".strip() + f" {weight}"
    font.os2_vendor = VENDER_NAME
    font.copyright = COPYRIGHT


if __name__ == "__main__":
    main()
