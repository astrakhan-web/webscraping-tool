from flask import Flask, render_template, request, send_file, jsonify
import os
from datetime import datetime
from scrape import scrape_website, list_all_urls, list_all_urls_with_stats
from urllib.parse import urlparse
import threading
import time

app = Flask(__name__)

# CORSの設定を追加
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 出力ディレクトリの作成
UPLOAD_FOLDER = 'outputs'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# タスクの状態を管理する辞書
task_status = {}

@app.route('/')
def index():
    return render_template('index.html')

def run_scrape_task(task_id, url, exclude_paths, enable_ocr, enable_pdf, include_only_prefix):
    """バックグラウンドでスクレイピングを実行する関数"""
    try:
        task_status[task_id] = {'status': 'processing', 'done': 0, 'total': 0}
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(UPLOAD_FOLDER, f'scraped_{timestamp}.docx')
        
        def progress_callback(done, total):
            task_status[task_id].update({'done': done, 'total': total})
        
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
        task_status[task_id] = {'status': 'completed', 'file_path': result}
    except Exception as e:
        task_status[task_id] = {'status': 'failed', 'error': str(e)}

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
        
        # タスクIDを生成
        task_id = f"task_{int(time.time() * 1000)}"
        
        # バックグラウンドでスクレイピングを開始
        thread = threading.Thread(
            target=run_scrape_task,
            args=(task_id, url, exclude_paths_list, enable_ocr, enable_pdf, include_only_prefix)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'task_id': task_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<task_id>', methods=['GET', 'OPTIONS'])
def get_status(task_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if task_id not in task_status:
            return jsonify({'error': 'タスクが見つかりません'}), 404
            
        status = task_status[task_id]
        return jsonify(status)
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

def run_list_urls_task(task_id, url, exclude_paths, include_only_prefix):
    """バックグラウンドでURL一覧取得を実行する関数"""
    try:
        task_status[task_id] = {'status': 'processing', 'done': 0, 'total': 0}
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(UPLOAD_FOLDER, f'all_urls_{timestamp}.csv')
        
        def progress_callback(done, total):
            task_status[task_id].update({'done': done, 'total': total})
            
        result = list_all_urls_with_stats(
            url,
            output_file,
            exclude_paths=exclude_paths,
            include_only_prefix=include_only_prefix,
            progress_callback=progress_callback
        )
        task_status[task_id] = {'status': 'completed', 'file_path': result}
    except Exception as e:
        task_status[task_id] = {'status': 'failed', 'error': str(e)}

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
        
        # タスクIDを生成
        task_id = f"task_{int(time.time() * 1000)}"
        
        # バックグラウンドでURL一覧取得を開始
        thread = threading.Thread(
            target=run_list_urls_task,
            args=(task_id, url, exclude_paths_list, include_only_prefix)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'task_id': task_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port) 