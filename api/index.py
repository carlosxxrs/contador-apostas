import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

# Localiza a pasta 'templates' situada na raiz do projeto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua_chave_secreta_aqui')

# Configuração da URL do Banco de Dados PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Fallback em memória para o ambiente serverless
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Rota principal (suporta index.html ou home.html)
@app.route('/')
def home():
    total_apostas = 0.0
    try:
        return render_template('index.html', total=total_apostas)
    except:
        return render_template('home.html', total=total_apostas)

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Rota para silenciar o aviso 404 do ícone do navegador
@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    return '', 204

# Objeto WSGI exportado para o ambiente serverless da Vercel
app = app
