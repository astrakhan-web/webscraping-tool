from flask import Flask, render_template, request, send_file, jsonify
from celery import Celery, current_task
import os
from datetime import datetime
from scrape import scrape_website, list_all_urls, list_all_urls_with_stats  # 既存のスクレイピング関数をインポート
from urllib.parse import urlparse

app = Flask(__name__)

# CORSの設定を追加
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Celeryの設定 - 環境変数からRedis URLを取得
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
app.config['CELERY_BROKER_URL'] = redis_url
app.config['CELERY_RESULT_BACKEND'] = redis_url

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# 出力ディレクトリの作成
UPLOAD_FOLDER = 'outputs'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@celery.task(bind=True)
def scrape_task(self, url, exclude_paths, enable_ocr, enable_pdf, include_only_prefix):
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(UPLOAD_FOLDER, f'scraped_{timestamp}.docx')
        
        def progress_callback(done, total):
            self.update_state(state='PROGRESS', meta={'done': done, 'total': total})
        
        # スクレイピング実行
        result = scrape_website(
            url,
            output_file,
            exclude_paths=exclude_paths,
            enable_ocr=enable_ocr,
            enable_pdf=enable_pdf,
            include_only_prefix=include_only_prefix,
            progress_callback=progress_callback
        )
        return {'status': 'completed', 'file_path': result}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}

@app.route('/scrape', methods=['POST', 'OPTIONS'])
def start_scrape():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        url = request.form.get('url')
        exclude_paths = request.form.get('exclude_paths', '')
        enable_ocr = request.form.get('enable_ocr', 'off') == 'on'
        enable_pdf = request.form.get('enable_pdf', 'off') == 'on'
        if not url:
            return jsonify({'error': 'URLが指定されていません'}), 400
        exclude_paths_list = [p.strip() for p in exclude_paths.split(',') if p.strip()]
        # URLのパス部分を自動的にinclude_only_prefixに
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        include_only_prefix = [path] if path else []
        task = scrape_task.delay(url, exclude_paths_list, enable_ocr, enable_pdf, include_only_prefix)
        return jsonify({'task_id': task.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<task_id>', methods=['GET', 'OPTIONS'])
def get_status(task_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        task = celery.AsyncResult(task_id)
        if task.ready():
            if task.successful():
                result = task.result
                return jsonify(result) if isinstance(result, dict) else jsonify({'status': 'completed', 'file_path': result})
            else:
                return jsonify({
                    'status': 'failed',
                    'error': str(task.result)
                })
        # 進捗情報を返す
        meta = task.info if task.info else {}
        return jsonify({'status': 'processing', **meta})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>', methods=['GET', 'OPTIONS'])
def download_file(filename):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@celery.task(bind=True)
def list_urls_task(self, url, exclude_paths, include_only_prefix):
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(UPLOAD_FOLDER, f'all_urls_{timestamp}.csv')
        def progress_callback(done, total):
            self.update_state(state='PROGRESS', meta={'done': done, 'total': total})
        result = list_all_urls_with_stats(
            url,
            output_file,
            exclude_paths=exclude_paths,
            include_only_prefix=include_only_prefix,
            progress_callback=progress_callback
        )
        return output_file
    except Exception as e:
        return None

@app.route('/list_urls', methods=['POST', 'OPTIONS'])
def list_urls():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        url = request.form.get('url')
        exclude_paths = request.form.get('exclude_paths', '')
        if not url:
            return jsonify({'error': 'URLが指定されていません'}), 400
        exclude_paths_list = [p.strip() for p in exclude_paths.split(',') if p.strip()]
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        include_only_prefix = [path] if path else []
        task = list_urls_task.apply_async(args=[url, exclude_paths_list, include_only_prefix])
        return jsonify({'task_id': task.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port) 