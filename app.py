import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma_chave_secreta_e_segura_aqui'

# --- CONFIGURAÇÃO DA URI DO BANCO ---
uri = os.getenv("DATABASE_URL")
if uri:
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql+pg8000://", 1)
    elif uri.startswith("postgresql://"):
        uri = uri.replace("postgresql://", "postgresql+pg8000://", 1)
else:
    uri = 'sqlite:///local_database.db'

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS DO BANCO ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    apostas = db.relationship('Aposta', backref='author', lazy=True)

class Aposta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    casa = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- ROTAS CORRIGIDAS ---

# 1. Rota Inicial (Painel)
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user_apostas = Aposta.query.filter_by(user_id=user_id).all()
    total_soma = sum(aposta.valor for aposta in user_apostas)
    return render_template('index.html', apostas=user_apostas, total=total_soma)

# 2. Rota de Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

# 3. Rota de Cadastro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Este usuário já existe.', 'danger')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Inicialização segura das tabelas
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
