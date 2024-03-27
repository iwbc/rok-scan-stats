# rok-scan-stats

Rise of Kingdoms なぜ公式で用意しないのかランキング圧倒的No1のKvK戦績収集を自動化するスクリプト。

## 自動キャプチャ - autocap.py

個人戦力ランキングから各プレイヤーの情報をキャプチャします。

### 動作環境

- Windows 10以降
- Python 3.10（Microsoft Store版）
- BlueStacks 5

### セットアップ

#### 環境

Pythonは[Microsoft Store](https://www.microsoft.com/ja-jp/p/python-310/9pjpw5ldxlz5?cid=msft_web_chart&activetab=pivot:overviewtab)からインストールするのが手軽です。

コマンドプロンプトやPowerShellで以下のコマンドを入力し、動作に必要なモジュールをインストールしてください。

```bash
pip install android-auto-play-opencv
pip install pyperclip
pip install portalocker
pip install fasteners
```

画像解析に失敗するため、rok-scan-statsディレクトリのパスには日本語やスペース等が含まれないようにしてください。  
OK → `C:¥rok-scan-stats`  
NG → `C:¥ライキン¥rok-scan-stats¥`

#### 初期設定

##### BlueStacksインスタンス

- パフォーマンス
  - CPUの割り当て: 高（4コア）
  - メモリの割り当て: 改良済み（4GB）
  - パフォーマンスモード: バランス
  - フレームレート: 60
- ディスプレイ
  - 画面解像度: 1600 x 900
  - 画素密度: 240 DPI（中）
- 上位設定
  - Android Debug Bridge（ADB）: 有効

##### RoK

- 言語: 日本語
- 画質: 中
- フレームレート: 60
- 画面フラッシュ効果オフ: 有効
- 王国称号の通知: 無効

※ 同盟通知が読み取り対象に重なってしまうため、同盟から脱退し無所属の状態で実行してください。

### 使い方

RoKを起動し、戦力ランキングを表示した状態で実行します。  
RoKを起動してから時間が経つとRoKの動作が重くなってくるため、画面遷移時の待機時間が不足しキャプチャに失敗することがあります。その際は、`autocap.py`の`aapo.sleep(sec)`の`sec`部分を調整するか、`--delay`オプションを使用してください。

```bash
python autocap.py 127.0.0.1:5745
```

`127.0.0.1:5745`の部分は環境によって異なります。  
BlueStacksインスタンスの上位設定の`Android Debug Bridge（ADB）`に記載されているものに置き換えてください。

#### オプション

| オプション       | デフォルト値                   | 説明                                                                                                                           |
| ---------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| -d, --dir        | 実行時の日付<br>（YYYY-MM-DD） | キャプチャの保存先ディレクトリ名                                                                                               |
| -s, --start-rank | 1                              | キャプチャ開始順位<br>※ 4位以降から撮影開始する場合は、指定した順位が戦力ランキングの上から4番目に位置するよう表示してください |
| -e, --end-rank   | 1000                           | キャプチャ終了順位                                                                                                             |
| --delay          | 1                              | 各画面遷移時の待機時間調整倍率<br>例えば2を渡すと本来0.5秒待機するところが1秒待機となります                                    |

```bash
# 「data/abc/」に100-200位のスクリーンショットを保存
python autocap.py 127.0.0.1:5745 -d abc -s 100 -e 200
```

### 並列実行

複数のBlueStacksとPowerShellを起動することで、並列に処理させることが可能です。  
※ 複数のBlueStacksでそれぞれランキングを表示する際、時間差による順位ズレが発生しキャプチャ漏れするプレイヤーが出る可能性があります。BlueStacksの同期操作機能を使用し同時にランキングを表示することで防止できます。  
※ 2並列で4コア8スレッドCPU・メモリ16GB、3並列で8コア16スレッドCPU・メモリ24GB搭載のPC推奨します。性能が不足すると表示遅延が発生し、正しくキャプチャできない場合があります。

```bash
# PowerShell 1
# 1-150位を処理
python autocap.py 127.0.0.1:5745 -e 150
```

```bash
# PowerShell 2
# 151-300位を処理
python autocap.py 127.0.0.1:5755 -s 151 -e 300
```

## OCR - ocr.py

autocap.pyで収集したスクリーンショットから、プレイヤー名、ID、同盟タグ、戦力、過去最大戦力、T1〜T5撃破数、戦死数、資源援助数を抽出し、TSV（タブ区切りのCSV）で出力します。

### 動作環境

- Windows 10以降
  - Python 3.10
- Tesseract OCR 5.x

### セットアップ

#### 環境

Windowsは[GitHub](https://github.com/UB-Mannheim/tesseract/wiki)から64bit版のTesseract v5.xをダウンロードしてインストールしてください。  
※ インストール後、tesseract.exeまでのPathを通さないと動作しません。

macOSはHomebrewからインストールできます。

コマンドプロンプトやPowerShellで以下のコマンドを入力し、動作に必要なモジュールをインストールしてください。

```bash
pip install portalocker
pip install pillow
pip install joblib
pip install pyocr
```

### 使い方

```bash
python ocr.py {キャプチャの保存ディレクトリ名 }
```

#### オプション

| オプション    | デフォルト値                                                                | 説明                                                                          |
| ------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| -j, --jobs    | 論理CPU数 - 1                                                               | 並列処理数                                                                    |
| -t, --targets | id alliance power hpower t1kill t2kill t3kill t4kill t5kill ranged dead rss | OCR対象                                                                       |
| --killtest    | テストしない                                                                | 撃破数が正しくOCRされているか撃破ポイントの数値と比較テストする（処理時間増） |

```bash
# シングルプロセスでID,戦力,T4-T5撃破,戦死をOCR
python ocr.py dirname -j 1 -t id power t4kill t5kill dead

# T1-T5全ての撃破を対象にする場合は、'kill'で一括指定可
python ocr.py dirname -t id power kill dead --killtest
```
