import os
import sqlite3
import hashlib
import time
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import CSRFProtect
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- 設定 ---
app.config['SECRET_KEY'] = 'dev-key-kUjneiQj84jUhfskI9hehSzqp92' # CSRF用の秘密鍵
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB制限
DATABASE = 'database.db'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

csrf = CSRFProtect(app)

# --- データベース関連の関数 ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        conn.execute('''
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, brand TEXT,
                current_side TEXT, current_size TEXT,
                wanted_side TEXT, wanted_size TEXT,
                condition TEXT, description TEXT,
                image TEXT, status TEXT
            )
        ''')
        conn.commit()
        conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ルート定義 ---
@app.route('/')
def index():
    init_db()  # アクセスされた時にテーブルがなければ作るようにします
    search_size = request.args.get('search_size')
    conn = get_db_connection()
    if search_size:
        posts = conn.execute('SELECT * FROM posts WHERE wanted_size = ? ORDER BY id DESC', (search_size,)).fetchall()
    else:
        posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('index.html', posts=posts, search_size=search_size)

@app.route('/post', methods=['POST'])
def post():
    file = request.files.get('image')
    image_filename = None
    
    # 画像保存とバリデーション
    if file and allowed_file(file.filename):
        extension = file.filename.rsplit('.', 1)[1].lower()
        hash_name = hashlib.sha256(f"{file.filename}{time.time()}".encode()).hexdigest()
        image_filename = f"{hash_name}.{extension}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    # DB保存
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO posts (category, brand, current_side, current_size, wanted_side, wanted_size, condition, description, image, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        request.form.get('category'), request.form.get('brand'),
        request.form.get('current_side'), request.form.get('current_size'),
        request.form.get('wanted_side'), request.form.get('wanted_size'),
        request.form.get('condition'), request.form.get('description'),
        image_filename, '募集中'
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/complete/<int:post_id>')
def complete(post_id):
    conn = get_db_connection()
    conn.execute('UPDATE posts SET status = ? WHERE id = ?', ('成立済み', post_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.errorhandler(413)
def error_413(e):
    return "ファイルが大きすぎます(最大2MB)", 413

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db()
    
    # Renderなどの環境では、環境変数 PORT を使って起動する必要があります
    # なければ 5000 番を使います
    port = int(os.environ.get("PORT", 5000))
    # 0.0.0.0 は「外部からの接続をすべて許可する」設定です
    app.run(host="0.0.0.0", port=port)
    