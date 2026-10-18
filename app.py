import streamlit as st
from supabase import create_client, Client
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
        "twitter_url": twitter_url
    }
    supabase.table('crypto_games').insert(proj).execute()
    st.toast(f'✅ {nome} adicionado ao radar!', icon='🎯')

# --- Motor Alpha de Social Listening ---
def buscar_projetos_reais():
    with st.spinner('A caçar links underground e anúncios...'):
        try:
            existentes_db = supabase.table('crypto_games').select("site_url").execute()
            sites_existentes = [x['site_url'] for x in existentes_db.data if x.get('site_url')]
            
            url = "https://www.reddit.com/search.json"
            params = {
                "q": '("web3 game" OR "crypto game" OR "solana game") AND (launch OR tge OR airdrop OR whitelist OR token)',
                "sort": "new",
                "limit": 50
            }
            
            # Passaporte oficial que contorna o erro 403 do Reddit
            headers = {
                'User-Agent': 'python:altitude-sniper-bot:v1.0 (by /u/eder_altitude)',
                'Accept': 'application/json'
            }
            
            resposta = requests.get(url, params=params, headers=headers)
            
            if resposta.status_code == 403:
                st.error("⚠️ Erro 403 persistente: O Reddit continua a bloquear o servidor da nuvem. O passo seguinte será utilizar uma API especializada em cripto em vez de fóruns públicos.")
                return
            elif resposta.status_code == 429:
                st.error("⚠️ Erro 429: Muitas requisições num curto espaço de tempo. Aguarde uns minutos.")
                return
            elif resposta.status_code != 200:
                st.error(f"⚠️ A fonte recusou a ligação (Erro {resposta.status_code}).")
                return

            try:
                dados = resposta.json()
            except ValueError:
                st.error("⚠️ Falha ao descodificar os dados.")
                return
            
            novos_projetos_inseridos = 0
            
            for post in dados.get('data', {}).get('children', []):
                post_data = post['data']
                titulo = post_data.get('title', '')
                texto = post_data.get('selftext', '')
                conteudo_total = (titulo + " " + texto).lower()
                
                urls_encontradas = re.findall(r'https?://[^\s)\]"]+', texto)
                site_url = "#"
                twitter_url = "#"
                
                for link in urls_encontradas:
                    if "twitter.com" in link or "x.com" in link:
                        twitter_url = link
                    elif any(ext in link for ext in [".fun", ".gg", ".io", ".net", ".com", "linktr.ee"]) and "reddit" not in link:
                        site_url = link
                
                if site_url == "#" or site_url in sites_existentes:
                    continue
                    
                nome_projeto = " ".join(titulo.split()[0:4]).replace("[", "").replace("]", "")
                
                rede = "Ethereum / Outra"
                if "solana" in conteudo_total or "sol" in conteudo_total: rede = "Solana"
                elif "ronin" in conteudo_total: rede = "Ronin"
                elif "immutable" in conteudo_total or "imx" in conteudo_total: rede = "Immutable X"
                elif "polygon" in conteudo_total: rede = "Polygon"
                
                score = 60
                if "whitelist" in conteudo_total: score += 15
                if "q4" in conteudo_total or "q1" in conteudo_total: score += 10
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
                
            if novos_projetos_inseridos > 0:
                st.toast(f'Varredura concluída! {novos_projetos_inseridos} projetos novos encontrados.', icon='📡')
            else:
                st.toast('Nenhum link novo encontrado nesta varredura.', icon='⚠️')
                
        except Exception as e:
            st.error(f"Erro inesperado no sistema de busca: {e}")

# --- Interface do Usuário ---
st.title("🎯 Crypto Sniper Dashboard")

# Barra Lateral (Menu)
with st.sidebar:
    st.header("⚙️ Controles e Caça")
    
    if st.button("📡 Buscar Projetos Underground"):
        buscar_projetos_reais()
        
    st.divider()
    
    with st.expander("➕ Adicionar Projeto Manualmente"):
        with st.form("form_manual"):
            m_nome = st.text_input("Nome do Jogo")
            m_rede = st.selectbox("Rede", ["Solana", "Ronin", "Immutable X", "Polygon", "Avalanche", "Outra"])
            m_site = st.text_input("Link do Site")
            m_twitter = st.text_input("Link do Twitter")
            submit_manual = st.form_submit_button("Salvar no Radar")
            if submit_manual and m_nome:
                inserir_projeto_manual(m_nome, m_rede, m_site, m_twitter)

    st.divider()
    st.subheader("Filtros")
    filtro_rede = st.selectbox("Filtrar por Rede", ["Todas", "Solana", "Ronin", "Immutable X", "Polygon", "Avalanche", "Outra"])

    st.divider()
    if st.button("🚨 Limpar Todo o Dashboard", type="primary"):
        limpar_dashboard_inteiro()

# Renderização dos Dados
jogos = buscar_jogos()

if not jogos:
    st.info("O radar está limpo. Busque novos projetos ou insira links manualmente.")
else:
    col1, col2, col3 = st.columns(3)
    
    for idx, jogo in enumerate(jogos):
        if filtro_rede != "Todas" and jogo['rede'] != filtro_rede:
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
            with col1: 
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button("🗑️ Apagar", key=f"del_{jogo['id']}"):
                    apagar_jogo(jogo['id'])
                    st.rerun()
        elif idx % 3 == 1:
            with col2: 
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button("🗑️ Apagar", key=f"del_{jogo['id']}"):
                    apagar_jogo(jogo['id'])
                    st.rerun()
        else:
            with col3: 
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button("🗑️ Apagar", key=f"del_{jogo['id']}"):
                    apagar_jogo(jogo['id'])
                    st.rerun()
