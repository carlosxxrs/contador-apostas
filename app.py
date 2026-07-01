import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma_chave_secreta_e_segura_aqui'

# --- CONEXÃO LIMPA PARA O RAILWAY ---
uri = os.getenv("DATABASE_URL")
if uri:
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
else:
    uri = 'sqlite:///local_database.db'

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS ---
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

@app.before_request
def setup_db():
    db.create_all()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user_apostas = Aposta.query.filter_by(user_id=user_id).all()
    total_soma = sum(aposta.valor for aposta in user_apostas)
    return render_template('index.html', apostas=user_apostas, total=total_soma)

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
        flash('Conta criada com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=30)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/adicionar', methods=['POST'])
def adicionar_aposta():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    casa = request.form.get('casa')
    valor = float(request.form.get('valor', 0))
    nova_aposta = Aposta(casa=casa, valor=valor, user_id=session['user_id'])
    db.session.add(nova_aposta)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/deletar/<int:id>')
def deletar_aposta(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    aposta = Aposta.query.get_or_404(id)
    if aposta.user_id == session['user_id']:
        db.session.delete(aposta)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
