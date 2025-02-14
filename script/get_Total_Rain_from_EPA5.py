#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import cdsapi
import pandas as pd
import xarray as xr
import numpy as np
import os
from pathlib import Path
import logging
from typing import Dict, Tuple, List
import shutil
import sys
import time
from tqdm import tqdm

class ERA5RainRetriever:
    """ERA5降水量データ取得クラス"""
    
    MESH_SIZE_KM = 20  # メッシュサイズを20kmに設定
    
    def __init__(self, year: int, input_file: str, debug: bool = False):
        # 入力ファイル名からベース名を取得（拡張子を除く）
        input_base = Path(input_file).stem
        
        # カレントディレクトリを基準に設定
        self.base_dir = Path.cwd() / 'data' / input_base
        self.year = year
        self.debug = debug
        self.setup_directories()
        self.setup_logging()
        self.processed_meshes = {}
        self.all_results = []
    
    def setup_directories(self):
        """必要なディレクトリを作成"""
        # outputディレクトリを削除し、必要なディレクトリのみ作成
        dirs = ['netcdf', 'csv', 'temp']
        for dir_name in dirs:
            (self.base_dir / dir_name).mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """ロギングの設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.base_dir / 'processing.log'),
                logging.StreamHandler()
            ]
        )
    
    def calculate_mesh_bounds(self, lat: float, lon: float) -> Tuple[float, float, float, float]:
        """20kmメッシュの境界を計算
        
        Args:
            lat: 中心緯度
            lon: 中心経度
            
        Returns:
            (north, west, south, east)の境界座標
        """
        # 緯度1度あたりの距離は約111km
        # 経度1度あたりの距離は緯度によって変化（cos(lat)に比例）
        km_per_lat = 111.0
        km_per_lon = 111.0 * np.cos(np.radians(lat))
        
        # メッシュの半分のサイズを度に変換
        half_size_lat = (self.MESH_SIZE_KM / 2) / km_per_lat
        half_size_lon = (self.MESH_SIZE_KM / 2) / km_per_lon
        
        return (
            lat + half_size_lat,  # north
            lon - half_size_lon,  # west
            lat - half_size_lat,  # south
            lon + half_size_lon   # east
        )
    
    def get_mesh_id(self, lat: float, lon: float) -> str:
        """20kmメッシュIDを計算
        
        Args:
            lat: 緯度
            lon: 経度
            
        Returns:
            メッシュID文字列
        """
        bounds = self.calculate_mesh_bounds(lat, lon)
        return f"{lat:.4f}_{lon:.4f}_20km"
    
    def download_era5_data(self, mesh_id: str, lat: float, lon: float) -> Path:
        """ERA5データをダウンロード
        
        Args:
            mesh_id: メッシュID
            lat: 緯度
            lon: 経度
            
        Returns:
            ダウンロードしたファイルのパス
        """
        c = cdsapi.Client()
        output_file = self.base_dir / 'netcdf' / f'precip_{mesh_id}.nc'
        
        # メッシュの境界を計算
        north, west, south, east = self.calculate_mesh_bounds(lat, lon)
        
        if not output_file.exists():
            request_params = {
                'product_type': 'monthly_averaged_reanalysis',
                'variable': 'total_precipitation',
                'year': str(self.year),
                'month': [f"{i:02d}" for i in range(1, 13)],
                'time': '00:00',
                'area': [
                    north, west, south, east
                ],
                'format': 'netcdf'
            }
            
            c.retrieve(
                'reanalysis-era5-single-levels-monthly-means',
                request_params,
                str(output_file)
            )
            logging.info(f"Downloaded data for mesh {mesh_id} at ({lat}, {lon})")
        
        return output_file
    
    def process_precipitation_data(
        self, nc_file: Path, lat: float, lon: float
    ) -> Tuple[np.ndarray, float]:
        """降水量データを処理"""
        ds = xr.open_dataset(nc_file)
        
        # データの形状を確認してログに出力
        logging.debug(f"Data shape: {ds['tp'].values.shape}")
        
        # 1次元の場合の処理
        if len(ds['tp'].values.shape) == 1:
            precip = ds['tp'].values * 1000 * 24 * 30  # m to mm/month
            monthly_precip = precip
        else:
            # 3次元（時間、緯度、経度）の場合の処理
            precip = ds['tp'].values * 1000 * 24 * 30  # m to mm/month
            lat_idx = abs(ds.latitude - lat).argmin()
            lon_idx = abs(ds.longitude - lon).argmin()
            monthly_precip = precip[:, lat_idx, lon_idx]
        
        annual_precip = np.sum(monthly_precip)
        
        ds.close()
        return monthly_precip, annual_precip
    
    def save_results(
        self, results: Tuple[np.ndarray, float], location: Dict
    ) -> None:
        """結果をCSVファイルに保存"""
        monthly_precip, annual_precip = results
        data = []
        
        # 月別データ
        for month, precip in enumerate(monthly_precip, 1):
            data.append({
                'No': location['No'],
                'Latitude': location['lat1'],
                'Longitude': location['lon1'],
                'Location': location.get('location_name', ''),
                'Month': month,
                'Total Precipitation (mm)': precip
            })
            
            # 全地点の結果リストに追加
            self.all_results.append({
                'No': location['No'],
                'Latitude': location['lat1'],
                'Longitude': location['lon1'],
                'Location': location.get('location_name', ''),
                'Month': month,
                'Year': self.year,
                'Total Precipitation (mm)': precip
            })
        
        # 年間データ
        data.append({
            'No': location['No'],
            'Latitude': location['lat1'],
            'Longitude': location['lon1'],
            'Location': location.get('location_name', ''),
            'Month': 'Annual',
            'Total Precipitation (mm)': annual_precip
        })
        
        # 個別地点のCSVファイルを保存
        df = pd.DataFrame(data)
        output_file = self.base_dir / 'csv' / f"precip_location_{location['No']}.csv"
        df.to_csv(output_file, index=False)
        logging.info(f"Saved results for location {location['No']}")

    def save_all_results(self):
        """全地点の結果をまとめたCSVファイルを保存"""
        if self.all_results:
            # 月別データのDataFrame
            monthly_df = pd.DataFrame([
                result for result in self.all_results 
                if result['Month'] != 'Annual'
            ])
            
            # 年間データを計算
            annual_df = monthly_df.groupby(['No', 'Latitude', 'Longitude', 'Location', 'Year'])[
                'Total Precipitation (mm)'
            ].sum().reset_index()
            annual_df['Month'] = 'Annual'
            
            # 月別と年間データを結合
            df = pd.concat([monthly_df, annual_df], ignore_index=True)
            
            # csvディレクトリ内に保存
            output_file = self.base_dir / 'csv' / f"precipitation_results_{self.year}.csv"
            df.to_csv(output_file, index=False)
            logging.info(f"Saved combined results to {output_file}")

    def check_missing_locations(self, input_file: str) -> pd.DataFrame:
        """未取得地点を特定"""
        # 入力ファイルの読み込み
        input_df = pd.read_csv(input_file)
        total_locations = len(input_df)
        
        logging.info(f"\n全地点数: {total_locations}")
        
        # CSVディレクトリのパス
        csv_dir = self.base_dir / 'csv'
        
        if not csv_dir.exists():
            logging.info(f"出力ディレクトリが存在しません。全{total_locations}地点を処理する必要があります。")
            return input_df
        
        # 処理済みの地点を特定（個別ファイルの存在確認）
        processed_locations = []
        for _, row in input_df.iterrows():
            location_file = csv_dir / f"precip_location_{row['No']}.csv"
            if location_file.exists():
                processed_locations.append({
                    'No': row['No'],
                    'lat1': row['lat1'],
                    'lon1': row['lon1']
                })
        
        processed_count = len(processed_locations)
        
        # 処理済み地点をDataFrameに変換
        if processed_locations:
            processed_df = pd.DataFrame(processed_locations)
            
            # 未処理の地点を特定
            missing_df = input_df.merge(
                processed_df,
                on=['No', 'lat1', 'lon1'],
                how='left',
                indicator=True
            )
            
            # _mergeカラムが'left_only'の行が未処理地点
            missing_df = missing_df[missing_df['_merge'] == 'left_only'].drop('_merge', axis=1)
        else:
            missing_df = input_df
        
        missing_count = len(missing_df)
        
        if missing_count > 0:
            logging.info(f"処理済み地点数: {processed_count}")
            logging.info(f"未取得地点数: {missing_count}")
            logging.info(f"進捗状況: {processed_count/total_locations*100:.1f}% 完了")
            
            # 未取得地点の一覧をCSVファイルに保存
            missing_file = self.base_dir / 'missing_locations.csv'
            missing_df.to_csv(missing_file, index=False)
            logging.info(f"未取得地点の一覧を保存しました: {missing_file}")
            
            # 最初の5件を表示
            logging.info("\n未取得地点の例（最初の5件）:")
            for _, row in missing_df.head().iterrows():
                logging.info(f"No: {row['No']}, 緯度: {row['lat1']}, 経度: {row['lon1']}, 地点: {row.get('location_name', 'N/A')}")
        else:
            logging.info(f"全{total_locations}地点のデータが取得済みです（100% 完了）")
        
        return missing_df

    def process_locations(self, input_file: str, resume: bool = False) -> None:
        """位置データを処理"""
        input_path = Path(input_file)
        if not input_path.is_absolute():
            input_path = Path.cwd() / input_path

        if not input_path.exists():
            raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")

        # 未取得地点を確認
        df = self.check_missing_locations(input_path)
        
        # resumeモードでない場合は、続行するか確認
        if not resume and len(df) < pd.read_csv(input_path).shape[0]:
            logging.warning("既存のデータが存在します。--resumeオプションを使用して未取得地点のみを処理することをお勧めします。")
            logging.warning("5秒後に処理を開始します。中断する場合はCtrl+Cを押してください。")
            time.sleep(5)
            df = pd.read_csv(input_path)
        
        if len(df) == 0:
            logging.info("処理する地点がありません。")
            return

        # ヘッダー名のマッピング
        header_mapping = {
            'No': ['No', 'no', 'ID', 'id', 'index'],
            'lat1': ['lat1', 'lat', 'latitude', 'Latitude', 'LAT'],
            'lon1': ['lon1', 'lon', 'longitude', 'Longitude', 'LON']
        }
        
        # 必要なカラムの存在確認と名前の標準化
        column_mapping = {}
        for required_col, possible_names in header_mapping.items():
            found_col = None
            for col_name in possible_names:
                if col_name in df.columns:
                    found_col = col_name
                    break
            
            if found_col is None:
                raise ValueError(f"必要なカラム {required_col} が見つかりません。以下のいずれかの名前が必要です: {possible_names}")
            
            column_mapping[found_col] = required_col
        
        # カラム名を標準化
        df = df.rename(columns=column_mapping)
        
        # デバッグモードの場合は最初の5行のみ処理
        if self.debug:
            df = df.head(5)
            logging.info("Running in debug mode with 5 locations")
        
        # インデックスがない場合は追加
        if 'No' not in df.columns:
            df['No'] = range(len(df))
        
        # 進捗バーを追加（残り時間の推定を含む）
        total = len(df)
        with tqdm(total=total, desc="処理中", unit="地点", 
                 bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} 地点'
                 ' [{elapsed}<{remaining}, {rate_fmt}{postfix}]') as pbar:
            for _, location in df.iterrows():
                try:
                    mesh_id = self.get_mesh_id(location['lat1'], location['lon1'])
                    
                    if mesh_id in self.processed_meshes:
                        # 同じメッシュ内のデータを再利用
                        nc_file = self.processed_meshes[mesh_id]
                    else:
                        nc_file = self.download_era5_data(
                            mesh_id, location['lat1'], location['lon1']
                        )
                        self.processed_meshes[mesh_id] = nc_file
                    
                    results = self.process_precipitation_data(
                        nc_file, location['lat1'], location['lon1']
                    )
                    self.save_results(results, location)
                    
                except Exception as e:
                    logging.error(f"Error processing location {location['No']}: {str(e)}")
                    logging.error(f"Details: lat={location['lat1']}, lon={location['lon1']}")
                    continue
                finally:
                    pbar.update(1)  # 進捗バーを更新
                    pbar.set_postfix({
                        'Location': f"{location.get('location_name', 'N/A')}",
                        'No': location['No'],
                        '完了': f"{pbar.n/total*100:.1f}%"
                    })
        
        # 全地点の処理が終わった後に結果をまとめて保存
        self.save_all_results()

def main():
    parser = argparse.ArgumentParser(
        description='ERA5降水量データ取得ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
入力CSVファイル形式:
  以下のいずれかのヘッダーを持つCSVファイルが必要です：
    - ID/インデックス列: No, no, ID, id, index
    - 緯度列: lat1, lat, latitude, Latitude, LAT
    - 経度列: lon1, lon, longitude, Longitude, LON
  
  例1：
    No,lat1,lon1,location_name
    0,43.0621,141.3544,札幌市中央区
  
  例2：
    id,latitude,longitude,name
    1,35.6895,139.6917,東京都新宿区

出力ディレクトリ:
  入力ファイル名をベースにディレクトリが作成されます
  例: test_2010.csv → ./data/test_2010/
        """
    )
    parser.add_argument('-d', '--debug', action='store_true',
                      help='デバッグモード（5地点のみ処理）')
    parser.add_argument('-y', '--year', type=int, default=2010,
                      help='処理する年（デフォルト：2010）')
    parser.add_argument('-i', '--input', type=str, 
                      default='test_latlon.csv',
                      help='緯度経度データを含む入力CSVファイル（ヘッダー: No,lat1,lon1,location_name）')
    parser.add_argument('-r', '--resume', action='store_true',
                      help='未取得地点のみを処理する')
    parser.add_argument('--dry-run', action='store_true',
                      help='未取得地点の確認のみを行い、データは取得しない')
    
    args = parser.parse_args()
    
    try:
        retriever = ERA5RainRetriever(args.year, args.input, args.debug)
        
        # dry-runの場合は未取得地点の確認のみ
        if args.dry_run:
            retriever.check_missing_locations(args.input)
            return
        
        retriever.process_locations(args.input, args.resume)
    except Exception as e:
        logging.error(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
