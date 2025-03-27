from flask import Flask, render_template, request, redirect, url_for, flash
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64
import yfinance as yf
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-aqui'  # Troque por algo único e seguro

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Usuários pré-definidos (nome de usuário: senha)
USERS = {
    'flavio': 'senha123',  # Substitua pelos seus usuários e senhas
    'amigo1': 'senha456',
    'amigo2': 'senha789'
}

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    if username in USERS:
        return User(username)
    return None

def adjust_ticker(ticker):
    ticker = ticker.strip().upper()
    if ticker.endswith(('3', '4', '5', '6', '11')) or '.SA' in ticker:
        return ticker.replace('.SA', '') + '.SA'
    return ticker

def generate_price_chart(ticker):
    df = yf.download(ticker, period='1y', interval='1h')
    if df.empty:
        return None
    
    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df['Close'], label='Preço de Fechamento', color='blue')
    last_date = df.index[-1]
    last_close = float(df['Close'].iloc[-1])
    plt.scatter(last_date, last_close, color='red', s=100, label=f'Último Fechamento: {last_close:.2f}', zorder=5)
    plt.title(f'{ticker} - Análise de Preço (Último 1 Ano)')
    plt.xlabel('Data')
    plt.ylabel('Preço')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close()
    return chart_data

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    print(f"Acessando a rota '/' com método {request.method}")
    if request.method == 'POST':
        ticker = request.form['ticker'].strip().upper()
        ticker = adjust_ticker(ticker)
        return redirect(url_for('analyze', ticker=ticker))
    return render_template('index.html')

@app.route('/analyze', methods=['GET', 'POST'])
@login_required
def analyze():
    print(f"Acessando a rota '/analyze' com método {request.method}")
    if request.method == 'GET':
        ticker = request.args.get('ticker', '').strip().upper()
    else:
        ticker = request.form['ticker'].strip().upper()
    ticker = adjust_ticker(ticker)
    print(f"Ticker recebido: {ticker}")
    
    if not ticker:
        return render_template('result.html', error="Nenhum ticker fornecido.")
    
    try:
        # Para testes locais no Windows
        backend_url = 'http://127.0.0.1:5001/analyze'
        response = requests.post(backend_url, data={'ticker': ticker})
        response.raise_for_status()
        results = response.json()
        
        if 'error' in results:
            return render_template('result.html', error=results['error'])
        
        chart_data = generate_price_chart(ticker)
        results['chart_data'] = chart_data
        
        print("Renderizando resultado...")
        return render_template('result.html', **results)
    
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar ao backend: {str(e)}")
        return render_template('result.html', error=f"Erro ao conectar ao backend: {str(e)}")

@app.route('/detailed', methods=['POST'])
@login_required
def detailed():
    ticker = request.form['ticker'].strip().upper()
    ticker = adjust_ticker(ticker)
    period = request.form['period'].strip().lower()
    print(f"Detalhes solicitados - Ticker: {ticker}, Período: {period}")
    
    try:
        backend_url = 'http://127.0.0.1:5001/detailed'
        response = requests.post(backend_url, data={'ticker': ticker, 'period': period})
        response.raise_for_status()
        details = response.json()
        
        if 'error' in details:
            return render_template('detailed.html', period=period, ticker=ticker, error=details['error'])
        
        return render_template('detailed.html', period=period, ticker=ticker, details=details)
    
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar ao backend para detalhes: {str(e)}")
        return render_template('detailed.html', period=period, ticker=ticker, error=f"Erro ao conectar ao backend: {str(e)}")

if __name__ == "__main__":
   app.run(host='0.0.0.0', debug=True, port=5000)