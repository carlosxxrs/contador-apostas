import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session, flash

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.config['SECRET_KEY'] = 'chave_super_secreta_contador'

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db():
    if not DATABASE_URL:
        return None
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)

def init_db():
    conn = get_db()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(80) UNIQUE NOT NULL,
                        password VARCHAR(120) NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS apostas (
                        id SERIAL PRIMARY KEY,
                        valor FLOAT NOT NULL,
                        user_id INT REFERENCES users(id) ON DELETE CASCADE
                    );
                """)
                conn.commit()
        except Exception as e:
            conn.rollback()
        finally:
            conn.close()

# Executa criação de tabelas
init_db()

@app.route('/')
def home():
    user_id = session.get('user_id')
    username = session.get('username')
    total = 0.0

    if user_id:
        conn = get_db()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT SUM(valor) FROM apostas WHERE user_id = %s;", (user_id,))
                    res = cur.fetchone()
                    if res and res[0] is not None:
                        total = res[0]
            except Exception:
                pass
            finally:
                conn.close()

    try:
        return render_template('index.html', total=total, username=username, user_id=user_id)
    except:
        return render_template('home.html', total=total, username=username, user_id=user_id)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username') or request.form.get('usuario')
        password = request.form.get('password') or request.form.get('senha')

        if not username or not password:
            flash('Preencha todos os campos!')
            return render_template('register.html')

        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados (DATABASE_URL ausente).')
            return render_template('register.html')

        try:
            init_db()
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id;", (username, password))
                user_id = cur.fetchone()[0]
                conn.commit()
                
                session['user_id'] = user_id
                session['username'] = username
                flash('Conta criada com sucesso!')
                return redirect(url_for('home'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Este usuário já existe!')
        except Exception as e:
            conn.rollback()
            flash('Erro ao cadastrar. Tente novamente.')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username') or request.form.get('usuario')
        password = request.form.get('password') or request.form.get('senha')

        conn = get_db()
        if conn:
            try:
                init_db()
                with conn.cursor() as cur:
                    cur.execute("SELECT id, username FROM users WHERE username = %s AND password = %s;", (username, password))
                    user = cur.fetchone()
                    if user:
                        session['user_id'] = user[0]
                        session['username'] = user[1]
                        return redirect(url_for('home'))
                    else:
                        flash('Usuário ou senha incorretos.')
            except Exception:
                conn.rollback()
            finally:
                conn.close()

    return render_template('login.html')

@app.route('/adicionar_aposta', methods=['POST'])
def adicionar_aposta():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    valor = request.form.get('valor') or request.form.get('amount')
    if valor:
        conn = get_db()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO apostas (valor, user_id) VALUES (%s, %s);", (float(valor), user_id))
                    conn.commit()
            except Exception:
                conn.rollback()
            finally:
                conn.close()

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    return '', 204

app = app
