#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import pandas as pd
import argparse
import sys
import os
from datetime import datetime
import time
import glob

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='GPXファイルからウェイポイント情報を抽出し、CSVファイルに変換します。',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('gpx_files', nargs='+', help='入力GPXファイルのパス（ワイルドカード可: *.gpx）')
    parser.add_argument('-o', '--output', help='出力CSVファイルのパス（指定がない場合は標準出力に表示）')
    parser.add_argument('-v', '--verbose', action='store_true', help='詳細な情報を表示')
    return parser.parse_args()

def process_gpx_file(gpx_file_path, verbose=False):
    try:
        if not os.path.exists(gpx_file_path):
            print(f"エラー: ファイル '{gpx_file_path}' が見つかりません。", file=sys.stderr)
            return None

        # GPXファイルを読み込んでパース
        tree = ET.parse(gpx_file_path)
        root = tree.getroot()

        # 名前空間を指定（GPX 1.1 に準拠）
        ns = {'default': 'http://www.topografix.com/GPX/1/1'}

        # メタデータの取得
        metadata = root.find('default:metadata', ns)
        creator = root.get('creator', '')
        creation_time = None
        if metadata is not None:
            time_elem = metadata.find('default:time', ns)
            if time_elem is not None:
                try:
                    creation_time = datetime.strptime(time_elem.text, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    pass

        # ウェイポイント情報を抽出
        waypoints = []
        for wpt in root.findall('default:wpt', ns):
            lat = wpt.get('lat')
            lon = wpt.get('lon')
            ele = wpt.find('default:ele', ns)
            name = wpt.find('default:name', ns)
            time = wpt.find('default:time', ns)
            cmt = wpt.find('default:cmt', ns)
            sym = wpt.find('default:sym', ns)

            # 日時情報の処理
            utc_time = None
            local_time = None
            epoch_time = None
            
            # UTC時間の処理
            utc_date = None
            utc_time_str = None
            if time is not None:
                try:
                    utc_time = datetime.strptime(time.text, '%Y-%m-%dT%H:%M:%SZ')
                    utc_date = utc_time.strftime('%Y-%m-%d')
                    utc_time_str = utc_time.strftime('%H:%M:%S')
                except ValueError:
                    pass
            
            # ローカル時間の処理
            local_date = None
            local_time_str = None
            if cmt is not None:
                try:
                    local_time = datetime.strptime(cmt.text, '%Y-%m-%d %H:%M:%S')
                    local_date = local_time.strftime('%Y-%m-%d')
                    local_time_str = local_time.strftime('%H:%M:%S')
                    # ローカル時間からUNIXタイムを計算
                    epoch_time = int(local_time.timestamp())
                except ValueError:
                    pass

            waypoints.append({
                'Name': name.text if name is not None else '',
                'Latitude': float(lat) if lat else None,
                'Longitude': float(lon) if lon else None,
                'Elevation': float(ele.text) if ele is not None else None,
                'UTC_Date': utc_date,
                'UTC_Time': utc_time_str,
                'Local_Date': local_date,
                'Local_Time': local_time_str,
                'Epoch_Time': epoch_time,
                'Symbol': sym.text if sym is not None else '',
                'Device': creator,
                'File_Creation_Time': creation_time.strftime('%Y-%m-%d %H:%M:%S') if creation_time else None,
                'Source_File': os.path.basename(gpx_file_path)
            })

        # DataFrameに変換
        df = pd.DataFrame(waypoints)
        
        if verbose:
            print(f"ファイル '{gpx_file_path}' から {len(waypoints)} 個のウェイポイントを処理しました。", file=sys.stderr)
            
        return df

    except ET.ParseError as e:
        print(f"エラー: ファイル '{gpx_file_path}' の解析に失敗しました: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"エラー: ファイル '{gpx_file_path}' の処理中に予期せぬエラーが発生しました: {e}", file=sys.stderr)
        return None

def main():
    args = parse_arguments()
    
    if args.verbose:
        print(f"{len(args.gpx_files)} 個のGPXファイルを処理します...", file=sys.stderr)
    
    # すべてのファイルを処理
    all_dataframes = []
    for gpx_file in args.gpx_files:
        df = process_gpx_file(gpx_file, args.verbose)
        if df is not None:
            all_dataframes.append(df)
    
    if not all_dataframes:
        print("エラー: 処理可能なGPXファイルが見つかりませんでした。", file=sys.stderr)
        sys.exit(1)
    
    # すべてのデータフレームを結合
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    if args.verbose:
        print(f"\n合計 {len(combined_df)} 個のウェイポイントを処理しました。", file=sys.stderr)
    
    # 出力処理
    if args.output:
        # ファイルに保存
        combined_df.to_csv(args.output, index=False)
        if args.verbose:
            print(f"\nデータを '{args.output}' に保存しました。", file=sys.stderr)
    else:
        # 標準出力に表示
        print(combined_df.to_csv(index=False))

if __name__ == "__main__":
    main()