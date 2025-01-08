# ERA5降水量データ取得ツール 仕様書

## 概要
`get_Total_Rain_from_EPA5.py`は、指定された緯度経度の位置における月別・年間降水量をERA5データセットから取得し、結果をCSVファイルに保存するPythonスクリプトです。

## 特徴
- ERA5再解析データから月別降水量を取得
- バッチ処理による複数地点の効率的な処理
- 30kmメッシュによるデータ集約
- NetCDFとCSV形式でのデータ保存
- 同一メッシュ内のデータキャッシング機能
- デバッグモード搭載

## 必要条件
1. CDS APIアカウントと設定
2. 必要なPythonパッケージ：
   - cdsapi
   - pandas
   - xarray
   - numpy

## インストール方法
1. CDS API認証情報を`$HOME/.cdsapirc`に設定
2. 必要なPythonパッケージをインストール：
```bash
pip install cdsapi pandas xarray
```

## 使用方法
基本的なコマンド形式：
```bash
python get_Total_Rain_from_EPA5.py [-h] [-d] [-y 年] [-i 入力ファイル]
```

引数：
- `-d, --debug`: デバッグモード（5地点のみ処理）
- `-y, --year`: 処理する年（デフォルト：2010）
- `-i, --input`: 緯度経度データを含む入力CSVファイル（デフォルト：test_latlon.csv）

実行例：
```bash
# 2010年のテストデータを処理
python get_Total_Rain_from_EPA5.py -i test_latlon.csv -y 2010

# 2015年のデータをデバッグモードで処理
python get_Total_Rain_from_EPA5.py -d -y 2015
```

## 入力ファイル形式
CSVファイルは以下の列を含む必要があります：
```csv
No,lat1,lon1,location_name
0,43.0621,141.3544,札幌市中央区
...
```

## 出力構造
```
../data/
  ├── YYYY/              # 年ディレクトリ
  │   ├── output/        # 集計結果
  │   ├── netcdf/        # NetCDFファイル
  │   └── csv/           # 個別CSVファイル
  └── temp/              # 一時ファイル
```

### CSV出力形式
個別地点ファイル（csv/precip_location_X.csv）：
```csv
No,Latitude,Longitude,Month,Total Precipitation (mm)
X,緯度,経度,1,降水量
...
X,緯度,経度,12,降水量
X,緯度,経度,Annual,年間総量
```

## メッシュシステム
- 30kmメッシュによるデータ集約
- メッシュサイズ：
  - 緯度：0.27度（≈30km 南北）
  - 経度：0.37度（≈30km 東西、北緯43度付近）

## エラー処理
- ダウンロードデータの整合性検証
- 安全なファイル操作
- 詳細なエラーメッセージ
- 一時ファイルの自動クリーンアップ

## 注意事項
- データソース：Copernicus Climate Data StoreのERA5月平均データ
- 降水量の単位はミリメートル（mm）に変換
- 同一メッシュ内の地点は既存データを再利用してAPI呼び出しを削減

## セキュリティ注意事項

- CDS APIの認証情報は `$HOME/.cdsapirc` ファイルに保存し、決してソースコードやバージョン管理システムにコミットしないでください
- `.cdsapirc` ファイルのパーミッションは `600`（所有者のみ読み書き可能）に設定することを推奨します