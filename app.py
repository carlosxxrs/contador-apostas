from flask import Flask, render_template, request, redirect, url_for, session, flash
from pathlib import Path
import os
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, select, insert, delete
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configura uma chave secreta segura usando variáveis de ambiente em produção
app.secret_key = os.getenv('SECRET_KEY', 'chave_padrao_para_desenvolvimento_local_123')

DB_FILE = Path(__file__).resolve().parent / 'apostas.db'
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DB_FILE}')

engine = create_engine(DATABASE_URL, future=True)
metadata = MetaData()

users = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True),
    Column('username', String(100), unique=True, nullable=False),
    Column('password', String(255), nullable=False) # Aumentado para suportar o hash seguro
)

bets = Table(
    'bets', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, nullable=False),
    Column('house', String(200), nullable=False),
    Column('amount', Float, nullable=False),
    Column('date', String(50), nullable=False)
)


def hash_password(password):
    # Gera um hash seguro com Salt automático usando a biblioteca padrão do Flask
    return generate_password_hash(password)


def init_db():
    metadata.create_all(engine)
    with engine.begin() as conn:
        user = conn.execute(select(users.c.id).where(users.c.username == 'carlo')).first()
        if user is None:
            result = conn.execute(insert(users).values(username='carlo', password=hash_password('1234')))
            user_id = result.inserted_primary_key[0]
            conn.execute(
                insert(bets),
                [
                    {'user_id': user_id, 'house': 'bet 365', 'amount': 1000.0, 'date': '28/06/2026 00:00'},
                    {'user_id': user_id, 'house': 'betano', 'amount': 500.0, 'date': '28/06/2026 00:05'}
                ]
            )

# Inicializa o banco de dados
init_db()


def get_user(username):
    with engine.connect() as conn:
        row = conn.execute(select(users).where(users.c.username == username)).first()
    return row


def authenticate_user(username, password):
    user = get_user(username)
    # Verifica a senha digitada contra o hash seguro do banco
    return bool(user and check_password_hash(user.password, password))


def create_user(username, password):
    try:
        with engine.begin() as conn:
            conn.execute(insert(users).values(username=username, password=hash_password(password)))
        return True
    except IntegrityError:
        return False


def add_bet(username, house, amount):
    try:
        amount_value = float(amount)
    except ValueError:
        amount_value = 0.0

    user = get_user(username)
    if user is None:
        return False

    with engine.begin() as conn:
        conn.execute(
            insert(bets).values(
                user_id=user.id,
                house=house,
                amount=round(amount_value, 2),
                date=datetime.now().strftime('%d/%m/%Y %H:%M')
            )
        )
    return True


def get_user_bets(username):
    user = get_user(username)
    if user is None:
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            select(bets.c.id, bets.c.house, bets.c.amount, bets.c.date)
            .where(bets.c.user_id == user.id)
            .order_by(bets.c.id.desc())
        ).fetchall()
    return rows


def delete_bet(username, bet_id):
    user = get_user(username)
    if user is None:
        return False
    with engine.begin() as conn:
        # Aqui usamos o 'delete' do SQLAlchemy sem conflito de nome
        result = conn.execute(delete(bets).where(bets.c.id == bet_id, bets.c.user_id == user.id))
    return result.rowcount > 0


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash('Preencha todos os campos.', 'danger')
            return redirect(url_for('register'))
        if create_user(username, password):
            flash('Usuário criado com sucesso. Faça login.', 'success')
            return redirect(url_for('login'))
        flash('Usuário já existe.', 'danger')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if authenticate_user(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_bets = get_user_bets(username)

    if request.method == 'POST' and 'house' in request.form:
        house = request.form['house']
        amount = request.form['amount']
        add_bet(username, house, amount)
        return redirect(url_for('dashboard'))

    # Cálculo do resumo corrigido e garantido contra falhas de tipo
    summary = {}
    for bet in user_bets:
        house_name = bet.house
        amount_value = float(bet.amount) if bet.amount else 0.0
        
        summary.setdefault(house_name, {'count': 0, 'total': 0.0})
        summary[house_name]['count'] += 1
        summary[house_name]['total'] += amount_value

    return render_template('dashboard.html', username=username, bets=user_bets, summary=summary)


# Nome da função alterado para evitar conflito com o 'delete' do SQLAlchemy
@app.route('/delete/<int:bet_id>', methods=['POST'])
def delete_bet_route(bet_id):
    if 'username' in session:
        username = session['username']
        delete_bet(username, bet_id)
    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)