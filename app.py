import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time
import requests
import re

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

# --- Funções de Banco de Dados ---
def buscar_jogos():
    response = supabase.table('crypto_games').select("*").order('alpha_score', desc=True).execute()
    return response.data

def inserir_projeto_manual(nome, rede, site_url, twitter_url):
    # Calcula um score base focado em pre-TGE
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
        "twitter_url": twitter_url
    }
    supabase.table('crypto_games').insert(proj).execute()
    st.toast(f'✅ {nome} adicionado ao radar!')

# --- Motor Alpha de Social Listening (Foco em Underground/Pre-TGE) ---
def buscar_projetos_reais():
    with st.spinner('A caçar links underground e anúncios de lançamento...'):
        try:
            url = "https://www.reddit.com/search.json"
            # Filtro focado em achar a "data X" e sites web3
            params = {
                "q": '("web3 game" OR "crypto game" OR "solana game") AND ("launch date" OR "tge" OR "whitelist" OR "airdrop")',
                "sort": "new",
                "limit": 30
            }
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CryptoSniperBot/2.0'}
            
            resposta = requests.get(url, params=params, headers=headers)
            dados = resposta.json()
            
            novos_projetos_inseridos = 0
            
            for post in dados.get('data', {}).get('children', []):
                post_data = post['data']
                titulo = post_data.get('title', '')
                texto = post_data.get('selftext', '')
                conteudo_total = (titulo + " " + texto).lower()
                
                # Procura por links de sites de jogos (foco em .fun, .gg, .io, linktr.ee)
                urls_encontradas = re.findall(r'https?://[^\s)\]"]+', texto)
                
                site_url = "#"
                twitter_url = "#"
                
                for link in urls_encontradas:
                    if "twitter.com" in link or "x.com" in link:
                        twitter_url = link
                    elif any(ext in link for ext in [".fun", ".gg", ".io", ".net", ".com", "linktr.ee"]) and "reddit" not in link:
                        site_url = link
                
                # Se não houver site, descarta. Queremos os links "solanademons.fun" da vida.
                if site_url == "#":
                    continue
                    
                nome_projeto = " ".join(titulo.split()[0:4]).replace("[", "").replace("]", "")
                
                rede = "Ethereum / Outra"
                if "solana" in conteudo_total or "sol" in conteudo_total: rede = "Solana"
                elif "ronin" in conteudo_total: rede = "Ronin"
                elif "immutable" in conteudo_total or "imx" in conteudo_total: rede = "Immutable X"
                elif "polygon" in conteudo_total: rede = "Polygon"
                
                # --- Motor Alpha Pre-TGE ---
                score = 60 # Nota alta inicial por ter site e estar em fase de anúncio
                if "whitelist" in conteudo_total: score += 15
                if "q4" in conteudo_total or "q1" in conteudo_total: score += 10 # Indício de roadmap/data marcada
                if twitter_url != "#": score += 10
                
                proj = {
                    "nome": nome_projeto[:25],
                    "ticker": "TBA",
                    "rede": rede,
                    "estagio": "Pre-Launch / Underground",
                    "investidores": "Prospecção Automática",
                    "twitter_url": twitter_url,
                    "site_url": site_url,
                    "alpha_score": min(score, 100)
                }
                
                supabase.table('crypto_games').insert(proj).execute()
                novos_projetos_inseridos += 1
                
                if novos_projetos_inseridos >= 5:
                    break
                    
            if novos_projetos_inseridos > 0:
                st.success(f'📡 Varredura concluída! Encontramos {novos_projetos_inseridos} projetos novos com sites mapeados.')
            else:
                st.warning('Nenhum link novo underground encontrado nesta varredura. Tente novamente mais tarde.')
                
        except Exception as e:
            st.error(f"Falha na varredura de escuta social: {e}")

# --- Interface do Usuário ---
st.title("🎯 Crypto Sniper Dashboard")

# Barra Lateral (Menu)
with st.sidebar:
    st.header("⚙️ Controles e Caça")
    
    if st.button("📡 Buscar Projetos Underground"):
        buscar_projetos_reais()
        st.rerun()
        
    st.divider()
    
    # Formulário para Inserção Manual Rápida (Ex: solanademons.fun)
    with st.expander("➕ Adicionar Projeto Manualmente"):
        with st.form("form_manual"):
            m_nome = st.text_input("Nome do Jogo (Ex: Solana Demons)")
            m_rede = st.selectbox("Rede", ["Solana", "Ronin", "Immutable X", "Polygon", "Avalanche", "Outra"])
            m_site = st.text_input("Link do Site (.fun, .gg, etc)")
            m_twitter = st.text_input("Link do Twitter")
            submit_manual = st.form_submit_button("Salvar no Radar")
            if submit_manual and m_nome:
                inserir_projeto_manual(m_nome, m_rede, m_site, m_twitter)
                st.rerun()

    st.divider()
    st.subheader("Filtros do Dashboard")
    filtro_rede = st.selectbox("Filtrar por Rede", ["Todas", "Solana", "Ronin", "Immutable X", "Polygon", "Avalanche", "Outra"])
    nota_minima = st.slider("Alpha Score Mínimo", 0, 100, 50)

# Renderização dos Dados
jogos = buscar_jogos()

if not jogos:
    st.info("O radar está vazio. Clique em 'Buscar Projetos Underground' ou adicione um manualmente.")
else:
    col1, col2, col3 = st.columns(3)
    
    for idx, jogo in enumerate(jogos):
        if filtro_rede != "Todas" and jogo['rede'] != filtro_rede:
            continue
        if jogo['alpha_score'] < nota_minima:
            continue
            
        score = jogo['alpha_score']
        badge_class = "score-badge"
        if score < 60: badge_class += " low"
        elif score < 85: badge_class += " medium"
        
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
                <a href="{jogo.get('site_url', '#')}" target="_blank">🌐 Site Oficial</a>
            </div>
        </div>
        """
        
        if idx % 3 == 0:
            with col1: st.markdown(card_html, unsafe_allow_html=True)
        elif idx % 3 == 1:
            with col2: st.markdown(card_html, unsafe_allow_html=True)
        else:
            with col3: st.markdown(card_html, unsafe_allow_html=True)
