from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from tinydb import TinyDB, Query
import os

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração do TinyDB
db = TinyDB('database.json')
usuarios_db = db.table('usuarios')
livros_db = db.table('livros')
emprestimos_db = db.table('emprestimos')

# Configuração de upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Criar diretório de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper functions for date handling
def db_date_format(dt):
    """Convert datetime to database storage format (YYYY-MM-DD)"""
    return dt.strftime('%Y-%m-%d')

def display_date_format(dt):
    """Convert datetime to display format (DD/MM/YYYY)"""
    return dt.strftime('%d/%m/%Y')

def parse_date(date_str):
    """Parse date from either storage or display format"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')  # Try storage format first
    except ValueError:
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')  # Try display format
        except ValueError:
            return datetime.now()  # Fallback to current date

# Criar usuário admin padrão
if not usuarios_db.search(Query().username == 'admin'):
    usuarios_db.insert({
        'username': 'admin',
        'password': generate_password_hash('admin123'),
        'is_admin': True,
        'nome_completo': 'Administrador',
        'matricula': '00000'
    })

# Rotas Públicas
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = usuarios_db.get(Query().username == username)
        
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            session['nome'] = user.get('nome_completo', 'Usuário')
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin' if user['is_admin'] else 'user'))
        else:
            flash('Usuário ou senha incorretos', 'error')
    
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nome_completo = request.form['nome_completo']
        matricula = request.form['matricula']
        
        if usuarios_db.search(Query().username == username):
            flash('Nome de usuário já existe', 'error')
            return redirect(url_for('cadastro'))
        
        if usuarios_db.search(Query().matricula == matricula):
            flash('Matrícula já cadastrada', 'error')
            return redirect(url_for('cadastro'))
        
        usuarios_db.insert({
            'username': username,
            'password': generate_password_hash(password),
            'nome_completo': nome_completo,
            'matricula': matricula,
            'is_admin': False
        })
        
        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('index'))

# Rotas do Admin
@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        flash('Acesso restrito aos administradores', 'error')
        return redirect(url_for('login'))
    
    return render_template('admin.html')

@app.route('/adicionar-livro', methods=['POST'])
def adicionar_livro():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    titulo = request.form['titulo']
    autor = request.form['autor']
    isbn = request.form['isbn']
    
    # Processar upload da capa
    capa = None
    if 'capa' in request.files:
        file = request.files['capa']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{isbn}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            capa = filename
    
    livros_db.insert({
        'titulo': titulo,
        'autor': autor,
        'isbn': isbn,
        'disponivel': True,
        'capa': capa
    })
    
    flash('Livro adicionado com sucesso!', 'success')
    return redirect(url_for('admin'))

@app.route('/devolver/<int:livro_id>')
def devolver(livro_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    livros_db.update({'disponivel': True}, doc_ids=[livro_id])
    emprestimos_db.update(
        {'devolvido': True, 'data_devolucao': db_date_format(datetime.now())},
        (Query().livro_id == livro_id) & (Query().devolvido == False)
    )
    
    flash('Livro devolvido com sucesso!', 'success')
    return redirect(url_for('admin_emprestimos'))

@app.route('/admin/livros')
def admin_livros():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    query = request.args.get('q', '').lower()
    todos_livros = livros_db.all()
    
    if query:
        todos_livros = [livro for livro in todos_livros 
                       if query in livro['titulo'].lower() 
                       or query in livro['autor'].lower() 
                       or query in livro['isbn'].lower()]
    
    return render_template('admin_livros.html', livros=todos_livros)

@app.route('/admin/emprestimos')
def admin_emprestimos():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    query = request.args.get('q', '').lower()
    todos_emprestimos = emprestimos_db.search(Query().devolvido == False)
    
    for emp in todos_emprestimos:
        livro = livros_db.get(doc_id=emp['livro_id'])
        usuario = usuarios_db.get(Query().username == emp['usuario'])
        
        # Parse dates using robust function
        data_emprestimo = parse_date(emp['data_emprestimo'])
        data_devolucao = parse_date(emp['data_devolucao'])
        
        # Calculate days overdue
        hoje = datetime.now()
        dias_atraso = (hoje - data_devolucao).days if hoje > data_devolucao else 0
        
        emp['titulo'] = livro['titulo'] if livro else 'Livro removido'
        emp['nome_usuario'] = usuario['nome_completo'] if usuario else 'Usuário desconhecido'
        emp['data_emprestimo'] = display_date_format(data_emprestimo)
        emp['data_devolucao'] = display_date_format(data_devolucao)
        emp['livro_id'] = livro.doc_id if livro else 0
        emp['dias_atraso'] = dias_atraso
    
    if query:
        todos_emprestimos = [emp for emp in todos_emprestimos
                           if query in emp['titulo'].lower()
                           or query in emp['nome_usuario'].lower()]
    
    return render_template('admin_emprestimos.html', emprestimos=todos_emprestimos)

# Rotas do Usuário
@app.route('/user')
def user():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = usuarios_db.get(Query().username == session['username'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Mostrar apenas empréstimos ativos (não devolvidos)
    meus_emprestimos = emprestimos_db.search(
        (Query().usuario == session['username']) & 
        (Query().devolvido == False)
    )
    
    # Adicionar informações completas do livro a cada empréstimo
    emprestimos_completos = []
    for emp in meus_emprestimos:
        livro = livros_db.get(doc_id=emp['livro_id'])
        if livro:
            emprestimo_completo = {
                'titulo': livro['titulo'],
                'data_devolucao': display_date_format(parse_date(emp['data_devolucao'])),
                'livro_id': livro.doc_id,
                'capa': livro.get('capa', None)  # Adiciona a capa do livro
            }
            emprestimos_completos.append(emprestimo_completo)
    
    return render_template('user.html', 
                         nome=session.get('nome', 'Aluno'),
                         emprestimos=emprestimos_completos)

@app.route('/emprestar/<int:livro_id>')
def emprestar(livro_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    livro = livros_db.get(doc_id=livro_id)
    
    if livro and livro['disponivel']:
        livros_db.update({'disponivel': False}, doc_ids=[livro_id])
        data_devolucao = datetime.now() + timedelta(days=7)
        
        emprestimos_db.insert({
            'livro_id': livro_id,
            'usuario': session['username'],
            'data_emprestimo': db_date_format(datetime.now()),
            'data_devolucao': db_date_format(data_devolucao),
            'devolvido': False
        })
        
        flash(
            f'Livro "{livro["titulo"]}" emprestado com sucesso! Devolver até: {display_date_format(data_devolucao)}', 
            'success'
        )
    else:
        flash('Livro não disponível para empréstimo', 'error')
    
    return redirect(url_for('livros'))

@app.route('/livros')
def livros():
    query = request.args.get('q', '').lower()
    todos_livros = livros_db.all()
    
    if query:
        todos_livros = [livro for livro in todos_livros 
                       if query in livro['titulo'].lower()
                       or query in livro['autor'].lower()
                       or query in livro['isbn'].lower()]
    
    # Verificar disponibilidade e adicionar ação de empréstimo
    for livro in todos_livros:
        livro['pode_emprestar'] = livro['disponivel'] and 'username' in session
        livro['capa'] = livro.get('capa', None)
    
    return render_template('livros.html', livros=todos_livros)

@app.route('/deletar-livro/<int:livro_id>', methods=['POST'])
def deletar_livro(livro_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    # Verificar se o livro está emprestado antes de deletar
    emprestimo_ativo = emprestimos_db.search(
        (Query().livro_id == livro_id) & 
        (Query().devolvido == False)
    )
    
    if emprestimo_ativo:
        flash('Não é possível excluir um livro que está emprestado', 'error')
    else:
        # Remover a capa do livro se existir
        livro = livros_db.get(doc_id=livro_id)
        if livro and livro.get('capa'):
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], livro['capa']))
            except FileNotFoundError:
                pass
        
        # Remover o livro do banco de dados
        livros_db.remove(doc_ids=[livro_id])
        flash('Livro excluído com sucesso!', 'success')
    
    return redirect(url_for('admin_livros'))

if __name__ == '__main__':
    app.run(debug=True)