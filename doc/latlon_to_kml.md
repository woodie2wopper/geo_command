# lanlng_to_kml.py 仕様書

## 概要
`lanlng_to_kml.py` は、CSVファイルに含まれる地名（`name`）、緯度（`lat`）、経度（`lon`）の情報をもとに、KML（Keyhole Markup Language）フォーマットのXMLファイルを生成するPythonスクリプトです。生成されたKMLファイルは、Google EarthやGoogle Mapsなどで地図上に地点をプロットするために使用できます。

## 機能
- CSVファイルから地点情報（`name`, `lat`, `lon`）を読み取る。
- 読み取った情報をKMLフォーマットに変換。
- 変換後のKMLファイルを標準出力または指定されたファイルに出力。

## 入力
1. **CSVファイル**
   - 入力としてCSVファイルを使用。
   - CSVファイルのフォーマットは以下の通り：
     ```
     name,lat,lon[,elevation][,color]
     ```
   - `name`: 地点の名前（文字列）
   - `lat`: 地点の緯度（数値）
   - `lon`: 地点の経度（数値）
   - `elevation`: 標高（オプション、数値、メートル単位）
   - `color`: アイコンの色（オプション、16進数カラーコード）

   **例:**
   ```csv
   name,lat,lon,elevation,color
   観察地点1,35.6585,139.7454,100.5,ff0000ff
   観察地点2,35.6586,139.7514,150.2,ffff0000
   ```

2. **KMLテンプレート（オプション）**
   - カスタムKMLテンプレートを指定可能
   - 指定しない場合はデフォルトテンプレートを使用

## 出力
- **KMLファイル**
  - 出力はデフォルトで標準出力
  - オプションでファイル出力も可能
  - KMLファイルの構造において、各地点が`<Placemark>`タグで表現され、`<coordinates>`タグ内に経度と緯度が記載されます。
  
  **例:**
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <KML xmlns="http://www.opengis.net/kml/2.2">
    <Document>
      <name>調査地点</name>
      
      <Placemark>
        <name>観察地点1</name>
        <Point>
          <coordinates>139.7454,35.6585</coordinates>
        </Point>
      </Placemark>
      
      <Placemark>
        <name>観察地点2</name>
        <Point>
          <coordinates>139.7514,35.6586</coordinates>
        </Point>
      </Placemark>
    </Document>
  </KML>
  ```

## 使用方法

### コマンドライン引数
```bash
python script/latlon_to_kml.py [オプション]
```

#### オプション
- `--input-csv`, `-ic`: 入力CSVファイルのパス（必須、複数指定可能、-を指定すると標準入力から読み込み）
- `--input-template`, `-it`: カスタムKMLテンプレートファイルのパス（オプション）
- `--output`, `-o`: 出力ファイルのパス（オプション、指定しない場合は標準出力）

#### 使用例
```bash
# 基本的な使用方法（標準出力）
python script/latlon_to_kml.py --input-csv tests/latlon_to_kml/normal_data.csv

# 複数のCSVファイルを指定
python script/latlon_to_kml.py --input-csv tests/latlon_to_kml/normal_data.csv --input-csv tests/latlon_to_kml/second_data.csv

# カスタムテンプレートと出力ファイルを指定
python script/latlon_to_kml.py --input-csv tests/latlon_to_kml/normal_data.csv --input-template custom_template.xml --output output.kml

# 短いオプション名を使用
python script/latlon_to_kml.py -ic tests/latlon_to_kml/normal_data.csv -ic tests/latlon_to_kml/second_data.csv -o output.kml

# 標準入力から読み込み（テストデータを使用）
cat tests/latlon_to_kml/normal_data.csv | python script/latlon_to_kml.py -ic - -o stdin_output.kml

# ファイルと標準入力の組み合わせ（テストデータを使用）
cat tests/latlon_to_kml/second_data.csv | python script/latlon_to_kml.py -ic tests/latlon_to_kml/normal_data.csv -ic - -o combined_output.kml

# エラーデータの標準入力テスト
cat tests/latlon_to_kml/error_data.csv | python script/latlon_to_kml.py -ic - -o error_output.kml 2> error.log
```

## プログラムの詳細

1. **コマンドライン引数の処理**:
   - `argparse`モジュールを使用して、コマンドライン引数を処理します。

2. **CSVファイルの読み込み**:
   - `csv.DictReader`を使用して、CSVファイルを読み込みます。各行の`name`, `lat`, `lon`のデータを辞書として処理します。

3. **KMLテンプレートの読み込み**:
   - 指定されたテンプレートファイルを読み込みます。
   - テンプレートが指定されていない場合は、デフォルトテンプレートを使用します。

4. **Placemarkタグの作成**:
   - `create_placemark()`関数により、各地点の`<Placemark>`タグを動的に生成します。

5. **KMLファイルの出力**:
   - 指定された出力ファイルに書き込むか、標準出力に出力します。

## デフォルトKMLテンプレート
```xml
<?xml version="1.0" encoding="UTF-8"?>
<KML xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>調査地点</name>
    {styles}
    {placemarks}
  </Document>
</KML>
```

## アイコン設定
- アイコンの色は以下の優先順位で決定されます：
  1. CSVファイルの`color`列で指定された色（各地点ごとに個別に指定可能）
  2. デフォルトの色（赤 #ff0000ff）

- 色の指定方法：
  - 16進数カラーコード（例: ff0000ff）
  - 最初の2桁: アルファ値（透明度）
  - 次の2桁: 青
  - 次の2桁: 緑
  - 最後の2桁: 赤

## 標高の扱い
- 標高（elevation）が指定された場合、coordinatesタグに標高値が追加されます。
- 標高の単位はメートルです。
- 標高が指定されていない場合は、0として扱われます。

## 複数CSVファイルの合成
- 複数のCSVファイルを指定して、1つのKMLファイルに合成できます。
- 各CSVファイルのアイコン色は、CSVファイルの`color`列で指定された色を使用します。
- `color`列が指定されていない場合は、デフォルトの色（赤 #ff0000ff）を使用します。

## 出力例（複数CSVファイルの場合）
```xml
<?xml version="1.0" encoding="UTF-8"?>
<KML xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>調査地点（複数データセット）</name>

    <!-- スタイル設定 -->
    <Style id="icon1">
      <IconStyle>
        <color>ff0000ff</color>
        <scale>1.0</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/paddle/red-circle.png</href>
        </Icon>
      </IconStyle>
    </Style>

    <Style id="icon2">
      <IconStyle>
        <color>ffff0000</color>
        <scale>1.0</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/paddle/blue-circle.png</href>
        </Icon>
      </IconStyle>
    </Style>

    <!-- 地点情報（データセット1） -->
    <Placemark>
      <name>観察地点1（データセット1）</name>
      <styleUrl>#icon1</styleUrl>
      <Point>
        <coordinates>139.7454,35.6585,100.5</coordinates>
      </Point>
    </Placemark>

    <!-- 地点情報（データセット2） -->
    <Placemark>
      <name>観察地点1（データセット2）</name>
      <styleUrl>#icon2</styleUrl>
      <Point>
        <coordinates>139.7514,35.6586,150.2</coordinates>
      </Point>
    </Placemark>
  </Document>
</KML>
```

## テスト
プログラムの動作を確認するため、以下のテストを実装します：

1. **基本的なテストケース**
   - 正常なCSVファイルからKMLを生成
   - 複数のCSVファイルを合成
   - 色の指定（CSVのcolor列）
   - 標準入力からの読み込み

2. **テストデータ**
   - テストデータは `tests/latlon_to_kml/` ディレクトリに配置されています：
     - `normal_data.csv`: 正常系のテストデータ
     - `error_data.csv`: 異常系のテストデータ
     - `second_data.csv`: 複数CSVファイルの合成テスト用データ

3. **テスト実行方法**
   ```bash
   # 基本的なテスト
   python script/latlon_to_kml.py -ic tests/latlon_to_kml/normal_data.csv -o output.kml

   # エラーハンドリングテスト
   python script/latlon_to_kml.py -ic tests/latlon_to_kml/error_data.csv -o output.kml

   # 複数CSVファイルの合成テスト
   python script/latlon_to_kml.py -ic tests/latlon_to_kml/normal_data.csv -ic tests/latlon_to_kml/second_data.csv -o output.kml

   # 標準入力からの読み込みテスト
   cat tests/latlon_to_kml/normal_data.csv | python script/latlon_to_kml.py -ic - -o stdin_output.kml

   # ファイルと標準入力の組み合わせテスト
   cat tests/latlon_to_kml/second_data.csv | python script/latlon_to_kml.py -ic tests/latlon_to_kml/normal_data.csv -ic - -o combined_output.kml

   # エラーデータの標準入力テスト
   cat tests/latlon_to_kml/error_data.csv | python script/latlon_to_kml.py -ic - -o error_output.kml 2> error.log
   ```

4. **出力の検証**
   - 生成されたKMLファイルの構造が正しいこと
   - 指定された色が正しく反映されていること
   - 複数CSVファイルが正しく合成されていること
   - 標準入力からのデータが正しく処理されていること

## エラーハンドリング
プログラムは以下のエラーケースを適切に処理します：

1. **入力ファイル関連のエラー**
   - CSVファイルが存在しない場合
     - エラーメッセージ: "エラー: 入力ファイル '{ファイルパス}' が見つかりません。"
     - 終了コード: 1
   - CSVファイルの読み取り権限がない場合
     - エラーメッセージ: "エラー: 入力ファイル '{ファイルパス}' の読み取り権限がありません。"
     - 終了コード: 1
   - テンプレートファイルが存在しない場合
     - エラーメッセージ: "エラー: テンプレートファイル '{ファイルパス}' が見つかりません。"
     - 終了コード: 1

2. **CSVフォーマット関連のエラー**
   - 必須フィールド（name, lat, lon）が欠けている場合
     - エラーメッセージ: "エラー: CSVファイルに必須フィールド '{フィールド名}' がありません。"
     - 終了コード: 2
   - 緯度経度の値が不正な場合
     - エラーメッセージ: "エラー: 行 {行番号} の緯度経度の値が不正です。"
     - 終了コード: 2
   - 色の指定が不正な場合
     - エラーメッセージ: "エラー: 行 {行番号} の色の指定が不正です。"
     - 終了コード: 2

3. **出力関連のエラー**
   - 出力ファイルの書き込み権限がない場合
     - エラーメッセージ: "エラー: 出力ファイル '{ファイルパス}' の書き込み権限がありません。"
     - 終了コード: 3

## ログ出力
プログラムは以下の情報をログとして出力します：

1. **標準出力（stdout）**
   - 処理の開始
     ```
     処理を開始します: {入力ファイル数} 個のCSVファイルを処理します。
     ```
   - 各CSVファイルの処理状況
     ```
     {ファイル名} を処理中... ({現在の行数}/{総行数} 行)
     ```
   - 処理の完了
     ```
     処理が完了しました: {出力ファイル名}
     ```

2. **標準エラー（stderr）**
   - 警告メッセージ
     ```
     警告: {警告内容}
     ```
   - エラーメッセージ
     ```
     エラー: {エラー内容}
     ```

3. **ログレベル**
   - INFO: 通常の処理情報
   - WARNING: 警告（処理は継続）
   - ERROR: エラー（処理を中断）

## XML検証ツール
生成されたKMLファイルの妥当性を確認するために、以下のツールを使用できます。

### 1. xmllint（libxml2）
XMLの妥当性をチェックする基本的なツールです。

#### インストール方法（macOS）
```bash
brew install libxml2
```

#### 使用方法
```bash
# 基本的なXML妥当性チェック
xmllint --noout output.kml

# スキーマ検証（KMLスキーマを使用）
xmllint --schema http://schemas.opengis.net/kml/2.2.0/ogckml22.xsd --noout output.kml
```

### 2. xmlstarlet
XMLの操作と検証が可能な多機能ツールです。

#### インストール方法（macOS）
```bash
brew install xmlstarlet
```

#### 使用方法
```bash
# XML妥当性チェック
xmlstarlet val output.kml

# 特定の要素の数をカウント（名前空間を指定）
xmlstarlet sel -N kml="http://www.opengis.net/kml/2.2" -t -c "count(//kml:Placemark)" -n output.kml
xmlstarlet sel -N kml="http://www.opengis.net/kml/2.2" -t -c "count(//kml:Style)" -n output.kml

# 特定の要素の数をカウント（名前空間を指定せず）
xmlstarlet sel -t -c "count(//*[local-name()='Placemark'])" -n output.kml
xmlstarlet sel -t -c "count(//*[local-name()='Style'])" -n output.kml

# 名前空間の確認
xmlstarlet sel -t -c "//*[local-name()='KML']" -n output.kml
```

### 3. Pythonのlxmlライブラリ
PythonでXMLの検証を行う場合に使用します。

#### インストール方法
```bash
pip install lxml
```

#### 使用方法
```python
from lxml import etree

def validate_kml(file_path):
    try:
        # XMLとしてパース
        tree = etree.parse(file_path)
        
        # KMLの名前空間を確認
        root = tree.getroot()
        if root.tag != '{http://www.opengis.net/kml/2.2}KML':
            print("エラー: KMLの名前空間が正しくありません。")
            return False
        
        # ファイルサイズをチェック
        file_size = os.path.getsize(file_path)
        if file_size > 5 * 1024 * 1024:  # 5MB
            print(f"警告: ファイルサイズが大きすぎます（{file_size/1024/1024:.2f}MB）")
        
        # Placemarkの数をカウント
        placemarks = tree.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
        if len(placemarks) > 2000:
            print(f"警告: 地点の数が多すぎます（{len(placemarks)}地点）")
        
        # Styleの数をカウント
        styles = tree.findall('.//{http://www.opengis.net/kml/2.2}Style')
        if len(styles) > 100:
            print(f"警告: スタイルの数が多すぎます（{len(styles)}スタイル）")
        
        print("KMLファイルは有効です。")
        return True
        
    except etree.XMLSyntaxError as e:
        print(f"エラー: XMLの形式が不正です: {str(e)}")
        return False
    except Exception as e:
        print(f"エラー: {str(e)}")
        return False
```

### 4. 検証スクリプト
以下のシェルスクリプトを使用して、KMLファイルの総合的な検証を行うことができます。

```bash
#!/bin/bash

# 色付き出力のための関数
print_error() {
    echo -e "\033[31mエラー: $1\033[0m"
}

print_warning() {
    echo -e "\033[33m警告: $1\033[0m"
}

print_success() {
    echo -e "\033[32m$1\033[0m"
}

# 引数のチェック
if [ $# -ne 1 ]; then
    echo "使用方法: $0 <kmlファイル>"
    exit 1
fi

KML_FILE=$1

# ファイルの存在チェック
if [ ! -f "$KML_FILE" ]; then
    print_error "ファイルが見つかりません: $KML_FILE"
    exit 1
fi

# 1. 基本的なXML妥当性チェック
echo "1. XML妥当性チェック..."
if xmllint --noout "$KML_FILE" 2>/dev/null; then
    print_success "XMLの形式は有効です。"
else
    print_error "XMLの形式が不正です。"
    exit 1
fi

# 2. ファイルサイズチェック
echo "2. ファイルサイズチェック..."
FILE_SIZE=$(stat -f%z "$KML_FILE")
MAX_SIZE=$((5 * 1024 * 1024))  # 5MB
if [ "$FILE_SIZE" -gt "$MAX_SIZE" ]; then
    print_warning "ファイルサイズが大きすぎます（$((FILE_SIZE/1024/1024))MB）"
else
    print_success "ファイルサイズは適切です（$((FILE_SIZE/1024))KB）。"
fi

# 3. Placemarkの数チェック
echo "3. Placemarkの数チェック..."
PLACEMARK_COUNT=$(xmlstarlet sel -N kml="http://www.opengis.net/kml/2.2" -t -c "count(//kml:Placemark)" -n "$KML_FILE" 2>/dev/null)
MAX_PLACEMARKS=2000
if [ "$PLACEMARK_COUNT" -gt "$MAX_PLACEMARKS" ]; then
    print_warning "地点の数が多すぎます（$PLACEMARK_COUNT地点）"
else
    print_success "地点の数は適切です（$PLACEMARK_COUNT地点）。"
fi

# 4. Styleの数チェック
echo "4. Styleの数チェック..."
STYLE_COUNT=$(xmlstarlet sel -N kml="http://www.opengis.net/kml/2.2" -t -c "count(//kml:Style)" -n "$KML_FILE" 2>/dev/null)
MAX_STYLES=100
if [ "$STYLE_COUNT" -gt "$MAX_STYLES" ]; then
    print_warning "スタイルの数が多すぎます（$STYLE_COUNTスタイル）"
else
    print_success "スタイルの数は適切です（$STYLE_COUNTスタイル）。"
fi

# 5. 名前空間チェック
echo "5. 名前空間チェック..."
if xmlstarlet sel -t -c "//*[local-name()='KML']" -n "$KML_FILE" 2>/dev/null | grep -q "http://www.opengis.net/kml/2.2"; then
    print_success "KMLの名前空間は正しいです。"
else
    print_error "KMLの名前空間が正しくありません。"
    exit 1
fi

print_success "すべてのチェックが完了しました。"
```

このスクリプトを`check_kml.sh`として保存し、実行権限を付与して使用します：

```bash
chmod +x check_kml.sh
./check_kml.sh output.kml
```

