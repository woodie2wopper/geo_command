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

class ERA5RainRetriever:
    """ERA5降水量データ取得クラス"""
    
    MESH_SIZE_KM = 20  # メッシュサイズを20kmに設定
    
    def __init__(self, year: int, debug: bool = False):
        self.script_dir = Path(__file__).parent.resolve()
        self.base_dir = self.script_dir.parent / 'data' / str(year)
        self.year = year
        self.debug = debug
        self.setup_directories()
        self.setup_logging()
        self.processed_meshes = {}
        
    def setup_directories(self):
        """必要なディレクトリを作成"""
        dirs = ['output', 'netcdf', 'csv', 'temp']
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
        """降水量データを処理
        
        Args:
            nc_file: NetCDFファイルパス
            lat: 緯度
            lon: 経度
            
        Returns:
            月別降水量と年間総降水量のタプル
        """
        ds = xr.open_dataset(nc_file)
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
        """結果をCSVファイルに保存
        
        Args:
            results: 月別降水量と年間総降水量のタプル
            location: 位置情報を含む辞書
        """
        monthly_precip, annual_precip = results
        data = []
        
        # 月別データ
        for month, precip in enumerate(monthly_precip, 1):
            data.append({
                'No': location['No'],
                'Latitude': location['lat1'],
                'Longitude': location['lon1'],
                'Month': month,
                'Total Precipitation (mm)': precip
            })
        
        # 年間データ
        data.append({
            'No': location['No'],
            'Latitude': location['lat1'],
            'Longitude': location['lon1'],
            'Month': 'Annual',
            'Total Precipitation (mm)': annual_precip
        })
        
        df = pd.DataFrame(data)
        output_file = self.base_dir / 'csv' / f"precip_location_{location['No']}.csv"
        df.to_csv(output_file, index=False)
        logging.info(f"Saved results for location {location['No']}")
    
    def process_locations(self, input_file: str) -> None:
        """位置データを処理
        
        Args:
            input_file: 入力CSVファイルパス
        """
        input_path = Path(input_file)
        if not input_path.is_absolute():
            input_path = self.script_dir / input_path

        if not input_path.exists():
            raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")

        df = pd.read_csv(input_path)
        if self.debug:
            df = df.head(5)
            logging.info("Running in debug mode with 5 locations")
        
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
                continue

def main():
    parser = argparse.ArgumentParser(
        description='ERA5降水量データ取得ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
入力CSVファイル形式:
  以下のヘッダーを持つCSVファイルが必要です：
    No,lat1,lon1,location_name
  
  例：
    No,lat1,lon1,location_name
    0,43.0621,141.3544,札幌市中央区
    1,35.6895,139.6917,東京都新宿区
        """
    )
    parser.add_argument('-d', '--debug', action='store_true',
                      help='デバッグモード（5地点のみ処理）')
    parser.add_argument('-y', '--year', type=int, default=2010,
                      help='処理する年（デフォルト：2010）')
    parser.add_argument('-i', '--input', type=str, 
                      default=str(Path(__file__).parent / 'doc' / 'test_latlon.csv'),
                      help='緯度経度データを含む入力CSVファイル（ヘッダー: No,lat1,lon1,location_name）')
    
    args = parser.parse_args()
    
    try:
        retriever = ERA5RainRetriever(args.year, args.debug)
        retriever.process_locations(args.input)
    except Exception as e:
        logging.error(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
