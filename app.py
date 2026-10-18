import streamlit as st
from supabase import create_client, Client
import requests
import re
from datetime import datetime, timedelta, timezone

# --- Configuração da Página ---
st.set_page_config(page_title="Sniper Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- Conexão Segura com Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- Estilização CSS dos Cards ---
css = """
<style>
.sniper-card {
    background-color: #1E1E24;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 5px;
    border: 1px solid #333;
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
.info-row { font-size: 13px; color: #CCC; margin-bottom: 5px; }
.links-row a {
    text-decoration: none;
    color: #00BFFF;
    margin-right: 15px;
    font-size: 14px;
    font-weight: bold;
}
.links-row a:hover { color: #FFF; }
.yt-link { color: #FF0000 !important; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- Funções de Banco de Dados ---
def buscar_jogos():
    response = supabase.table('crypto_games').select("*").order('alpha_score', desc=True).execute()
    return response.data

def apagar_jogo(jogo_id):
    try:
        supabase.table('crypto_games').delete().eq('id', jogo_id).execute()
    except Exception as e:
        st.error(f"Erro de permissão ao apagar: {e}")

def limpar_dashboard_inteiro():
    try:
        jogos = buscar_jogos()
        for j in jogos:
            supabase.table('crypto_games').delete().eq('id', j['id']).execute()
        st.toast('🚨 Dashboard completamente limpo!', icon='🗑️')
    except Exception as e:
        st.error(f"Erro ao limpar: {e}")

def inserir_projeto_manual(nome, rede, site_url, twitter_url):
    score = 50
    if site_url and len(site_url) > 5: score += 20
    if twitter_url and len(twitter_url) > 5: score += 15
    if rede in ["Solana", "Ronin"]: score += 10
    
    proj = {
        "nome": nome,
        "ticker": "TBA",
        "rede": rede,
        "alpha_score": min(score, 100),
        "estagio": "Underground / Radar",
        "investidores": "Mapeamento Manual",
        "site_url": site_url,
        "twitter_url": twitter_url,
        "data_publicacao": datetime.now().strftime("%d/%m/%Y"),
        "visualizacoes": "N/A",
        "video_url": "#"
    }
    supabase.table('crypto_games').insert(proj).execute()
    st.toast(f'✅ {nome} adicionado ao radar!', icon='🎯')

# --- Função Auxiliar: Limpeza de Nome ---
def extrair_nome_provavel(titulo, site_url):
    """Tenta adivinhar o nome do projeto pelo domínio do site ou limpa o título."""
    if site_url != "#":
        # Remove parâmetros como ?ref= para extrair o domínio limpo
        url_limpa = site_url.split('?')[0]
        dominio = re.sub(r'https?://(www\.)?', '', url_limpa).split('/')[0]
        nome_dominio = dominio.split('.')[0]
        
        blacklist = ['discord', 'twitter', 'facebook', 'youtube', 'gate', 'linktr', 'medium', 'coinmarketcap', 'coingecko', 'binance', 'bybit', 't', 'telegram']
        
        if len(nome_dominio) > 2 and nome_dominio.lower() not in blacklist:
            return nome_dominio.capitalize()
            
    # Fallback: limpar o título do vídeo
    titulo_limpo = re.sub(r'[^a-zA-Z0-9\s]', '', titulo)
    palavras = titulo_limpo.split()
    stop_words = ['new', 'crypto', 'game', 'play', 'to', 'earn', 'free', 'solana', 'airdrop', 'the', 'best', 'review', 'tutorial', 'top', 'upcoming', 'update', 'everyday', 'setiap', 'hari']
    palavras_chave = [p for p in palavras if p.lower() not in stop_words]
    
    if palavras_chave:
         return " ".join(palavras_chave[0:3]).capitalize()
    return " ".join(palavras[0:3]).capitalize() if palavras else "Unknown"

# --- Motor Alpha de Varredura YouTube ---
def buscar_projetos_reais():
    if "YOUTUBE_API_KEY" not in st.secrets:
        st.error("⚠️ Chave do YouTube não encontrada nos Secrets do Streamlit.")
        return

    with st.spinner('A analisar vídeos do YouTube das últimas 48 horas...'):
        try:
            youtube_key = st.secrets["YOUTUBE_API_KEY"]
            existentes_db = supabase.table('crypto_games').select("site_url", "video_url").execute()
            sites_existentes = [x['site_url'] for x in existentes_db.data if x.get('site_url') and x.get('site_url') != "#"]
            videos_existentes = [x['video_url'] for x in existentes_db.data if x.get('video_url') and x.get('video_url') != "#"]
            
            data_limite = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat("T", "seconds").replace("+00:00", "Z")
            
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                "part": "snippet",
                "q": '("new crypto game" OR "solana game" OR "play to earn") (launch OR gameplay OR airdrop)',
                "type": "video",
                "order": "date",
                "publishedAfter": data_limite,
                "maxResults": 20,
                "key": youtube_key
            }
            search_resp = requests.get(search_url, params=search_params)
            
            if search_resp.status_code != 200:
                st.error(f"Erro na API do YouTube: {search_resp.json().get('error', {}).get('message', 'Acesso Negado')}")
                return
