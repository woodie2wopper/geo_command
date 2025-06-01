# GPX to CSV コンバーター

## 概要
Garmin GPSデバイス（etrex 10J等）で記録したGPXファイルからウェイポイント情報を抽出し、CSVファイルに変換するツールです。複数のGPXファイルを一度に処理することができます。

## 機能
- GPXファイルから以下の情報を抽出：
  - ポイント名
  - 緯度・経度
  - 標高
  - UTC時間（日付と時間を分離）
  - 現地時間（日付と時間を分離）
  - UNIXタイム（エポック時間）
  - シンボル情報
  - デバイス情報
  - ファイル作成時間
  - ソースファイル名
- 複数ファイルの一括処理
- ワイルドカードによるファイル指定
- エラー発生時も他のファイルの処理を継続

## 文字コード
- スクリプトファイル: UTF-8
- 入力GPXファイル: UTF-8
- 出力CSVファイル: UTF-8

## 使用方法

### 基本的な使用方法
```bash
# 単一ファイルの処理
python convert_gpx_to_csv.py input.gpx

# 複数ファイルの処理（ワイルドカード使用）
python convert_gpx_to_csv.py *.gpx

# 特定のパターンのファイルを処理
python convert_gpx_to_csv.py 2023*.gpx

# 複数のパターンを指定
python convert_gpx_to_csv.py 2023*.gpx 2024*.gpx
```

### オプション
- `-o, --output`: 出力CSVファイルのパスを指定（指定がない場合は標準出力に表示）
- `-v, --verbose`: 詳細な情報を表示
- `-h, --help`: ヘルプメッセージを表示

### 使用例
```bash
# 標準出力に表示
python convert_gpx_to_csv.py '/Volumes/GARMIN/Garmin/GPX/*.gpx'

# ファイルに保存
python convert_gpx_to_csv.py '/Volumes/GARMIN/Garmin/GPX/*.gpx' -o output.csv

# 詳細情報を表示
python convert_gpx_to_csv.py '/Volumes/GARMIN/Garmin/GPX/*.gpx' -v
```

## 出力形式

### CSVファイルの列
1. `Name`: ポイント名
2. `Latitude`: 緯度
3. `Longitude`: 経度
4. `Elevation`: 標高（メートル）
5. `UTC_Date`: UTC日付（YYYY-MM-DD形式）
6. `UTC_Time`: UTC時間（HH:MM:SS形式）
7. `Local_Date`: 現地日付（YYYY-MM-DD形式）
8. `Local_Time`: 現地時間（HH:MM:SS形式）
9. `Epoch_Time`: UNIXタイム（1970年1月1日からの経過秒数）
10. `Symbol`: ウェイポイントのアイコン
11. `Device`: GPSデバイスの種類
12. `File_Creation_Time`: ファイル作成時間
13. `Source_File`: 元のGPXファイル名

### 出力例
```csv
Name,Latitude,Longitude,Elevation,UTC_Date,UTC_Time,Local_Date,Local_Time,Epoch_Time,Symbol,Device,File_Creation_Time,Source_File
237,37.699191,140.324664,553.601135,2025-05-20,20:11:49,2025-05-21,5:11:49,1747873909,Flag Blue,eTrex 10J,2025-05-20 20:11:49,ﾎﾟｲﾝﾄ_25-05-21.gpx
```

## 対応しているGPXファイル形式
- GPX 1.1形式
- Garmin GPSデバイスで作成されたGPXファイル
- 以下の名前空間に対応：
  - http://www.topografix.com/GPX/1/1
  - http://www.garmin.com/xmlschemas/GpxExtensions/v3
  - http://www.garmin.com/xmlschemas/WaypointExtension/v1
  - http://www.garmin.com/xmlschemas/TrackPointExtension/v1

## エラー処理
- ファイルが存在しない場合のエラー処理
- GPXファイルの解析エラー処理
- 日時情報の解析エラー処理
- 個別のファイル処理エラーが他のファイルの処理に影響しない

## 依存ライブラリ
- xml.etree.ElementTree: XMLファイルの解析
- pandas: データフレーム処理とCSV出力
- datetime: 日時処理
- time: UNIXタイムの計算
- glob: ファイルパターンマッチング

## 注意事項
- 入力ファイルはUTF-8エンコーディングである必要があります
- 日時情報は日本時間（JST）を想定しています
- 標高はメートル単位で出力されます
- 複数ファイルを処理する場合、メモリ使用量に注意してください
- ワイルドカードはシェルの機能を使用します
