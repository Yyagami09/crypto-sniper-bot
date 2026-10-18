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
                
            dados_busca = search_resp.json()
            video_ids = [item['id']['videoId'] for item in dados_busca.get('items', [])]
            
            if not video_ids:
                st.toast('Nenhum vídeo relevante publicado nas últimas 48h.', icon='⚠️')
                return
                
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            videos_params = {
                "part": "snippet,statistics",
                "id": ",".join(video_ids),
                "key": youtube_key
            }
            videos_resp = requests.get(videos_url, params=videos_params).json()
            
            novos_projetos_inseridos = 0
            
            for item in videos_resp.get('items', []):
                video_id = item.get('id')
                video_link = f"https://www.youtube.com/watch?v={video_id}"
                
                if video_link in videos_existentes:
                    continue
                    
                snippet = item.get('snippet', {})
                estatisticas = item.get('statistics', {})
                
                titulo = snippet.get('title', '')
                descricao = snippet.get('description', '')
                data_pub_raw = snippet.get('publishedAt', '')
                visualizacoes = estatisticas.get('viewCount', '0')
                
                try:
                    data_pub = datetime.strptime(data_pub_raw, "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")
                except:
                    data_pub = "Recente"
                    
                conteudo_total = (titulo + " " + descricao).lower()
                
                urls_encontradas = re.findall(r'https?://[^\s)\]"]+', descricao)
                site_url = "#"
                twitter_url = "#"
                
                # Sistema aprimorado de hierarquia de links
                for link in urls_encontradas:
                    l_lower = link.lower()
                    if "twitter.com" in l_lower or "x.com" in l_lower:
                        twitter_url = link
                    # Ignora redes sociais para a vaga de Site Oficial
                    elif any(bad in l_lower for bad in ['discord.com', 'discord.gg', 't.me', 'telegram', 'facebook', 'instagram', 'youtube', 'youtu.be', 'medium.com']):
                        continue
                    elif any(ext in l_lower for ext in [".fun", ".io", ".gg", ".xyz", ".net", ".com", "linktr.ee"]):
                        if site_url == "#":
                            site_url = link
                        # Se já temos um site, mas encontramos uma extensão puramente Web3, trancamos essa
                        elif any(web3 in l_lower for web3 in [".fun", ".io", ".xyz"]) and not any(web3 in site_url.lower() for web3 in [".fun", ".io", ".xyz"]):
                            site_url = link
                
                if site_url == "#" or site_url in sites_existentes:
                    continue
                
                nome_projeto = extrair_nome_provavel(titulo, site_url)
                
                rede = "Ethereum / Outra"
                if "solana" in conteudo_total or "sol" in conteudo_total: rede = "Solana"
                elif "ronin" in conteudo_total: rede = "Ronin"
                elif "immutable" in conteudo_total or "imx" in conteudo_total: rede = "Immutable X"
                elif "polygon" in conteudo_total: rede = "Polygon"
                
                score = 65 
                if "whitelist" in conteudo_total: score += 10
                if "airdrop" in conteudo_total: score += 10
                if twitter_url != "#": score += 15
                
                if int(visualizacoes) > 1000: score += 10
                
                proj = {
                    "nome": nome_projeto[:25],
                    "ticker": "TBA",
                    "rede": rede,
                    "estagio": "Underground / YouTube",
                    "investidores": "Prospecção YouTube",
                    "twitter_url": twitter_url,
                    "site_url": site_url,
                    "alpha_score": min(score, 100),
                    "data_publicacao": data_pub,
                    "visualizacoes": visualizacoes,
                    "video_url": video_link
                }
                
                supabase.table('crypto_games').insert(proj).execute()
                sites_existentes.append(site_url) 
                videos_existentes.append(video_link)
                novos_projetos_inseridos += 1
                
            if novos_projetos_inseridos > 0:
                st.toast(f'Varredura concluída! {novos_projetos_inseridos} projetos novos extraídos do YouTube.', icon='📡')
            else:
                st.toast('Vídeos analisados, mas nenhum link de site válido foi encontrado nas descrições.', icon='⚠️')
                
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
        
        data_pub = jogo.get('data_publicacao', 'N/A')
        views = jogo.get('visualizacoes', 'N/A')
        v_url = jogo.get('video_url', '#')
        
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
            <div class="info-row">
                <strong>📅 Publicado:</strong> {data_pub} | <strong>👁️ Views:</strong> {views}
            </div>
            <div class="info-row" style="margin-bottom: 15px;">
                <strong>Origem:</strong> {jogo.get('investidores', 'N/A')}
            </div>
            <div class="links-row">
                <a href="{jogo.get('twitter_url', '#')}" target="_blank">🐦 Twitter</a>
                <a href="{jogo.get('site_url', '#')}" target="_blank">🌐 Site Oficial</a>
                {f'<a href="{v_url}" target="_blank" class="yt-link">▶️ Fonte Original</a>' if v_url and v_url != '#' else ''}
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
