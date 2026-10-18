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

# --- Estilização CSS Personalizada ---
css = """
<style>
div.stButton > button:first-child {
    background-color: #2B2B36;
    color: #FFFFFF;
    border: 1px solid #3A3A4A;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    transition: all 0.3s ease;
    font-weight: 600;
}
div.stButton > button:first-child:hover {
    border-color: #00BFFF;
    color: #00BFFF;
    box-shadow: 0 0 12px rgba(0, 191, 255, 0.2);
}
div.stButton > button[kind="primary"] {
    background-color: #3b1c1c;
    border-color: #FF3333;
    color: #FF3333;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #FF3333;
    color: #FFFFFF;
    box-shadow: 0 0 12px rgba(255, 51, 51, 0.4);
}
.sniper-card {
    background-color: #1E1E24;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 15px;
    border: 1px solid #333;
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}
.game-title-label {
    background-color: #2A2A38;
    padding: 6px 12px;
    border-radius: 6px;
    border-left: 4px solid #00BFFF;
    display: flex;
    align-items: baseline;
}
.game-title { font-size: 18px; font-weight: 800; color: #FFF; margin: 0; }
.game-ticker { font-size: 12px; color: #888; margin-left: 8px; font-weight: normal; }
.score-badge {
    background-color: #00FF66; color: #000; font-weight: 900; font-size: 18px;
    padding: 5px 12px; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 255, 102, 0.4);
}
.score-badge.medium { background-color: #FFD700; box-shadow: 0 0 10px rgba(255, 215, 0, 0.4); }
.score-badge.low { background-color: #FF3333; color: white; box-shadow: 0 0 10px rgba(255, 51, 51, 0.4); }
.tags-row { margin-bottom: 15px; font-size: 14px; color: #AAA;}
.tag { background: #333; padding: 4px 10px; border-radius: 6px; margin-right: 6px; color: #FFF; font-size: 12px;}
.info-row { font-size: 13px; color: #CCC; margin-bottom: 6px; }
.links-row { margin-top: 15px; padding-top: 15px; border-top: 1px solid #333;}
.links-row a { text-decoration: none; color: #00BFFF; margin-right: 15px; font-size: 14px; font-weight: bold; transition: color 0.2s; }
.links-row a:hover { color: #FFF; }
.yt-link { color: #FF6B6B !important; }
.kanban-date { color: #00FF66; font-weight: bold; font-size: 14px; margin-top: 5px;}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- Funções de Banco de Dados ---
def buscar_jogos(status_filtro=None):
    query = supabase.table('crypto_games').select("*").order('alpha_score', desc=True)
    if status_filtro:
        query = query.eq('kanban_status', status_filtro)
    return query.execute().data

def apagar_jogo(jogo_id):
    try:
        supabase.table('crypto_games').delete().eq('id', jogo_id).execute()
    except Exception as e:
        st.error(f"Erro de permissão ao deletar: {e}")

def alterar_status_kanban(jogo_id, novo_status):
    supabase.table('crypto_games').update({'kanban_status': novo_status}).eq('id', jogo_id).execute()

def salvar_data_lancamento(jogo_id, data_str):
    supabase.table('crypto_games').update({'data_lancamento': data_str}).eq('id', jogo_id).execute()
    st.toast('📅 Data salva com sucesso!', icon='✅')

def limpar_dashboard_inteiro():
    try:
        jogos = buscar_jogos('Radar')
        for j in jogos:
            supabase.table('crypto_games').delete().eq('id', j['id']).execute()
        st.toast('🚨 Radar limpo! (Jogos no Kanban foram protegidos)', icon='🗑️')
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
        "estagio": "Radar",
        "investidores": "Mapeamento Manual",
        "site_url": site_url,
        "twitter_url": twitter_url,
        "data_publicacao": datetime.now().strftime("%d/%m/%Y"),
        "kanban_status": "Radar"
    }
    supabase.table('crypto_games').insert(proj).execute()
    st.toast(f'✅ {nome} adicionado ao radar!', icon='🎯')

def extrair_nome_provavel(titulo, site_url):
    if site_url != "#":
        url_limpa = site_url.split('?')[0]
        dominio = re.sub(r'https?://(www\.)?', '', url_limpa).split('/')[0]
        nome_dominio = dominio.split('.')[0]
        blacklist = ['discord', 'twitter', 'facebook', 'youtube', 'gate', 'linktr', 'medium', 'coinmarketcap', 'coingecko', 'binance', 'bybit', 't', 'telegram']
        if len(nome_dominio) > 2 and nome_dominio.lower() not in blacklist:
            return nome_dominio.capitalize()
            
    titulo_limpo = re.sub(r'[^a-zA-Z0-9\s]', '', titulo)
    palavras = titulo_limpo.split()
    stop_words = ['new', 'crypto', 'game', 'play', 'to', 'earn', 'free', 'solana', 'airdrop', 'the', 'best', 'review', 'tutorial', 'top', 'upcoming', 'update', 'everyday', 'setiap', 'hari', 'novo', 'jogo', 'nft', 'pagando', 'ganhar', 'dinheiro', 'gratis', 'grátis', 'lançamento', 'analise', 'análise', 'como', 'funciona', 'vale', 'a', 'pena']
    palavras_chave = [p for p in palavras if p.lower() not in stop_words]
    
    if palavras_chave:
         return " ".join(palavras_chave[0:3]).capitalize()
    return " ".join(palavras[0:3]).capitalize() if palavras else "Unknown"

# --- Motor Alpha de Varredura YouTube ---
def buscar_projetos_reais():
    if "YOUTUBE_API_KEY" not in st.secrets:
        st.error("⚠️ Chave do YouTube não encontrada nos Secrets do Streamlit.")
        return

    with st.spinner('A analisar vídeos do YouTube dos últimos 5 dias...'):
        try:
            youtube_key = st.secrets["YOUTUBE_API_KEY"]
            existentes_db = supabase.table('crypto_games').select("site_url", "video_url").execute()
            sites_existentes = [x['site_url'] for x in existentes_db.data if x.get('site_url') and x.get('site_url') != "#"]
            videos_existentes = [x['video_url'] for x in existentes_db.data if x.get('video_url') and x.get('video_url') != "#"]
            
            data_limite = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat("T", "seconds").replace("+00:00", "Z")
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                "part": "snippet",
                "q": '("new crypto game" OR "solana game" OR "play to earn" OR "novo jogo nft" OR "jogo nft") (launch OR gameplay OR airdrop OR lançamento)',
                "type": "video", "order": "date", "publishedAfter": data_limite, "maxResults": 40, "key": youtube_key
            }
            search_resp = requests.get(search_url, params=search_params)
            
            if search_resp.status_code != 200:
                st.error(f"Erro na API do YouTube.")
                return
                
            dados_busca = search_resp.json()
            video_ids = [item['id']['videoId'] for item in dados_busca.get('items', [])]
            if not video_ids:
                st.toast('Nenhum vídeo relevante publicado nos últimos 5 dias.', icon='⚠️')
                return
                
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            videos_params = {"part": "snippet,statistics", "id": ",".join(video_ids), "key": youtube_key}
            videos_resp = requests.get(videos_url, params=videos_params).json()
            
            novos_projetos_inseridos = 0
            for item in videos_resp.get('items', []):
                video_link = f"https://www.youtube.com/watch?v={item.get('id')}"
                if video_link in videos_existentes: continue
                    
                snippet = item.get('snippet', {})
                estatisticas = item.get('statistics', {})
                titulo = snippet.get('title', '')
                descricao = snippet.get('description', '')
                data_pub_raw = snippet.get('publishedAt', '')
                visualizacoes = estatisticas.get('viewCount', '0')
                
                try: data_pub = datetime.strptime(data_pub_raw, "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")
                except: data_pub = "Recente"
                    
                conteudo_total = (titulo + " " + descricao).lower()
                urls_encontradas = re.findall(r'https?://[^\s)\]"]+', descricao)
                site_url = "#"
                twitter_url = "#"
                
                for link in urls_encontradas:
                    l_lower = link.lower()
                    if "twitter.com" in l_lower or "x.com" in l_lower: twitter_url = link
                    elif any(bad in l_lower for bad in ['discord.com', 'discord.gg', 't.me', 'telegram', 'facebook', 'instagram', 'youtube', 'youtu.be', 'medium.com']): continue
                    elif any(ext in l_lower for ext in [".fun", ".io", ".gg", ".xyz", ".net", ".com", "linktr.ee"]):
                        if site_url == "#": site_url = link
                        elif any(web3 in l_lower for web3 in [".fun", ".io", ".xyz"]) and not any(web3 in site_url.lower() for web3 in [".fun", ".io", ".xyz"]): site_url = link
                
                if site_url == "#" or site_url in sites_existentes: continue
                
                nome_projeto = extrair_nome_provavel(titulo, site_url)
                rede = "Solana" if "solana" in conteudo_total or "sol" in conteudo_total else "Ronin" if "ronin" in conteudo_total else "Ethereum / Outra"
                
                score = 65 
                if "whitelist" in conteudo_total or "lista branca" in conteudo_total: score += 10
                if "airdrop" in conteudo_total: score += 10
                if twitter_url != "#": score += 15
                if int(visualizacoes) > 1000: score += 10
                
                proj = {
                    "nome": nome_projeto[:25], "ticker": "TBA", "rede": rede, "estagio": "YouTube",
                    "investidores": "Prospecção YouTube", "twitter_url": twitter_url, "site_url": site_url,
                    "alpha_score": min(score, 100), "data_publicacao": data_pub, "visualizacoes": visualizacoes,
                    "video_url": video_link, "kanban_status": "Radar"
                }
                supabase.table('crypto_games').insert(proj).execute()
                sites_existentes.append(site_url) 
                novos_projetos_inseridos += 1
                
            if novos_projetos_inseridos > 0: st.toast(f'Varredura concluída! {novos_projetos_inseridos} projetos novos extraídos.', icon='📡')
            else: st.toast('Busca feita (5 dias). Nenhum link novo encontrado.', icon='⚠️')
        except Exception as e:
            st.error(f"Erro inesperado no sistema de busca: {e}")

# --- Barra Lateral (Menu e Controles) ---
with st.sidebar:
    try:
        st.image("Crypto Sniper Logo.png", use_container_width=True)
    except FileNotFoundError:
        st.markdown("<h2 style='text-align: center; margin-bottom: 30px; color: #FFF;'>🎯 Crypto Sniper</h2>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # SISTEMA DE NAVEGAÇÃO
    pagina_atual = st.radio("Navegação do Sistema", ["📍 Radar de Caça", "📋 Kanban de Lançamentos"], label_visibility="collapsed")
    
    st.divider()
    
    if pagina_atual == "📍 Radar de Caça":
        if st.button("🚀 Buscar Crypto Games", use_container_width=True):
            buscar_projetos_reais()
            
        st.subheader("🔎 Filtros")
        filtro_rede = st.selectbox("Rede", ["Todas", "Solana", "Ronin", "Immutable X", "Polygon", "Avalanche", "Outra"])
        
        with st.expander("➕ Adicionar Projeto Manual"):
            with st.form("form_manual"):
                m_nome = st.text_input("Nome do Jogo")
                m_rede = st.selectbox("Rede", ["Solana", "Ronin", "Immutable X", "Polygon", "Avalanche", "Outra"])
                m_site = st.text_input("Link do Site")
                m_twitter = st.text_input("Link do Twitter")
                if st.form_submit_button("Salvar no Radar", use_container_width=True) and m_nome:
                    inserir_projeto_manual(m_nome, m_rede, m_site, m_twitter)

        st.divider()
        if st.button("🚨 Limpar Apenas o Radar", type="primary", use_container_width=True):
            limpar_dashboard_inteiro()

# --- Renderização HTML do Card Comum ---
def renderizar_card(jogo, mostrar_botoes_radar=False, mostrar_botoes_kanban=False):
    score = jogo['alpha_score']
    badge_class = "score-badge low" if score < 60 else "score-badge medium" if score < 85 else "score-badge"
    v_url = jogo.get('video_url', '#')
    
    data_lanc_html = ""
    if jogo.get('data_lancamento'):
        data_lanc_html = f"<div class='kanban-date'>🚀 Lançamento: {jogo['data_lancamento']}</div>"
    
    html = f"""
    <div class="sniper-card">
        <div class="card-header">
            <div class="game-title-label">
                <span class="game-title">{jogo['nome']}</span>
                <span class="game-ticker">{jogo['ticker'] or ''}</span>
            </div>
            <div class="{badge_class}">{score}</div>
        </div>
        <div class="tags-row">
            <span class="tag">⛓️ {jogo['rede']}</span>
        </div>
        <div class="info-row"><strong>📅 Encontrado:</strong> {jogo.get('data_publicacao', 'N/A')} | <strong>👁️ Views:</strong> {jogo.get('visualizacoes', 'N/A')}</div>
        {data_lanc_html}
        <div class="links-row">
            <a href="{jogo.get('twitter_url', '#')}" target="_blank">🐦 Twitter</a>
            <a href="{jogo.get('site_url', '#')}" target="_blank">🌐 Site Oficial</a>
            {f'<a href="{v_url}" target="_blank" class="yt-link">▶️ Fonte</a>' if v_url and v_url != '#' else ''}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    
    # Botões do Radar (Adicionar à Esquerda, Deletar à Direita)
    if mostrar_botoes_radar:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ Adicionar", key=f"add_{jogo['id']}", use_container_width=True):
                alterar_status_kanban(jogo['id'], 'Aguardando Lançamento')
                st.rerun()
        with b2:
            if st.button("Deletar", key=f"del_{jogo['id']}", use_container_width=True):
                apagar_jogo(jogo['id'])
                st.rerun()

    # Botões e Controles do Kanban
    if mostrar_botoes_kanban:
        with st.expander("📅 Marcar Data"):
            col_data, col_btn = st.columns([2, 1])
            with col_data:
                data_escolhida = st.date_input("Data", key=f"date_{jogo['id']}")
            with col_btn:
                # Usa espaço em branco para alinhar o botão
                st.write("") 
                if st.button("Salvar", key=f"save_dt_{jogo['id']}", use_container_width=True):
                    salvar_data_lancamento(jogo['id'], data_escolhida.strftime("%d/%m/%Y"))
                    st.rerun()
                    
        k1, k2 = st.columns(2)
        with k1:
            if jogo['kanban_status'] == 'Aguardando Lançamento':
                if st.button("✅ Lançado", key=f"pass_{jogo['id']}", use_container_width=True):
                    alterar_status_kanban(jogo['id'], 'Lançado')
                    st.rerun()
            else:
                if st.button("⏪ Voltar", key=f"back_{jogo['id']}", use_container_width=True):
                    alterar_status_kanban(jogo['id'], 'Aguardando Lançamento')
                    st.rerun()
        with k2:
            if st.button("🗑️ Excluir", key=f"kdel_{jogo['id']}", use_container_width=True):
                apagar_jogo(jogo['id'])
                st.rerun()

# --- Lógica de Exibição das Páginas ---
st.markdown("<br>", unsafe_allow_html=True)

if pagina_atual == "📍 Radar de Caça":
    jogos = buscar_jogos(status_filtro='Radar')
    if not jogos:
        st.info("O radar está limpo. Busque novos projetos.")
    else:
        col1, col2, col3 = st.columns(3)
        for idx, jogo in enumerate(jogos):
            if filtro_rede != "Todas" and jogo['rede'] != filtro_rede: continue
            if idx % 3 == 0:
                with col1: renderizar_card(jogo, mostrar_botoes_radar=True)
            elif idx % 3 == 1:
                with col2: renderizar_card(jogo, mostrar_botoes_radar=True)
            else:
                with col3: renderizar_card(jogo, mostrar_botoes_radar=True)

elif pagina_atual == "📋 Kanban de Lançamentos":
    col_aguardando, col_lancado = st.columns(2)
    
    with col_aguardando:
        st.markdown("<h3 style='text-align: center; color: #FFD700;'>⏳ Aguardando Lançamento</h3>", unsafe_allow_html=True)
        jogos_ag = buscar_jogos(status_filtro='Aguardando Lançamento')
        for jogo in jogos_ag:
            renderizar_card(jogo, mostrar_botoes_kanban=True)
            
    with col_lancado:
        st.markdown("<h3 style='text-align: center; color: #00FF66;'>🚀 Projetos Lançados</h3>", unsafe_allow_html=True)
        jogos_lanc = buscar_jogos(status_filtro='Lançado')
        for jogo in jogos_lanc:
            renderizar_card(jogo, mostrar_botoes_kanban=True)
