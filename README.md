# ウェブスクレイピングツール

Python + Flask + Celery + Redis を使ったWebスクレイピングシステムです。

## 機能

- **Webサイト全体のスクレイピング**: 指定したURLから全ページを自動収集
- **Word文書出力**: スクレイピング結果をWord文書として出力
- **CSV統計出力**: ページ一覧とディレクトリ別統計をCSV形式で出力
- **リアルタイム進捗表示**: スクレイピング中の進捗を%で表示
- **ヘッダー・ナビゲーション除去**: 不要な要素を自動除去
- **画像OCR**: 画像内のテキストを抽出（オプション）
- **PDF抽出**: PDFファイルのテキストを抽出（オプション）

## Renderでのデプロイ

### 1. GitHubリポジトリ作成
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/webscraping-tool.git
git push -u origin main
```

### 2. Renderでサービス作成
1. [Render](https://render.com) にアクセス
2. GitHubアカウントでログイン
3. "New" → "Blueprint" を選択
4. GitHubリポジトリを選択
5. `render.yaml` が自動検出される
6. デプロイ開始

### 3. 環境変数設定
Renderで以下の環境変数が自動設定されます：
- `REDIS_URL`: Redis接続URL
- `PORT`: Webサーバーポート

## ローカル開発

### 必要な環境
- Python 3.8+
- Redis Server

### セットアップ
```bash
# 依存関係インストール
pip install -r requirements.txt

# Redisサーバー起動
redis-server

# Celeryワーカー起動
celery -A app.celery worker --loglevel=info

# Flaskアプリ起動
python app.py
```

## 使用方法

1. ブラウザで `http://localhost:5001` にアクセス
2. スクレイピング対象のURLを入力
3. 除外したいディレクトリパスを指定（オプション）
4. OCR・PDF抽出のON/OFFを選択
5. 「スクレイピング開始」または「ページ一覧をCSVでダウンロード」をクリック
6. 進捗を確認しながら完了を待つ
7. 完了後、ファイルをダウンロード

## 技術スタック

- **Backend**: Python, Flask
- **Task Queue**: Celery
- **Cache/Broker**: Redis
- **Web Scraping**: BeautifulSoup, Requests
- **Document Generation**: python-docx
- **Image Processing**: Pillow, pytesseract
- **PDF Processing**: PyMuPDF
- **Frontend**: HTML, CSS, JavaScript

## ライセンス

MIT License 