from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from datetime import timedelta
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, select, insert, delete

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

if os.path.exists(TEMPLATE_DIR):
    app = Flask(__name__, template_folder=TEMPLATE_DIR)
else:
    app = Flask(__name__, template_folder=BASE_DIR)

# CONFIGURAÇÃO DE SESSÃO PERMANENTE (Mantém logado mesmo se reiniciar)
app.secret_key = os.getenv('SECRET_KEY', 'chave_secreta_super_segura_9988')
app.permanent_session_lifetime = timedelta(days=30)  # Lembra o login por 30 dias

# Conexão com o banco PostgreSQL do Railway
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///apostas.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, future=True)
metadata = MetaData()

# Tabelas Simplificadas
users = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True),
    Column('username', String(100), unique=True, nullable=False),
    Column('password', String(100), nullable=False)
)

bets = Table(
    'bets', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, nullable=False),
    Column('house', String(200), nullable=False),
    Column('amount', Float, nullable=False)
)

def init_db():
    try:
        metadata.create_all(engine)
    except Exception as e:
        print(f"Erro ao iniciar banco: {e}")

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password'].strip()
        
        if not username or not password:
            flash('Preencha os campos!', 'danger')
            return redirect(url_for('register'))
            
        with engine.connect() as conn:
            user_exists = conn.execute(select(users).where(users.c.username == username)).first()
            
        if user_exists:
            flash('Esse usuário já existe!', 'danger')
            return redirect(url_for('register'))
            
        with engine.begin() as conn:
            conn.execute(insert(users).values(username=username, password=password))
            
        flash('Conta criada! Faça o login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password'].strip()
        
        with engine.connect() as conn:
            user = conn.execute(select(users).where(users.c.username == username, users.c.password == password)).first()
            
        if user:
            session.permanent = True  # Ativa a durabilidade do cookie de login
            session['username'] = user.username
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha incorretos!', 'danger')
            
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    
    # Adicionar nova aposta
    if request.method == 'POST':
        house = request.form['house'].strip().upper() # Padroniza em MAIÚSCULO para somar certo
        try:
            amount = float(request.form['amount'])
        except ValueError:
            amount = 0.0
            
        if house and amount > 0:
            with engine.begin() as conn:
                conn.execute(insert(bets).values(user_id=user_id, house=house, amount=amount))
        return redirect(url_for('dashboard'))

    # Buscar apostas do usuário
    with engine.connect() as conn:
        all_bets = conn.execute(select(bets).where(bets.c.user_id == user_id).order_by(bets.c.id.desc())).fetchall()

    # Criar a lógica da SOMA POR CASA
    summary = {}
    total_geral = 0.0
    
    for b in all_bets:
        casa = b.house
        valor = float(b.amount)
        total_geral += valor
        
        if casa in summary:
            summary[casa] += valor
        else:
            summary[casa] = valor

    return render_template('dashboard.html', username=session['username'], bets=all_bets, summary=summary, total_geral=total_geral)

@app.route('/delete/<int:bet_id>', methods=['POST'])
def delete_bet(bet_id):
    if 'user_id' in session:
        with engine.begin() as conn:
            conn.execute(delete(bets).where(bets.c.id == bet_id, bets.c.user_id == session['user_id']))
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

init_db()

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
