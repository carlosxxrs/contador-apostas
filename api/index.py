import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

# Localiza a pasta templates na raiz (/home/.../contador-apostas/templates)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua_chave_secreta_aqui')

# Configuração do Banco de Dados PostgreSQL (Neon/Supabase/ElephantSQL)
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Rota Principal - Passa 'total' e tenta carregar index.html ou home.html
@app.route('/')
def home():
    total_apostas = 0.0
    
    # Se o usuário estiver logado e você tiver lógica de soma, calcule aqui
    # Exemplo: total_apostas = sum(...)

    try:
        return render_template('index.html', total=total_apostas)
    except:
        return render_template('home.html', total=total_apostas)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

# Objeto exportado para a Vercel
app = app
