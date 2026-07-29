import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma_chave_super_secreta_e_segura_123'

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

if not os.getenv("DATABASE_URL"):
    @event.listens_for(db.engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

# --- MODELOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    apostas = db.relationship('Aposta', backref='author', lazy=True)
    lucros = db.relationship('LucroOperacao', backref='author', lazy=True)

class Aposta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    casa = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Novo modelo exclusivo para o bloco de lucro operado
class LucroOperacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_conta = db.Column(db.String(100), nullable=False)
    valor_lucro = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- ROTAS ---
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    
    # Busca dados principais
    user_apostas = Aposta.query.filter_by(user_id=user_id).order_by(Aposta.id.asc()).all()
    total_investido = sum(aposta.valor for aposta in user_apostas)
    
    # Busca registros do bloco de Lucro da Conta
    user_lucros = LucroOperacao.query.filter_by(user_id=user_id).order_by(LucroOperacao.id.asc()).all()
    nome_conta_atual = user_lucros[0].nome_conta if user_lucros else ""
    total_lucro_operacao = sum(item.valor_lucro for item in user_lucros)
    
    return render_template(
        'index.html', 
        apostas=user_apostas, 
        total=total_investido,
        lucros=user_lucros,
        nome_conta_atual=nome_conta_atual,
        total_lucro_operacao=total_lucro_operacao
    )

@app.route('/adicionar_aposta', methods=['POST'])
def adicionar_aposta():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    casa = request.form.get('casa')
    valor_texto = request.form.get('valor')
    if casa and valor_texto:
        try:
            valor = float(valor_texto)
            nova_aposta = Aposta(casa=casa, valor=valor, user_id=session['user_id'])
            db.session.add(nova_aposta)
            db.session.commit()
        except ValueError:
            flash('Valor inválido.', 'danger')
    return redirect(url_for('index'))

@app.route('/deletar_aposta/<int:id>', methods=['POST'])
def deletar_aposta(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    aposta = Aposta.query.get_or_404(id)
    if aposta.user_id == session['user_id']:
        db.session.delete(aposta)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/editar_aposta/<int:id>', methods=['POST'])
def editar_aposta(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    aposta = Aposta.query.get_or_404(id)
    if aposta.user_id == session['user_id']:
        novo_valor = request.form.get('novo_valor')
        if novo_valor:
            try:
                aposta.valor = float(novo_valor)
                db.session.commit()
            except ValueError:
                flash('Valor inválido.', 'danger')
    return redirect(url_for('index'))

# --- ROTAS DO BLOCO DE LUCRO INDEPENDENTE ---
@app.route('/adicionar_lucro', methods=['POST'])
def adicionar_lucro():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    nome_conta = request.form.get('nome_conta')
    valor_texto = request.form.get('valor_lucro')
    
    if nome_conta and valor_texto:
        try:
            valor = float(valor_texto)
            novo_lucro = LucroOperacao(nome_conta=nome_conta, valor_lucro=valor, user_id=session['user_id'])
            db.session.add(novo_lucro)
            db.session.commit()
        except ValueError:
            flash('Valor de lucro inválido.', 'danger')
            
    return redirect(url_for('index'))

@app.route('/limpar_lucros', methods=['POST'])
def limpar_lucros():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Apaga apenas os registros de lucros operados pelo usuário
    LucroOperacao.query.filter_by(user_id=session['user_id']).delete()
    db.session.commit()
    return redirect(url_for('index'))

# --- AUTENTICAÇÃO ---
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
            return redirect(url_for('login'))
    return render_template('login.html')

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
        flash('Conta criada com sucesso! Faça seu login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
