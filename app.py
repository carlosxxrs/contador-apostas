import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, flash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave_secreta_contador_apostas_render'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            valor REAL NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

LAYOUT = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contador de Apostas</title>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #fff; text-align: center; margin: 0; padding: 20px; }
        .card { background: #1e1e1e; max-width: 400px; margin: 20px auto; padding: 20px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        h1, h2 { color: #00e676; }
        input { width: 90%; padding: 10px; margin: 8px 0; background: #2a2a2a; border: 1px solid #333; color: #fff; border-radius: 4px; box-sizing: border-box; }
        button { width: 90%; padding: 10px; background: #00e676; border: none; font-weight: bold; cursor: pointer; border-radius: 4px; color: #121212; margin-top: 10px; font-size: 16px; }
        a { color: #00e676; text-decoration: none; }
        .flash { background: #ff5252; color: white; padding: 10px; border-radius: 4px; list-style: none; margin-bottom: 15px; }
    </style>
</head>
<body>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div style="max-width: 400px; margin: 0 auto;">
          {% for m in messages %}<p class="flash">{{ m }}</p>{% endfor %}
        </div>
      {% endif %}
    {% endwith %}
    {{ content | safe }}
</body>
</html>
"""

HOME_HTML = """
<div class="card">
    <h1>Contador de Apostas</h1>
    {% if username %}
        <p>Olá, <strong>{{ username }}</strong>! [<a href="/logout">Sair</a>]</p>
        <h2>Total de Lucros: R$ {{ "%.2f"|format(total) }}</h2>
        <form action="/adicionar_aposta" method="POST">
            <input type="number" step="0.01" name="valor" placeholder="Valor da aposta (ex: 50.00)" required>
            <button type="submit">Adicionar Aposta</button>
        </form>
    {% else %}
        <p>Faça login para gerenciar suas apostas.</p>
        <p><a href="/login"><button>Entrar</button></a></p>
        <p><a href="/register"><button style="background: #333; color: #fff;">Criar Conta</button></a></p>
    {% endif %}
</div>
"""

LOGIN_HTML = """
<div class="card">
    <h2>Entrar</h2>
    <form action="/login" method="POST">
        <input type="text" name="username" placeholder="Usuário" required>
        <input type="password" name="password" placeholder="Senha" required>
        <button type="submit">Entrar</button>
    </form>
    <p>Não tem conta? <a href="/register">Cadastre-se</a></p>
</div>
"""

REGISTER_HTML = """
<div class="card">
    <h2>Criar Conta</h2>
    <form action="/register" method="POST">
        <input type="text" name="username" placeholder="Usuário" required>
        <input type="password" name="password" placeholder="Senha" required>
        <button type="submit">Cadastrar</button>
    </form>
    <p>Já tem conta? <a href="/login">Entrar</a></p>
</div>
"""

@app.route('/')
def home():
    user_id = session.get('user_id')
    username = session.get('username')
    total = 0.0

    if user_id:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(valor) FROM apostas WHERE user_id = ?', (user_id,))
        res = cursor.fetchone()
        if res and res[0] is not None:
            total = res[0]
        conn.close()

    body = render_template_string(HOME_HTML, total=total, username=username)
    return render_template_string(LAYOUT, content=body)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        else:
            flash('Usuário ou senha incorretos.')

    body = render_template_string(LOGIN_HTML)
    return render_template_string(LAYOUT, content=body)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            session['user_id'] = cursor.lastrowid
            session['username'] = username
            flash('Conta criada com sucesso!')
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            flash('Este usuário já existe!')
        finally:
            conn.close()

    body = render_template_string(REGISTER_HTML)
    return render_template_string(LAYOUT, content=body)

@app.route('/adicionar_aposta', methods=['POST'])
def adicionar_aposta():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    valor = request.form.get('valor')
    if valor:
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO apostas (valor, user_id) VALUES (?, ?)', (float(valor), user_id))
            conn.commit()
            conn.close()
        except Exception:
            flash('Erro ao salvar aposta.')

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
