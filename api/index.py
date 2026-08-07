import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

# Localiza a pasta 'templates' na raiz
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave_secreta_contador_apostas')

# Configuração da URL do Banco de Dados PostgreSQL (Neon)
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS DO BANCO DE DADOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Aposta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Função para criar tabelas no Neon automaticamente
def init_db():
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        print(f"Erro no banco: {e}")

init_db()

# --- ROTAS ---

@app.route('/')
def home():
    user_id = session.get('user_id')
    total_apostas = 0.0
    
    if user_id:
        try:
            apostas = Aposta.query.filter_by(user_id=user_id).all()
            total_apostas = sum(a.valor for a in apostas)
        except Exception:
            db.session.rollback()
    
    try:
        return render_template('index.html', total=total_apostas, user_id=user_id)
    except Exception:
        return render_template('home.html', total=total_apostas, user_id=user_id)

@app.route('/adicionar_aposta', methods=['POST'])
def adicionar_aposta():
    user_id = session.get('user_id')
    if not user_id:
        flash('Faça login para adicionar apostas!')
        return redirect(url_for('login'))

    valor = request.form.get('valor') or request.form.get('amount')
    if valor:
        try:
            nova_aposta = Aposta(valor=float(valor), user_id=user_id)
            db.session.add(nova_aposta)
            db.session.commit()
        except Exception:
            db.session.rollback()

    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            user = User.query.filter_by(username=username, password=password).first()
            if user:
                session['user_id'] = user.id
                session['username'] = user.username
                return redirect(url_for('home'))
            flash('Usuário ou senha incorretos.')
        except Exception:
            db.session.rollback()
            flash('Erro ao consultar usuário.')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            init_db()
            if User.query.filter_by(username=username).first():
                flash('Usuário já existe!')
                return redirect(url_for('register'))
                
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            session['username'] = new_user.username
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar conta. Tente novamente.')
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    return '', 204

app = app
