# ERA5降水量データ取得ツール

## 概要
ERA5の月別再解析データから指定地点の降水量データを取得し、CSVファイルとして保存するツールです。

## 使用方法

```bash
get_Total_Rain_from_EPA5.py [-h] [-d] [-y YEAR] [-i INPUT] [-r] [--dry-run]
```

### オプション
- `-h, --help`: ヘルプメッセージを表示
- `-d, --debug`: デバッグモード（最初の5地点のみ処理）
- `-y YEAR, --year YEAR`: 処理する年（デフォルト：2010）
- `-i INPUT, --input INPUT`: 入力CSVファイル（デフォルト：test_latlon.csv）
- `-r, --resume`: 未取得地点のみを処理
- `--dry-run`: 未取得地点の確認のみを行い、データは取得しない

### 入力ファイル形式
以下のいずれかのヘッダーを持つCSVファイルが必要です：
- ID/インデックス列: `No`, `no`, `ID`, `id`, `index`
- 緯度列: `lat1`, `lat`, `latitude`, `Latitude`, `LAT`
- 経度列: `lon1`, `lon`, `longitude`, `Longitude`, `LON`
- 地点名列（オプション）: `location_name`

例：
```csv
No,lat1,lon1,location_name
0,43.0621,141.3544,札幌市中央区
1,35.6895,139.6917,東京都新宿区
```

### 出力ディレクトリ構造
入力ファイル名をベースにディレクトリが作成されます。
例：`test_2010.csv` → `./data/test_2010/`

```
data/
└── [入力ファイル名]/
    ├── csv/
    │   ├── precip_location_0.csv  # 地点ごとの降水量データ
    │   ├── precip_location_1.csv
    │   └── ...
    ├── netcdf/  # ERA5データのキャッシュ
    ├── temp/    # 一時ファイル
    ├── missing_locations.csv  # 未取得地点リスト
    └── processing.log        # 処理ログ
```

### 出力ファイル形式（地点ごと）
各地点のCSVファイルには以下の列が含まれます：
- `No`: 地点番号
- `Latitude`: 緯度
- `Longitude`: 経度
- `Location`: 地点名（入力ファイルに含まれる場合）
- `Month`: 月（1-12）または'Annual'
- `Total Precipitation (mm)`: 月間または年間降水量

## 処理の流れ
1. 入力CSVファイルから地点情報を読み込み
2. 未取得地点の確認（`--resume`または`--dry-run`オプション使用時）
3. 20kmメッシュ単位でERA5データをダウンロード
4. 各地点の降水量を計算
5. 結果をCSVファイルに保存

## エラー処理
- 地点ごとにエラーが発生した場合でも処理を継続
- エラーが発生した地点は処理ログに記録
- `--resume`オプションで未取得地点の再処理が可能

## 進捗表示
- 処理中の地点数と推定残り時間を表示
- 現在の地点情報と完了率をリアルタイム表示
- ログファイルに詳細な処理状況を記録

## 注意事項
- ERA5データの取得にはCDSのアカウントとAPIキーが必要
- `~/.cdsapirc`に適切なAPI設定が必要
- 大量の地点を処理する場合は`--resume`オプションの使用を推奨