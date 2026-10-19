import sqlite3
import html
import bcrypt
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
# 配置 JWT 密钥（用于签名和验证 Token）
app.config["JWT_SECRET_KEY"] = "super-secret-key-for-lab" 
jwt = JWTManager(app)

# 初始化数据库，创建用户表并插入测试用户
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
    # 使用 bcrypt 对密码进行哈希存储（绝不存明文）
    hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt())
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", hashed))
    except sqlite3.IntegrityError:
        pass 
    conn.commit()
    conn.close()

# API 1: 登录并获取 Token
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"msg": "Missing username or password"}), 400
    
    username = data['username']
    password = data['password'].encode('utf-8')
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # 【防护 SQLi】使用参数化查询 (?) 而不是直接拼接字符串
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()

    # 使用 bcrypt 验证密码，且失败时统一提示，防止暴力破解探测用户名
    if user and bcrypt.checkpw(password, user[2]):
        access_token = create_access_token(identity=str(user[0]))
        return jsonify(access_token=access_token), 200
    
    return jsonify({"msg": "Invalid username or password"}), 401

# API 2: 获取数据（受 JWT 保护）
@app.route('/api/data', methods=['GET'])
@jwt_required() # 这里的装饰器相当于验证中间件
def get_data():
    raw_data = [
        {"id": 1, "title": "Welcome", "content": "This is a test."},
        {"id": 2, "title": "Comment", "content": "<script>alert('XSS')</script> 恶意脚本。"}
    ]
    # 【防护 XSS】使用 html.escape 对返回给前端的文本进行转义
    safe_data = []
    for item in raw_data:
        safe_data.append({
            "id": item["id"],
            "title": html.escape(item["title"]),
            "content": html.escape(item["content"])
        })
    return jsonify(safe_data), 200

# API 3: 获取当前用户信息（受 JWT 保护）
@app.route('/api/me', methods=['GET'])
@jwt_required()
def get_me():
    current_user_id = get_jwt_identity()
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE id = ?", (current_user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return jsonify({"id": user[0], "username": user[1]}), 200
    return jsonify({"msg": "User not found"}), 404

if __name__ == '__main__':
    init_db()
    app.run(debug=False, port=5000)