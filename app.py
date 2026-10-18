import streamlit as st
from supabase import create_client, Client
import requests
import re
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components

# --- Configuração da Página ---
st.set_page_config(page_title="Crypto Sniper", layout="wide", initial_sidebar_state="expanded")

# --- Conexão Segura com Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- Controle de Estado de Navegação e Automação ---
if 'modulo_ativo' not in st.session_state:
    st.session_state.modulo_ativo = "Game Sniper"
if 'pagina' not in st.session_state:
    st.session_state.pagina = "Buscar projetos"
if 'mostrar_form_manual' not in st.session_state:
    st.session_state.mostrar_form_manual = False
if 'auto_sniper' not in st.session_state:
    st.session_state.auto_sniper = False

# --- Estilização CSS (Tema Dark & Teal SaaS + Menu Lateral Customizado) ---
css = """
<style>
/* Fundo Geral e Sidebar */
.stApp { background-color: #0B0E11; color: #EAECEF; }
[data-testid="stSidebar"] { background-color: #080A0C; border-right: 1px solid #14181F; }
.block-container { padding-top: 1.8rem !important; max-width: 96% !important; }

/* Tipografia */
.breadcrumb { font-size: 13px; color: #848E9C; margin-bottom: 15px; font-weight: 500; }
.breadcrumb span { color: #00E6A8; font-weight: 600; }
.main-title { font-size: 32px; font-weight: 800; color: #FFFFFF; margin: 0 0 4px 0; letter-spacing: -0.5px; }
.sub-title { font-size: 15px; color: #848E9C; margin-bottom: 24px; }

/* Cards, KPIs e Progresso */
.kpi-card { background-color: #12161C; border: 1px solid #1E242D; border-radius: 12px; padding: 18px 20px; display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.kpi-icon { width: 46px; height: 46px; border-radius: 10px; background-color: #192028; display: flex; align-items: center; justify-content: center; font-size: 20px; border: 1px solid #252E3A; }
.kpi-label { font-size: 13px; color: #848E9C; margin: 0 0 2px 0; }
.kpi-val { font-size: 26px; font-weight: 800; color: #FFFFFF; margin: 0; line-height: 1.1; }

.sniper-card { background-color: #12161C; border: 1px solid #1E242D; border-radius: 12px; padding: 18px; margin-bottom: 8px; transition: border-color 0.2s; position: relative; }
.sniper-card:hover { border-color: #2B3645; }
.card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
.game-name { font-size: 18px; font-weight: 700; color: #FFFFFF; margin: 0 0 6px 0; }
.badge-tba { background-color: #1C222B; color: #848E9C; font-size: 11px; padding: 3px 8px; border-radius: 5px; font-weight: 600; display: inline-block; margin-bottom: 8px; }
.net-pill { background-color: #191E26; border: 1px solid #262E3B; color: #EAECEF; font-size: 12px; padding: 4px 10px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px; font-weight: 500; }

.score-wrapper { display: flex; align-items: baseline; gap: 4px; }
.score-box { font-weight: 800; font-size: 16px; padding: 5px 10px; border-radius: 7px; color: #000; }
.score-green { background-color: #00E6A8; box-shadow: 0 0 12px rgba(0, 230, 168, 0.25); }
.score-yellow { background-color: #FCD535; box-shadow: 0 0 12px rgba(252, 213, 53, 0.25); }
.score-red { background-color: #F6465D; color: #FFF; }
.score-max { font-size: 12px; color: #5E6673; font-weight: 600; }

.progress-bg { width: 100%; height: 5px; background-color: #1E242D; border-radius: 3px; margin: 14px 0; overflow: hidden; }
.progress-fill-green { height: 100%; background-color: #00E6A8; border-radius: 3px; }
.progress-fill-yellow { height: 100%; background-color: #FCD535; border-radius: 3px; }
.progress-fill-red { height: 100%; background-color: #F6465D; border-radius: 3px; }

.meta-line { font-size: 12px; color: #848E9C; margin-bottom: 12px; display: flex; gap: 12px; align-items: center; }
.links-line { font-size: 13px; padding-top: 12px; border-top: 1px solid #1E242D; display: flex; gap: 14px; align-items: center; }
.links-line a { color: #848E9C; text-decoration: none; font-weight: 500; transition: color 0.2s; }
.links-line a:hover { color: #00E6A8; }

/* Botões do Streamlit */
div.stButton > button { background-color: #161B22; color: #EAECEF; border: 1px solid #262E3B; border-radius: 8px; font-weight: 600; font-size: 13px; padding: 0.45rem 1rem; transition: all 0.2s; }
div.stButton > button:hover { border-color: #00E6A8; color: #00E6A8; background-color: #121D1B; }
div.stButton > button[kind="primary"] { background-color: #00E6A8 !important; color: #06110E !important; border: none !important; font-weight: 700 !important; }
div.stButton > button[kind="primary"]:hover { background-color: #00C892 !important; box-shadow: 0 0 15px rgba(0, 230, 168, 0.35); }

/* Botão de X nas buscas (Simula um ícone discreto) */
.btn-deletar-x button { background: transparent !important; border: 1px solid #262E3B !important; color: #848E9C !important; font-size: 14px !important; padding: 0 8px !important; border-radius: 8px !important; height: 100% !important;}
.btn-deletar-x button:hover { background: #F6465D !important; color: #FFF !important; border-color: #F6465D !important; }

/* Menu (...) do Kanban */
[data-testid="stPopover"] > button { background: transparent !important; border: 1px solid #1E242D !important; color: #848E9C !important; padding: 2px 10px !important; min-height: 32px !important; }
[data-testid="stPopover"] > button:hover { border-color: #00E6A8 !important; color: #FFF !important; }

/* HUD do Auto Sniper */
.sentinel-hud { background: #071B17; border: 1px solid #00DCB0; padding: 12px; border-radius: 8px; display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 20px; box-shadow: inset 0 0 15px rgba(0,220,176,0.1); }
.sentinel-pulse { width: 10px; height: 10px; background-color: #00DCB0; border-radius: 50%; box-shadow: 0 0 8px #00DCB0; animation: pulse 1.5s infinite; }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0,220,176, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(0,220,176, 0); } 100% { box-shadow: 0 0 0 0 rgba(0,220,176, 0); } }
.sentinel-text { color: #00DCB0; font-size: 16px; font-weight: 700; letter-spacing: 1px; }

/* Kanban Cards e Timer */
.kanban-header { background-color: #12161C; border: 1px solid #1E242D; border-radius: 10px; padding: 12px 16px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }
.kanban-header-title { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px; margin: 0; }
.count-pill { background-color: #1E242D; color: #848E9C; font-size: 12px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
.k-card { background-color: #12161C; border: 1px solid #1E242D; border-radius: 10px; padding: 16px; margin-bottom: 6px; }
.k-info-line { font-size: 12px; color: #848E9C; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; }
.k-note-line { font-size: 12px; color: #6C7582; margin-top: 6px; display: flex; justify-content: space-between; align-items: center; font-style: italic; }
.k-action-link { color: #00E6A8 !important; text-decoration: none; font-weight: 600; font-size: 12px; }

/* O Novo Timer Regressivo */
.k-countdown { background-color: #071B17; border: 1px solid #00DCB0; color: #00E6A8; font-family: monospace; font-size: 13px; font-weight: bold; text-align: center; padding: 6px; border-radius: 6px; margin-top: 10px; box-shadow: inset 0 0 8px rgba(0,220,176,0.1); letter-spacing: 1px; transition: all 0.3s;}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- Ícones Oficiais das Redes (HTML) ---
def obter_icone_rede(rede):
    r = (rede or "").lower()
    if "solana" in r: return '<img src="https://cryptologos.cc/logos/solana-sol-logo.png?v=029" width="14" style="vertical-align:middle;"> Solana'
    elif "ethereum" in r: return '<img src="https://cryptologos.cc/logos/ethereum-eth-logo.png?v=029" width="14" style="vertical-align:middle;"> Ethereum'
    elif "polygon" in r: return '<img src="https://cryptologos.cc/logos/polygon-matic-logo.png?v=029" width="14" style="vertical-align:middle;"> Polygon'
    elif "avalanche" in r: return '<img src="https://cryptologos.cc/logos/avalanche-avax-logo.png?v=029" width="14" style="vertical-align:middle;"> Avalanche'
    elif "ronin" in r: return '⚔️ Ronin'
    elif "immutable" in r: return '🛡️ Immutable X'
    return f'⛓️ {rede}'

# --- Conversor de Data para o Timer ---
def data_pt_para_iso(data_str):
    meses = {"jan":"01", "fev":"02", "mar":"03", "abr":"04", "mai":"05", "jun":"06", "jul":"07", "ago":"08", "set":"09", "out":"10", "nov":"11", "dez":"12"}
    try:
        partes = data_str.split()
        if len(partes) == 3:
            dia = partes[0].zfill(2)
            mes = meses.get(partes[1].lower(), "01")
            ano = partes[2]
            return f"{ano}-{mes}-{dia}T00:00:00"
    except:
        pass
    return ""

# --- Funções de Banco de Dados ---
def buscar_todos_jogos():
    # Ordenado por ID decrescente para os mais recentes ficarem no topo (Fim da fila resolvido)
    res = supabase.table('crypto_games').select("*").order('id', desc=True).execute()
    return res.data or []

def apagar_jogo(jogo_id):
    supabase.table('crypto_games').delete().eq('id', jogo_id).execute()

def limpar_dashboard_inteiro():
    jogos = buscar_todos_jogos()
    for j in jogos:
        if j.get('kanban_status') not in ['Aguardando Lançamento', 'Lançado']:
            apagar_jogo(j['id'])
    st.toast('🚨 Tela de busca limpa! Projetos salvos foram protegidos.', icon='🗑️')

def atualizar_status_kanban(jogo_id, novo_status):
    res = supabase.table('crypto_games').update({'kanban_status': novo_status}).eq('id', jogo_id).execute()
    if not res.data: st.error("⚠️ Erro de permissão no Supabase (UPDATE).")
    else: st.toast(f'Projeto movido para: {novo_status}', icon='✅')

def salvar_detalhes_kanban(jogo_id, data_str, anotacao_str):
    dados = {}
    if data_str is not None: dados['data_lancamento'] = data_str
    if anotacao_str is not None: dados['anotacoes'] = anotacao_str
    supabase.table('crypto_games').update(dados).eq('id', jogo_id).execute()
    st.toast('Alterações salvas!', icon='💾')

def inserir_projeto_manual(nome, rede, site_url, twitter_url, etapa="Aguardando Lançamento"):
    score = 65
    if site_url and len(site_url) > 5: score += 15
    if twitter_url and len(twitter_url) > 5: score += 10
    if rede in ["Solana", "Ronin"]: score += 5
    proj = {
        "nome": nome, "ticker": "A anunciar", "rede": rede, "alpha_score": min(score, 100),
        "estagio": "YouTube", "investidores": "Manual", "site_url": site_url or "#",
        "twitter_url": twitter_url or "#", "data_publicacao": datetime.now().strftime("%d %b %Y"),
        "visualizacoes": "0", "video_url": "#", "kanban_status": etapa, "anotacoes": ""
    }
    supabase.table('crypto_games').insert(proj).execute()
    st.toast(f'✅ {nome} adicionado em {etapa}!', icon='🎯')

# --- Funções Auxiliares e Motor YouTube Otimizado ---
def extrair_nome_provavel(titulo, site_url):
    if site_url != "#":
        url_limpa = site_url.split('?')[0]
        dominio = re.sub(r'https?://(www\.)?', '', url_limpa).split('/')[0]
        nome_dominio = dominio.split('.')[0]
        blacklist = ['discord', 'twitter', 'facebook', 'youtube', 'gate', 'linktr', 'medium', 'coinmarketcap', 'coingecko', 'binance', 'bybit', 't', 'telegram']
        if len(nome_dominio) > 2 and nome_dominio.lower() not in blacklist: return nome_dominio.capitalize()
    titulo_limpo = re.sub(r'[^a-zA-Z0-9\s]', '', titulo)
    palavras = titulo_limpo.split()
    stop_words = ['new', 'crypto', 'game', 'play', 'to', 'earn', 'free', 'solana', 'airdrop', 'the', 'best', 'review', 'tutorial', 'top', 'upcoming', 'update', 'everyday', 'setiap', 'hari', 'novo', 'jogo', 'nft', 'pagando', 'ganhar', 'dinheiro', 'gratis', 'grátis', 'lançamento', 'analise', 'análise', 'como', 'funciona', 'vale', 'a', 'pena']
    palavras_chave = [p for p in palavras if p.lower() not in stop_words]
    if palavras_chave: return " ".join(palavras_chave[0:3]).capitalize()
    return " ".join(palavras[0:3]).capitalize() if palavras else "Unknown"

def buscar_projetos_reais(custom_query=None):
    if "YOUTUBE_API_KEY" not in st.secrets:
        st.error("⚠️ Chave do YouTube não encontrada nos Secrets do Streamlit.")
        return

    with st.spinner('Rastreando novos projetos Web3 no YouTube...'):
        try:
            youtube_key = st.secrets["YOUTUBE_API_KEY"]
            existentes_db = supabase.table('crypto_games').select("site_url", "video_url").execute()
            sites_existentes = [x['site_url'] for x in existentes_db.data if x.get('site_url') and x.get('site_url') != "#"]
            videos_existentes = [x['video_url'] for x in existentes_db.data if x.get('video_url') and x.get('video_url') != "#"]
            
            data_limite = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat("T", "seconds").replace("+00:00", "Z")
            search_url = "https://www.googleapis.com/youtube/v3/search"
            
            # Novo motor de palavras-chave ampliado para captar "Evermagic", "Tokens" e "Ganhar dinheiro"
            query_padrao = '("novo jogo nft" OR "jogo nft" OR "crypto game" OR "play to earn" OR "mmorpg nft") (pagando OR ganhei dinheiro OR tokens OR token OR lançamento OR airdrop OR review)'
            query_final = custom_query if custom_query and len(custom_query.strip()) > 0 else query_padrao

            search_params = {
                "part": "snippet",
                "q": query_final,
                "type": "video", "order": "date", "publishedAfter": data_limite, "maxResults": 40, "key": youtube_key
            }
            search_resp = requests.get(search_url, params=search_params)
            if search_resp.status_code != 200:
                st.error("Erro na API do YouTube. Verifique sua cota ou chave.")
                return
                
            video_ids = [item['id']['videoId'] for item in search_resp.json().get('items', [])]
            if not video_ids:
                st.toast('Busca feita: nenhum vídeo relevante novo.', icon='⚠️')
                return
                
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            videos_resp = requests.get(videos_url, params={"part": "snippet,statistics", "id": ",".join(video_ids), "key": youtube_key}).json()
            
            novos = 0
            meses_pt = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
            
            for item in videos_resp.get('items', []):
                video_link = f"https://www.youtube.com/watch?v={item.get('id')}"
                if video_link in videos_existentes: continue
                    
                snippet = item.get('snippet', {})
                estatisticas = item.get('statistics', {})
                titulo = snippet.get('title', '')
                descricao = snippet.get('description', '')
                visualizacoes = estatisticas.get('viewCount', '0')
                
                try:
                    dt = datetime.strptime(snippet.get('publishedAt', ''), "%Y-%m-%dT%H:%M:%SZ")
                    data_pub = f"{dt.day} {meses_pt[dt.month-1]} {dt.year}"
                except:
                    data_pub = "Recente"
                    
                conteudo_total = (titulo + " " + descricao).lower()
                urls_encontradas = re.findall(r'https?://[^\s)\]"]+', descricao)
                site_url, twitter_url = "#", "#"
                
                for link in urls_encontradas:
                    l_lower = link.lower()
                    if "twitter.com" in l_lower or "x.com" in l_lower: twitter_url = link
                    elif any(bad in l_lower for bad in ['discord.com', 'discord.gg', 't.me', 'telegram', 'facebook', 'instagram', 'youtube', 'youtu.be', 'medium.com']): continue
                    elif any(ext in l_lower for ext in [".fun", ".io", ".gg", ".xyz", ".net", ".com", "linktr.ee"]):
                        if site_url == "#": site_url = link
                        elif any(web3 in l_lower for web3 in [".fun", ".io", ".xyz"]) and not any(web3 in site_url.lower() for web3 in [".fun", ".io", ".xyz"]): site_url = link
                
                if site_url == "#" or site_url in sites_existentes: continue
                
                nome_projeto = extrair_nome_provavel(titulo, site_url)
                rede = "Solana" if ("solana" in conteudo_total or "sol" in conteudo_total) else "Ronin" if "ronin" in conteudo_total else "Polygon" if "polygon" in conteudo_total else "Ethereum"
                
                score = 65 
                if "whitelist" in conteudo_total or "lista branca" in conteudo_total: score += 10
                if "airdrop" in conteudo_total: score += 10
                if twitter_url != "#": score += 15
                if int(visualizacoes) > 1000: score += 10
                
                proj = {
                    "nome": nome_projeto[:25], "ticker": "A anunciar", "rede": rede, "alpha_score": min(score, 100),
                    "estagio": "YouTube", "investidores": "YouTube", "twitter_url": twitter_url, "site_url": site_url,
                    "data_publicacao": data_pub, "visualizacoes": visualizacoes,
                    "video_url": video_link, "kanban_status": "Radar", "anotacoes": ""
                }
                supabase.table('crypto_games').insert(proj).execute()
                sites_existentes.append(site_url)
                novos += 1
                
            if novos > 0: st.toast(f'{novos} novos projetos encontrados!', icon='🚀')
        except Exception as e:
            st.error(f"Erro na busca: {e}")

# --- Navegação Lateral (Sólida e Nativa) ---
from pathlib import Path
from urllib.parse import quote

def navegar_sidebar(campo, destino):
    st.session_state[campo] = destino

NAV_ICONS = {
    "game": '<path d="M6 7h12c2 0 3 2 3.5 5l.5 5c.2 2-2 3-3.5 1.5L16 16H8l-2.5 2.5C4 20 1.8 19 2 17l.5-5C3 9 4 7 6 7Z"/><path d="M7 10v5M4.5 12.5h5"/><circle cx="16" cy="11" r=".6"/><circle cx="19" cy="14" r=".6"/>',
    "crypto": '<rect x="3" y="14" width="4" height="7" rx="1"/><rect x="10" y="9" width="4" height="12" rx="1"/><rect x="17" y="3" width="4" height="18" rx="1"/>',
    "search": '<circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/>',
    "kanban": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18M6 7v5M12 7v9M18 7v3"/>',
}

def svg_nav_uri(body):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           'fill="none" stroke="white" stroke-width="1.7" '
           'stroke-linecap="round" stroke-linejoin="round">' + body + '</svg>')
    return 'data:image/svg+xml,' + quote(svg, safe='')

sidebar_css = '''
<style>
[data-testid="stSidebar"] { background: #0D1216 !important; border-right: 1px solid #20282F !important; }
@media (min-width: 769px) { [data-testid="stSidebar"][aria-expanded="true"] { width: 274px !important; min-width: 274px !important; max-width: 274px !important; } }
[data-testid="stSidebarContent"] { display: flex; flex-direction: column; min-height: 100dvh; }
[data-testid="stSidebarUserContent"] { padding: 0 20px 24px !important; display: flex; flex-direction: column; flex: 1; }
[data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] { flex: 1; gap: 0 !important; }
[data-testid="stSidebarUserContent"] > div:has(> [data-testid="stVerticalBlock"]) { display: flex; flex-direction: column; flex: 1; }
[data-testid="stSidebar"] .st-key-sniper_brand { margin: 0 8px 46px; }
[data-testid="stSidebar"] .st-key-sniper_brand img { display: block; width: 100%; max-width: 234px; object-fit: contain; }
.sniper-brand-fallback { display: flex; align-items: center; gap: 8px; min-height: 56px; color: #F2F4F5; font-size: 23px; font-weight: 800; letter-spacing: -1px; white-space: nowrap; }
.sniper-brand-fallback svg { width: 38px; height: 38px; flex-shrink: 0; }
[data-testid="stSidebar"] .sidebar-section { margin: 0 8px 13px; color: #9AABBD; font-size: 11px; font-weight: 500; letter-spacing: 1.3px; line-height: 18px; }
[data-testid="stSidebar"] .sidebar-divider { height: 1px; background: #252D35; margin: 26px 0 24px; }
[data-testid="stSidebar"] :is(.st-key-nav_game, .st-key-nav_crypto, .st-key-nav_search, .st-key-nav_kanban) { margin-bottom: 6px; }
[data-testid="stSidebar"] :is(.st-key-nav_game, .st-key-nav_crypto, .st-key-nav_search, .st-key-nav_kanban) button { width: 100% !important; min-height: 47px !important; padding: 0 18px !important; border: 1px solid transparent !important; border-left: 1px solid transparent !important; border-radius: 9px !important; background: transparent !important; box-shadow: none !important; color: #ADBDCF !important; display: flex !important; align-items: center !important; justify-content: flex-start !important; gap: 16px !important; transition: background .18s ease, color .18s ease; }
[data-testid="stSidebar"] :is(.st-key-nav_game, .st-key-nav_crypto, .st-key-nav_search, .st-key-nav_kanban) button p { margin: 0 !important; color: inherit !important; font-size: 14px !important; font-weight: 500 !important; line-height: 1.2 !important; text-align: left !important; white-space: nowrap; }
[data-testid="stSidebar"] :is(.st-key-nav_game, .st-key-nav_crypto, .st-key-nav_search, .st-key-nav_kanban) button::before { content: ""; width: 21px; height: 21px; flex: 0 0 21px; background-color: currentColor; -webkit-mask: var(--nav-icon) center / contain no-repeat; mask: var(--nav-icon) center / contain no-repeat; }
[data-testid="stSidebar"] :is(.st-key-nav_game, .st-key-nav_crypto, .st-key-nav_search, .st-key-nav_kanban) button:hover { color: #EEF5F7 !important; background: #142027 !important; }
[data-testid="stSidebar"] :is(.st-key-nav_game, .st-key-nav_crypto, .st-key-nav_search, .st-key-nav_kanban) button:focus-visible { outline: 2px solid #00DCB0 !important; outline-offset: 3px; }
[data-testid="stSidebar"] .st-key-sniper_footer { margin-top: auto !important; padding-top: 32px; }
.sniper-online { display: flex; align-items: center; justify-content: space-between; min-height: 44px; padding: 0 16px; color: #DCE6EE; font-size: 13px; }
.sniper-online-label { display: flex; align-items: center; gap: 14px; }
.sniper-online-dot { width: 12px; height: 12px; border-radius: 50%; background: #00DCB0; box-shadow: 0 0 0 6px rgba(0,220,176,.09); }
.sniper-online-chevron { color: #93A6BA; font-size: 22px; }
</style>
'''

nav_items = [
    ("nav_game", "Game Sniper", "game", "modulo_ativo"),
    ("nav_crypto", "Crypto Sniper", "crypto", "modulo_ativo"),
    ("nav_search", "Buscar projetos", "search", "pagina"),
    ("nav_kanban", "Kanban", "kanban", "pagina"),
]
icon_css = []
for key, label, icon, state_key in nav_items:
    selector = f'[data-testid="stSidebar"] .st-key-{key} button'
    icon_css.append(f'{selector} {{ --nav-icon: url("{svg_nav_uri(NAV_ICONS[icon])}"); }}')
    if st.session_state[state_key] == label:
        icon_css.append(selector + ''' { background: linear-gradient(90deg, #0B302F, #102729) !important; border-color: #123436 !important; border-left-color: #00DCB0 !important; color: #8AF5F0 !important; }''')
st.markdown(sidebar_css + '<style>' + '\n'.join(icon_css) + '</style>', unsafe_allow_html=True)

with st.sidebar:
    with st.container(key="sniper_brand"):
        logo_path = Path(__file__).resolve().parent / "Crypto Sniper Logo.png"
        if logo_path.is_file(): st.image(str(logo_path), use_container_width=True)
        else: st.markdown('''<div class="sniper-brand-fallback"><svg viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M32 10a15 15 0 1 0 0 20" stroke="#00DCB0" stroke-width="6"/><path d="M23 11a10 10 0 0 1 0 18" stroke="#F2F4F5" stroke-width="3"/><circle cx="19" cy="20" r="5" fill="#00DCB0"/></svg><span>Crypto Sniper</span></div>''', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section">MÓDULOS</div>', unsafe_allow_html=True)
    for key, label, icon, state_key in nav_items[:2]:
        st.button(label, key=key, use_container_width=True, on_click=navegar_sidebar, args=(state_key, label))
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section">WORKSPACE</div>', unsafe_allow_html=True)
    for key, label, icon, state_key in nav_items[2:]:
        st.button(label, key=key, use_container_width=True, on_click=navegar_sidebar, args=(state_key, label))
    with st.container(key="sniper_footer"):
        st.markdown('''<div class="sniper-online" role="status"><span class="sniper-online-label"><span class="sniper-online-dot" aria-hidden="true"></span><span>Sistema online</span></span><span class="sniper-online-chevron" aria-hidden="true">›</span></div>''', unsafe_allow_html=True)

modulo = st.session_state.modulo_ativo
todos_jogos = buscar_todos_jogos()

# ==========================================
# MÓDULO: CRYPTO SNIPER (EM BREVE)
# ==========================================
if modulo == "Crypto Sniper":
    st.markdown("<div class='breadcrumb'>📊 Crypto Sniper / <span>Em breve</span></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Sniper de Tokens</h1><p class='sub-title'>Módulo de rastreamento on-chain em construção.</p>", unsafe_allow_html=True)

# ==========================================
# TELA 1: GAME SNIPER -> BUSCAR PROJETOS
# ==========================================
elif st.session_state.pagina == "Buscar projetos":
    
    # --- Topo (Títulos e Botões de Controle) ---
    col_t1, col_t2, col_t3 = st.columns([2.8, 1, 1.2])
    with col_t1:
        st.markdown("<div class='breadcrumb'>🎮 Game Sniper / <span>Busca</span></div>", unsafe_allow_html=True)
        st.markdown("<h1 class='main-title'>Descubra seu próximo projeto</h1><p class='sub-title'>Encontre, avalie e acompanhe novos jogos Web3.</p>", unsafe_allow_html=True)
    with col_t2:
        st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Limpar Busca", use_container_width=True, help="Remove projetos não adicionados"):
            limpar_dashboard_inteiro()
            st.rerun()
    with col_t3:
        st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
        if st.session_state.auto_sniper:
            if st.button("⏹ Parar Auto Sniper", type="primary", use_container_width=True):
                st.session_state.auto_sniper = False
                st.rerun()
        else:
            if st.button("▶ Iniciar Auto Sniper", type="primary", use_container_width=True):
                st.session_state.auto_sniper = True
                buscar_projetos_reais()
                st.rerun()

    # --- Busca Manual Customizada (Opcional) ---
    with st.expander("⚙️ Busca Manual (Palavras-chave personalizadas)"):
        c_kw, c_btn = st.columns([3, 1])
        with c_kw:
            custom_query = st.text_input("Termos de Busca", placeholder='Ex: "evermagic" OR "novo mmo nft" (Vazio = Radar Padrão)', label_visibility="collapsed")
        with c_btn:
            if st.button("⌖ Buscar Agora", use_container_width=True, type="primary"):
                buscar_projetos_reais(custom_query)
                st.rerun()

    # --- LÓGICA DO AUTO SNIPER (Timer 15 mins) ---
    if st.session_state.auto_sniper:
        st.markdown(f"<div class='sentinel-hud'><div class='sentinel-pulse'></div><div class='sentinel-text'>AUTO SNIPER ATIVO - PRÓXIMA VARREDURA EM: <span id='timer'>15:00</span></div></div>", unsafe_allow_html=True)
        st.markdown("<div style='display: none;'>", unsafe_allow_html=True)
        if st.button("TRIGGER_AUTOSNIPER", key="trigger_btn"):
            buscar_projetos_reais()
        st.markdown("</div>", unsafe_allow_html=True)
        components.html("""
        <script>
            var timeLeft = 900; 
            var timerId = setInterval(function() {
                var m = Math.floor(timeLeft / 60);
                var s = timeLeft % 60;
                var display = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
                var parentDoc = window.parent.document;
                var timerSpan = parentDoc.getElementById('timer');
                if(timerSpan) { timerSpan.innerHTML = display; }
                if (timeLeft <= 0) {
                    clearInterval(timerId);
                    if(timerSpan) { timerSpan.innerHTML = "Buscando..."; }
                    var buttons = parentDoc.querySelectorAll('button');
                    buttons.forEach(function(btn) { if(btn.innerText.includes('TRIGGER_AUTOSNIPER')) { btn.click(); } });
                }
                timeLeft--;
            }, 1000);
            setTimeout(function() {
                var parentDoc = window.parent.document;
                var buttons = parentDoc.querySelectorAll('button');
