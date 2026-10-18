import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- Configuração da Página ---
st.set_page_config(page_title="Sniper Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- Conexão Segura com Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- Estilização CSS dos Cards (Dark Mode & Glow) ---
css = """
<style>
.sniper-card {
    background-color: #1E1E24;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 15px;
    border: 1px solid #333;
    transition: transform 0.2s;
}
.sniper-card:hover {
    transform: translateY(-3px);
    border-color: #555;
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}
.game-title {
    font-size: 20px;
    font-weight: bold;
    color: #FFF;
    margin: 0;
}
.score-badge {
    background-color: #00FF66;
    color: #000;
    font-weight: 900;
    font-size: 18px;
    padding: 5px 10px;
    border-radius: 5px;
    box-shadow: 0 0 10px rgba(0, 255, 102, 0.5);
}
.score-badge.medium { background-color: #FFD700; box-shadow: 0 0 10px rgba(255, 215, 0, 0.5); }
.score-badge.low { background-color: #FF3333; color: white; box-shadow: 0 0 10px rgba(255, 51, 51, 0.5); }
.tags-row { margin-bottom: 15px; font-size: 14px; color: #AAA;}
.tag { background: #333; padding: 3px 8px; border-radius: 4px; margin-right: 5px; color: #FFF; font-size: 12px;}
.links-row a {
    text-decoration: none;
    color: #00BFFF;
    margin-right: 15px;
    font-size: 14px;
    font-weight: bold;
}
.links-row a:hover { color: #FFF; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- Funções do Banco de Dados ---
def buscar_jogos():
    response = supabase.table('crypto_games').select("*").order('alpha_score', desc=True).execute()
    return response.data

def inserir_teste():
    dado_teste = {
        "nome": "ChronoForge",
        "ticker": "$RIFT",
        "rede": "Immutable X",
        "alpha_score": 92,
        "estagio": "Pre-TGE",
        "investidores": "Animoca Brands, Spartan Group",
        "twitter_url": "https://twitter.com",
        "site_url": "https://chronoforge.gg"
    }
    supabase.table('crypto_games').insert(dado_teste).execute()
    st.toast('✅ Jogo de teste inserido com sucesso!')

# --- Interface do Usuário ---
st.title("🎯 Crypto Sniper Dashboard")

# Barra Lateral (Menu)
with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔌 Injetar Dado de Teste"):
        inserir_teste()
        st.rerun() # Atualiza a página
    
    st.divider()
    filtro_rede = st.selectbox("Filtrar por Rede", ["Todas", "Solana", "Ronin", "Immutable X", "Arbitrum"])
    nota_minima = st.slider("Alpha Score Mínimo", 0, 100, 70)

# Buscando dados
jogos = buscar_jogos()

if not jogos:
    st.info("O radar está vazio. Aguardando novos projetos ou clique em 'Injetar Dado de Teste' no menu lateral.")
else:
    # Renderizando os cards em grid (3 colunas)
    col1, col2, col3 = st.columns(3)
    
    for idx, jogo in enumerate(jogos):
        # Aplicando filtros
        if filtro_rede != "Todas" and jogo['rede'] != filtro_rede:
            continue
        if jogo['alpha_score'] < nota_minima:
            continue
            
        # Definindo a cor do Alpha Score
        score = jogo['alpha_score']
        badge_class = "score-badge"
        if score < 60: badge_class += " low"
        elif score < 85: badge_class += " medium"
        
        # HTML do Sniper Card
        card_html = f"""
        <div class="sniper-card">
            <div class="card-header">
                <p class="game-title">{jogo['nome']} <span style="font-size:14px; color:#888;">{jogo['ticker'] or ''}</span></p>
                <div class="{badge_class}">{score}</div>
            </div>
            <div class="tags-row">
                <span class="tag">⛓️ {jogo['rede']}</span>
                <span class="tag">🕒 {jogo.get('estagio', 'N/A')}</span>
            </div>
            <div style="font-size: 13px; color: #CCC; margin-bottom: 15px;">
                <strong>VCs:</strong> {jogo.get('investidores', 'N/A')}
            </div>
            <div class="links-row">
                <a href="{jogo.get('twitter_url', '#')}" target="_blank">🐦 Twitter</a>
                <a href="{jogo.get('site_url', '#')}" target="_blank">🌐 Site</a>
            </div>
        </div>
        """
        
        # Distribuindo nas colunas
        if idx % 3 == 0:
            with col1: st.markdown(card_html, unsafe_allow_html=True)
        elif idx % 3 == 1:
            with col2: st.markdown(card_html, unsafe_allow_html=True)
        else:
            with col3: st.markdown(card_html, unsafe_allow_html=True)
