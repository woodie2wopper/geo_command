#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import sys
from typing import Dict, List, Optional, TextIO
import xml.etree.ElementTree as ET
import os

# Google Mapsの制限
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_PLACEMARKS = 2000  # 最大地点数
MAX_STYLES = 100  # 最大スタイル数

# デフォルトのKMLテンプレート
DEFAULT_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>調査地点</name>
    {styles}
    {placemarks}
  </Document>
</kml>'''

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
    else:
        coords += ",0"  # 標高が指定されていない場合は0を設定
    
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

def validate_kml_content(kml_content: str) -> None:
    """KMLの妥当性をチェックします。"""
    try:
        # XMLとしてパース可能かチェック
        root = ET.fromstring(kml_content)
        
        # KMLの名前空間を確認
        if root.tag != '{http://www.opengis.net/kml/2.2}kml':
            raise ValueError("KMLの名前空間が正しくありません。")
        
        # Document要素の存在を確認
        document = root.find('{http://www.opengis.net/kml/2.2}Document')
        if document is None:
            raise ValueError("Document要素が見つかりません。")
        
        # ファイルサイズのチェック
        if len(kml_content.encode('utf-8')) > MAX_FILE_SIZE:
            raise ValueError(f"KMLファイルのサイズが大きすぎます（最大 {MAX_FILE_SIZE/1024/1024}MB）。")
        
        # Placemarkの数をチェック
        placemarks = document.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
        if len(placemarks) > MAX_PLACEMARKS:
            raise ValueError(f"地点の数が多すぎます（最大 {MAX_PLACEMARKS} 地点）。")
        
        # Styleの数をチェック
        styles = document.findall('.//{http://www.opengis.net/kml/2.2}Style')
        if len(styles) > MAX_STYLES:
            raise ValueError(f"スタイルの数が多すぎます（最大 {MAX_STYLES} スタイル）。")
            
    except ET.ParseError as e:
        raise ValueError(f"XMLの形式が不正です: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='CSVファイルからKMLファイルを生成します。')
    parser.add_argument('--input-csv', '-ic', action='append', nargs='*',
                      help='入力CSVファイルのパス（複数指定可能、省略時は標準入力から読み込み）')
    parser.add_argument('--input-template', '-it',
                      help='カスタムKMLテンプレートファイルのパス')
    parser.add_argument('--output', '-o',
                      help='出力ファイルのパス（指定しない場合は標準出力）')
    parser.add_argument('--validate', '-v', action='store_true',
                      help='KMLの妥当性チェックを実行（デフォルト: 有効）')
    parser.add_argument('--no-validate', action='store_true',
                      help='KMLの妥当性チェックを無効化')

    args = parser.parse_args()

    # 入力ソースの確認と標準入力の設定
    if not args.input_csv:
        args.input_csv = ['-']  # 標準入力をデフォルトとして設定

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

    # KMLの妥当性チェック
    if not args.no_validate:
        try:
            validate_kml_content(kml_content)
            print("KMLの妥当性チェックが完了しました。", file=sys.stderr)
        except ValueError as e:
            print(f"エラー: {str(e)}", file=sys.stderr)
            sys.exit(4)

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
