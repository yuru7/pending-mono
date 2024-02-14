# Pending Mono

Pending Mono は、欧文フォント [Commit Mono](https://commitmono.com/) と日本語フォント [BIZ UDゴシック](https://github.com/googlefonts/morisawa-biz-ud-gothic) を合成したプログラミング向けフォントです。

[✒ **ダウンロード**](https://github.com/yuru7/pending-mono/releases)  
※「Assets」内の zip ファイルをダウンロードしてご利用ください。

> 💡 その他、公開中のプログラミングフォント
> - 日本語文字に源柔ゴシック、英数字部分に Hack を使った [**白源 (はくげん／HackGen)**](https://github.com/yuru7/HackGen)
> - 日本語文字に IBM Plex Sans JP、英数字部分に IBM Plex Mono を使った [**PlemolJP (プレモル ジェイピー)**](https://github.com/yuru7/PlemolJP)
> - 日本語文字にBIZ UDゴシック、英数字部分に JetBrains Mono を使った [**UDEV Gothic**](https://github.com/yuru7/udev-gothic)

## 特徴

以下のような特徴があります。

- 隣接する `m` などの位置を調節する Smart Kerning 搭載。字体のシンプルさに重点を置いた [Commit Mono](https://commitmono.com/) 由来の英数字
- ユニバーサルデザインを掲げ、読みやすさを追求したモリサワ製 [BIZ UDゴシック](https://github.com/googlefonts/morisawa-biz-ud-gothic) 由来の日本語文字
- 文字幅比率が 半角3:全角5、ゆとりのある幅の半角英数字
    - 半角1:全角2 のバリエーションあり
- バグの原因になりがちな全角スペースが可視化される

## サンプル

TODO

## ビルド

ビルドに使用するツール、ランタイム

- fontforge: `20230101` \[[Windows](https://fontforge.org/en-US/downloads/windows/)\] \[[Linux](https://fontforge.org/en-US/downloads/gnulinux/)\]
- Python: `>=3.8`

### Windows (PowerShell)

```sh
# 必要パッケージのインストール
pip install -r requirements.txt
# ビルド
& "C:\Program Files (x86)\FontForgeBuilds\bin\ffpython.exe" .\fontforge_script.py && python fonttools_script.py
```

### Linux

coming soon...

## ライセンス

SIL Open Font License, Version 1.1 が適用され、個人・商用問わず利用可能です。

ソースフォントのライセンスも同様に SIL Open Font License, Version 1.1 が適用されています。詳しくは `source_fonts` ディレクトリに含まれる LICENSE ファイルを参照してください。
