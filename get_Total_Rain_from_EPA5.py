#!/usr/bin/env python3

import cdsapi
import pandas as pd
import xarray as xr
import os
import time
import argparse
import shutil

# コマンドライン引数の設定
parser = argparse.ArgumentParser(description='Get total precipitation data from ERA5 reanalysis')
parser.add_argument('-d', '--debug', action='store_true', 
                    help='Run in debug mode (process only five locations)')
parser.add_argument('-y', '--year', type=str, default='2010',
                    help='Year to process (default: 2010)')
parser.add_argument('-i', '--input', type=str, default='test_latlon.csv',
                    help='Input CSV file with latitude and longitude data (default: test_latlon.csv)')
args = parser.parse_args()

# 使用方法の例を追加
if __name__ == "__main__":
    print(f"""
ERA5 Total Precipitation Data Retrieval Tool
------------------------------------------
Input file: {args.input}
Year: {args.year}
Debug mode: {'On' if args.debug else 'Off'}

Usage examples:
  python get_Total_Rain_from_EPA5.py -i test_latlon.csv -y 2010
  python get_Total_Rain_from_EPA5.py -d -y 2015 -i other_locations.csv
""")

# 入力ファイルと出力ファイルのパス
input_file = args.input  # コマンドライン引数から入力ファイルを取得
base_dir = '../data'
year_dir = f'{args.year}'
output_dir = os.path.join(base_dir, year_dir, 'output')
netcdf_dir = os.path.join(base_dir, year_dir, 'netcdf')
csv_dir = os.path.join(base_dir, year_dir, 'csv')
output_file = f'precipitation_results_{args.year}.csv'

# 必要なディレクトリの作成
temp_dir = './temp'  # 一時ファイル用ディレクトリ
for directory in [output_dir, netcdf_dir, csv_dir, temp_dir]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# CSVファイルを読み込む
data = pd.read_csv(input_file)

# CDS APIクライアントを作成
c = cdsapi.Client()

# 結果を格納するリスト
results = []

# 緯度経度データを100個ずつ処理
batch_size = 100

# 定数定義（ファイル先頭付近に追加）
# 30kmメッシュに相当する緯度経度の範囲
# 緯度1度 ≈ 111km なので、30kmは約0.27度
# 経度1度は緯度によって異なる（cos(緯度)を掛ける）
# 北緯43度の場合: cos(43°) × 111km = 81.2km なので、30kmは約0.37度
GRID_LAT_DELTA = 0.27  # 約30km（南北方向）
GRID_LON_DELTA = 0.37  # 約30km（東西方向、北緯43度付近）

def safe_retrieve_data(client, location_id, lat, lon, year):
    """安全なデータ取得処理"""
    temp_file = os.path.join(temp_dir, f"temp_{location_id}.nc")  # 一時ファイルのパスを変更
    try:
        dataset = "reanalysis-era5-single-levels-monthly-means"
        request = {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": ["total_precipitation"],
            "year": [year],
            "month": [
                "01", "02", "03",
                "04", "05", "06",
                "07", "08", "09",
                "10", "11", "12"
            ],
            "time": ["00:00"],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": [
                lat + GRID_LAT_DELTA/2,  # 北端
                lon - GRID_LON_DELTA/2,  # 西端
                lat - GRID_LAT_DELTA/2,  # 南端
                lon + GRID_LON_DELTA/2   # 東端
            ]
        }

        # データ取得
        client.retrieve(dataset, request, temp_file)
        
        # データの整合性チェック
        with xr.open_dataset(temp_file) as ds:
            if 'tp' not in ds.variables:
                raise ValueError("Required variable 'tp' not found in dataset")
            return ds.load()
            
    except Exception as e:
        print(f"Error retrieving data for location {location_id}: {str(e)}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"Removed temporary file {temp_file} due to error")
        raise

def save_intermediate_files(location_id, lat, lon, monthly_precip, annual_precip):
    """中間ファイルを保存"""
    # location_idを整数に変換
    location_id = int(location_id)
    
    # CSVデータの作成
    csv_data = {
        'No': [location_id] * 13,  # 12ヶ月 + 年間
        'Latitude': [lat] * 13,
        'Longitude': [lon] * 13,
        'Month': list(range(1, 13)) + ['Annual'],  # 1-12月 + 年間
        'Total Precipitation (mm)': []  # 降水量データ
    }
    
    # 月別データを追加
    for month in range(1, 13):
        # 配列全体の平均を取得（monthly_meansデータセットの特性に対応）
        precip_value = float(monthly_precip.sel(month=month).values.mean())
        csv_data['Total Precipitation (mm)'].append(precip_value * 1000)  # mmに変換
    
    # 年間データを追加（月別値の合計）
    annual_value = float(annual_precip.values.mean()) * 1000  # mmに変換
    csv_data['Total Precipitation (mm)'].append(annual_value)
    
    # DataFrameに変換
    location_df = pd.DataFrame(csv_data)
    
    # CSVとして保存
    csv_file = os.path.join(csv_dir, f'precip_location_{location_id}.csv')
    location_df.to_csv(csv_file, index=False)
    print(f"CSV data saved to {csv_file}\n")    
    
    # 結果リストのために同じ形式のデータを返す
    return location_df.to_dict('records')

def get_mesh_id(lat, lon):
    """緯度経度からメッシュIDを計算"""
    # メッシュの中心点を計算
    lat_center = round(lat / GRID_LAT_DELTA) * GRID_LAT_DELTA
    lon_center = round(lon / GRID_LON_DELTA) * GRID_LON_DELTA
    return f"{lat_center:.3f}_{lon_center:.3f}"

def copy_mesh_data(src_id, dest_id, year):
    """同一メッシュ内のデータをコピー"""
    try:
        # NetCDFファイルのコピー
        src_nc = os.path.join(netcdf_dir, f'precip_{year}_location_{src_id}.nc')
        dest_nc = os.path.join(netcdf_dir, f'precip_{year}_location_{dest_id}.nc')
        if os.path.exists(src_nc):
            shutil.copy2(src_nc, dest_nc)
            print(f"Copied NetCDF from location {src_id} to {dest_id}")
        
        # CSVファイルのコピー
        src_csv = os.path.join(csv_dir, f'precip_{year}_location_{src_id}.csv')
        dest_csv = os.path.join(csv_dir, f'precip_{year}_location_{dest_id}.csv')
        if os.path.exists(src_csv):
            # CSVを読み込んで新しいlocation_idで保存
            df = pd.read_csv(src_csv)
            df['No'] = dest_id
            df.to_csv(dest_csv, index=False)
            print(f"Created CSV for location {dest_id} based on {src_id}")
        
        return True
    except Exception as e:
        print(f"Error copying mesh data: {str(e)}")
        return False

# メインループの前に処理済みメッシュを追跡する辞書を作成
processed_meshes = {}  # {mesh_id: first_location_id}

# メインループ内の処理を修正
for i in range(0, len(data), batch_size):
    batch = data.iloc[i:i + batch_size]
    
    # デバッグモードで5個だけ処理
    if args.debug:
        batch = batch.iloc[:5]
    
    start_time = time.time()
    
    for _, row in batch.iterrows():
        lat, lon = row['lat1'], row['lon1']
        location_id = int(row['No'])
        mesh_id = get_mesh_id(lat, lon)
        
        # 同じメッシュ内に既存のデータがあるかチェック
        if mesh_id in processed_meshes:
            src_id = processed_meshes[mesh_id]
            print(f"Location {location_id} is in the same mesh as location {src_id}. Copying data...")
            
            if copy_mesh_data(src_id, location_id, args.year):
                # 結果リストに追加（既存データを基に）
                with xr.open_dataset(os.path.join(netcdf_dir, f'precip_{args.year}_location_{src_id}.nc')) as ds:
                    daily_precip = ds['tp'] * 1000
                    monthly_precip = daily_precip.groupby('valid_time.month').sum(dim='valid_time')
                    annual_precip = daily_precip.sum(dim='valid_time')
                    location_results = save_intermediate_files(
                        location_id, lat, lon, monthly_precip, annual_precip
                    )
                    results.extend(location_results)
                continue
        
        try:
            nc_file = os.path.join(netcdf_dir, f'precip_{args.year}_location_{location_id}.nc')
            
            if os.path.exists(nc_file):
                print(f"File {nc_file} already exists. Skipping download.")
                dataset = xr.open_dataset(nc_file)
            else:
                print(f"Processing location {location_id} at ({lat}, {lon})...")
                dataset = safe_retrieve_data(c, location_id, lat, lon, args.year)
                dataset.to_netcdf(nc_file)
            
            # データ処理
            daily_precip = dataset['tp'] * 1000
            monthly_precip = daily_precip.groupby('valid_time.month').sum(dim='valid_time')
            annual_precip = daily_precip.sum(dim='valid_time')
            
            # 中間ファイルを保存
            location_results = save_intermediate_files(
                location_id, lat, lon, monthly_precip, annual_precip
            )
            results.extend(location_results)
            
            # デッシュ情報を記録
            processed_meshes[mesh_id] = location_id
            
            # データセットを閉じる
            dataset.close()
            
            # 一時ファイルの削除（safe_retrieve_data内で使用した同じファイル）
            temp_file = os.path.join(temp_dir, f"temp_{location_id}.nc")
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"Temporary file {temp_file} removed")
                
        except Exception as e:
            print(f"Error processing location {location_id}: {str(e)}")
            continue
    
    end_time = time.time()
    print(f"Batch {i // batch_size + 1} processed in {end_time - start_time:.2f} seconds")

# 出力ディレクトリの確認と作成
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 結果をデータフレームに変換
results_df = pd.DataFrame(results)

# 年間集計CSVをoutputディレクトリに保存
results_df.to_csv(os.path.join(output_dir, output_file), index=False)
print(f"\nAggregated data saved to {os.path.join(output_dir, output_file)}")
