# rok-scan-stats

Rise of Kingdoms なぜ公式で用意しないのかランキング圧倒的No1のKvK戦績収集を自動化するスクリプト。

## 自動キャプチャ - autocap.py

個人戦力ランキングから各プレイヤーの情報をキャプチャします。

### 動作環境

- Windows 10
- Python 3.10（Microsoft Store版）
- NoxPlayer 7

### セットアップ

#### 環境

Pythonは[Microsoft Store](https://www.microsoft.com/ja-jp/p/python-310/9pjpw5ldxlz5?cid=msft_web_chart&activetab=pivot:overviewtab)からインストールするのが手軽。

コマンドプロンプトやPowerShellで以下のコマンドを入力し、動作に必要なモジュールをインストールしてください。

```bash
pip install android-auto-play-opencv
pip install portalocker
```

rok-scan-statsディレクトリのパスには日本語を含まないようにしてください（`C:¥Program Files¥ライキン¥rok-scan-stats¥`のようにパスの途中に日本語を含むと画像解析に失敗します）  
`adb.exe が見つかりません。`エラーが出た場合は、`autocap.py`の`ADB_PATH`をNoxPlayerのadb.exeがあるパスに変更してください。

#### NoxPlayerとライキンの設定

NoxPlayerの設定は、パフォーマンス「高い（4コアCPU、4096MBメモリ）」、解像度「1600x900」にし、ライキンは、画質「中」、フレームレート「至高」にします。  
なお、同盟から脱退し無所属の状態で実行することを推奨します（同盟通知が読み取り対象に重なってしまうことがあります）

### 使い方

NoxPlayerでライキンを起動し、戦力ランキングを表示した状態で実行します。

```bash
python autocap.py
```

#### オプション

| オプション       | デフォルト値                 | 説明                                                                                                                             |
| ---------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| -d, --dir        | 実行時の日付<br>（年-月-日） | キャプチャの保存先ディレクトリ名                                                                                                 |
| -s, --start-rank | 1                            | キャプチャ開始順位<br>※ 4位以降から撮影開始する場合は、指定した順位が戦力ランキングの上から4番目に位置するよう表示してください。 |
| -e, --end-rank   | 1000                         | キャプチャ終了順位                                                                                                               |

```bash
# 「data/abc/」に100-200位のスクリーンショットを保存
python autocap.py -d abc -s 100 -e 200
```

### 並列実行

複数のNoxPlayerとPowerShellを起動することで、並列に処理させることが可能です。  
※ 複数のNoxPlayerでそれぞれランキングを表示する際、時間差による順位ズレが発生しキャプチャ漏れするプレイヤーが出る可能性があります。NoxPlayerのマルチ同期機能を使用し同時にランキングを表示することである程度防止できます。  
※ 2並列で4コア8スレッドCPU・メモリ16GB、3並列で8コア16スレッドCPU・メモリ24GB搭載のPC推奨します。性能が不足すると表示遅延が発生し、正しくキャプチャできない場合があります。

```bash
# PowerShell 1
# 1-150位を処理
python autocap.py -d scan -e 150
```

```bash
# PowerShell 2
# 151-300位を処理
python autocap.py -d scan -s 151 -e 300
```

## OCR - ocr.py

autocap.pyで収集したスクリーンショットから、プレイヤー名、ID、戦力、T1〜T5撃破数、戦死数、資源援助数を抽出し、TSV（タブ区切りのCSV）で出力します。

### 動作環境

- Windows 10
  - Python 3.10（Microsoft Store）
- macOS 11
  - Python 3.10（Homebrew）
- Tesseract OCR 5.0.x

### セットアップ

#### 環境

Windowsは[GitHub](https://github.com/UB-Mannheim/tesseract/wiki)から64bit版のTesseract v5.0.xをダウンロードしてインストールしてください。  
※ インストール後、tesseract.exeまでのPathを通さないと動作しません。

macOSはHomebrewからインストールできます。

コマンドプロンプトやPowerShellで以下のコマンドを入力し、動作に必要なモジュールをインストールしてください。

```bash
pip install portalocker
pip install pyperclip
pip install joblib
pip install pyocr
```

### 使い方

```bash
python ocr.py {キャプチャの保存ディレクトリ名 }
```

#### オプション

| オプション | デフォルト値  | 説明       |
| ---------- | ------------- | ---------- |
| -j, --jobs | 論理CPU数 - 1 | 並列処理数 |

```bash
# シングルプロセスでCPUに負荷をかけずに処理
python ocr.py dirname -j 1
```
