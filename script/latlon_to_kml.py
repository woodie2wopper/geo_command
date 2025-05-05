#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import sys
from typing import Dict, List, Optional, TextIO
import xml.etree.ElementTree as ET

# デフォルトのKMLテンプレート
DEFAULT_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<KML xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>調査地点</name>
    {styles}
    {placemarks}
  </Document>
</KML>'''

def validate_lat_lon(lat: float, lon: float) -> bool:
    """緯度経度の値が有効かどうかを検証します。"""
    return -90 <= lat <= 90 and -180 <= lon <= 180

def validate_color(color: str) -> bool:
    """色コードが有効かどうかを検証します。"""
    if not color or len(color) != 8:
        return False
    try:
        int(color, 16)
        return True
    except ValueError:
        return False

def create_style(color: str) -> str:
    """アイコンのスタイルを生成します。"""
    return f'''
    <Style id="icon{color}">
      <IconStyle>
        <color>{color}</color>
        <scale>1.0</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/paddle/red-circle.png</href>
        </Icon>
      </IconStyle>
    </Style>'''

def create_placemark(name: str, lat: float, lon: float, elevation: Optional[float] = None, color: Optional[str] = None) -> str:
    """Placemarkタグを生成します。"""
    coords = f"{lon},{lat}"
    if elevation is not None:
        coords += f",{elevation}"
    
    style_url = f'<styleUrl>#icon{color}</styleUrl>' if color else ''
    
    return f'''
    <Placemark>
      <name>{name}</name>
      {style_url}
      <Point>
        <coordinates>{coords}</coordinates>
      </Point>
    </Placemark>'''

def process_csv_reader(reader: csv.DictReader, source_name: str = "標準入力") -> tuple[List[str], List[str]]:
    """CSVリーダーを処理し、スタイルとPlacemarkを生成します。"""
    styles = []
    placemarks = []
    used_colors = set()

    # 必須フィールドの確認
    required_fields = ['name', 'lat', 'lon']
    if not all(field in reader.fieldnames for field in required_fields):
        print(f"エラー: CSVファイルに必須フィールドがありません。", file=sys.stderr)
        sys.exit(2)

    for row_num, row in enumerate(reader, 2):  # ヘッダ行を考慮して2から開始
        try:
            name = row['name']
            lat = float(row['lat'])
            lon = float(row['lon'])
            
            if not validate_lat_lon(lat, lon):
                print(f"エラー: {source_name} の行 {row_num} の緯度経度の値が不正です。", file=sys.stderr)
                sys.exit(2)

            elevation = float(row['elevation']) if 'elevation' in row and row['elevation'] else None
            color = row['color'].strip() if 'color' in row and row['color'] else None

            if color and not validate_color(color):
                print(f"エラー: {source_name} の行 {row_num} の色の指定が不正です。", file=sys.stderr)
                sys.exit(2)

            if color and color not in used_colors:
                styles.append(create_style(color))
                used_colors.add(color)

            placemarks.append(create_placemark(name, lat, lon, elevation, color))

        except ValueError as e:
            print(f"エラー: {source_name} の行 {row_num} のデータが不正です。", file=sys.stderr)
            sys.exit(2)

    return styles, placemarks

def process_csv_file(csv_file: str) -> tuple[List[str], List[str]]:
    """CSVファイルを処理し、スタイルとPlacemarkを生成します。"""
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return process_csv_reader(reader, csv_file)
    except FileNotFoundError:
        print(f"エラー: 入力ファイル '{csv_file}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"エラー: 入力ファイル '{csv_file}' の読み取り権限がありません。", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='CSVファイルからKMLファイルを生成します。')
    parser.add_argument('--input-csv', '-ic', action='append', nargs='?', const='-',
                      help='入力CSVファイルのパス（複数指定可能、-を指定すると標準入力から読み込み）')
    parser.add_argument('--input-template', '-it',
                      help='カスタムKMLテンプレートファイルのパス')
    parser.add_argument('--output', '-o',
                      help='出力ファイルのパス（指定しない場合は標準出力）')

    args = parser.parse_args()

    # 入力ソースの確認
    if not args.input_csv:
        print("エラー: 入力ソースが指定されていません。", file=sys.stderr)
        sys.exit(1)

    # テンプレートの読み込み
    template = DEFAULT_TEMPLATE
    if args.input_template:
        try:
            with open(args.input_template, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            print(f"エラー: テンプレートファイル '{args.input_template}' が見つかりません。", file=sys.stderr)
            sys.exit(1)
        except PermissionError:
            print(f"エラー: テンプレートファイル '{args.input_template}' の読み取り権限がありません。", file=sys.stderr)
            sys.exit(1)

    # 処理の開始
    input_count = len(args.input_csv)
    print(f"処理を開始します: {input_count} 個の入力ソースを処理します。", file=sys.stderr)

    all_styles = []
    all_placemarks = []

    # 各入力ソースを処理
    for input_source in args.input_csv:
        if input_source == '-':
            print("標準入力から読み込み中...", file=sys.stderr)
            reader = csv.DictReader(sys.stdin)
            styles, placemarks = process_csv_reader(reader)
        else:
            print(f"{input_source} を処理中...", file=sys.stderr)
            styles, placemarks = process_csv_file(input_source)
        
        all_styles.extend(styles)
        all_placemarks.extend(placemarks)

    # KMLファイルの生成
    kml_content = template.format(
        styles=''.join(all_styles),
        placemarks=''.join(all_placemarks)
    )

    # 出力
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(kml_content)
            print("処理が完了しました。", file=sys.stderr)
        except PermissionError:
            print(f"エラー: 出力ファイル '{args.output}' の書き込み権限がありません。", file=sys.stderr)
            sys.exit(3)
    else:
        print(kml_content)

if __name__ == '__main__':
    main()
