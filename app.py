import streamlit as st
from supabase import create_client, Client, ClientOptions
import requests
import re
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components
from pathlib import Path
from urllib.parse import quote

# --- Configuração da Página ---
st.set_page_config(page_title="Crypto Sniper", layout="wide", initial_sidebar_state="expanded")

# --- Conexão Segura com Supabase ---
def init_connection(access_token):
    import os
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = {}
    url = os.getenv("SUPABASE_URL") or secrets.get("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or secrets.get("SUPABASE_KEY")
    return create_client(url, key, options=ClientOptions(headers={'Authorization': 'Bearer '+access_token}, persist_session=False, auto_refresh_token=False)) if url and key else None

# --- Controle de Estado de Navegação e Automação ---
if 'modulo_ativo' not in st.session_state:
    st.session_state.modulo_ativo = "Dex Trade"
if st.session_state.modulo_ativo == "Meme Trader":
    st.session_state.modulo_ativo = "Dex Trade"
if 'pagina' not in st.session_state:
    st.session_state.pagina = "Buscar projetos"
if 'mostrar_form_manual' not in st.session_state:
    st.session_state.mostrar_form_manual = False
if 'auto_sniper' not in st.session_state:
    st.session_state.auto_sniper = False
if 'menu_expandido' not in st.session_state:
    st.session_state.menu_expandido = False

# --- Estilização CSS ---
css = """
<style>
.stApp { background-color: #0B0E11; color: #EAECEF; }
[data-testid="stSidebar"] { background-color: #080A0C; border-right: 1px solid #14181F; }
.block-container { padding-top: 1.8rem !important; max-width: 96% !important; }

.breadcrumb { font-size: 13px; color: #848E9C; margin-bottom: 15px; font-weight: 500; }
.breadcrumb span { color: #00E6A8; font-weight: 600; }
.main-title { font-size: 32px; font-weight: 800; color: #FFFFFF; margin: 0 0 4px 0; letter-spacing: -0.5px; }
.sub-title { font-size: 15px; color: #848E9C; margin-bottom: 24px; }

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

div.stButton > button { background-color: #161B22; color: #EAECEF; border: 1px solid #262E3B; border-radius: 8px; font-weight: 600; font-size: 13px; padding: 0.45rem 1rem; transition: all 0.2s; }
div.stButton > button:hover { border-color: #00E6A8; color: #00E6A8; background-color: #121D1B; }
div.stButton > button[kind="primary"] { background-color: #00E6A8 !important; color: #06110E !important; border: none !important; font-weight: 700 !important; }
div.stButton > button[kind="primary"]:hover { background-color: #00C892 !important; box-shadow: 0 0 15px rgba(0, 230, 168, 0.35); }

.btn-deletar-x button { background: transparent !important; border: 1px solid #262E3B !important; color: #848E9C !important; font-size: 14px !important; padding: 0 8px !important; border-radius: 8px !important; height: 100% !important; }
.btn-deletar-x button:hover { background: #F6465D !important; color: #FFF !important; border-color: #F6465D !important; }
[data-testid="stPopover"] > button { background: transparent !important; border: 1px solid #1E242D !important; color: #848E9C !important; padding: 2px 10px !important; min-height: 32px !important; }
[data-testid="stPopover"] > button:hover { border-color: #00E6A8 !important; color: #FFF !important; }

.sentinel-hud { background: #071B17; border: 1px solid #00DCB0; padding: 12px; border-radius: 8px; display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 20px; box-shadow: inset 0 0 15px rgba(0,220,176,0.1); }
.sentinel-pulse { width: 10px; height: 10px; background-color: #00DCB0; border-radius: 50%; box-shadow: 0 0 8px #00DCB0; animation: pulse 1.5s infinite; }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0,220,176, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(0,220,176, 0); } 100% { box-shadow: 0 0 0 0 rgba(0,220,176, 0); } }
.sentinel-text { color: #00DCB0; font-size: 16px; font-weight: 700; letter-spacing: 1px; }

.kanban-header { background-color: #12161C; border: 1px solid #1E242D; border-radius: 10px; padding: 12px 12px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }
.kanban-header-title { font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 8px; margin: 0; }
.count-pill { background-color: #1E242D; color: #848E9C; font-size: 12px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
.k-card { background-color: #12161C; border: 1px solid #1E242D; border-radius: 10px; padding: 14px; margin-bottom: 8px; }
.k-info-line { font-size: 11px; color: #848E9C; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; }
.k-note-line { font-size: 11px; color: #6C7582; margin-top: 6px; display: flex; justify-content: space-between; align-items: center; font-style: italic; }
.k-action-link { color: #00E6A8 !important; text-decoration: none; font-weight: 600; font-size: 11px; }
.k-countdown { background-color: #071B17; border: 1px solid #00DCB0; color: #00E6A8; font-family: monospace; font-size: 12px; font-weight: 700; text-align: center; padding: 6px; border-radius: 6px; margin-top: 10px; box-shadow: inset 0 0 8px rgba(0,220,176,0.1); letter-spacing: 1px; transition: all 0.3s; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# Authentication precedes all navigation, data loading and user actions.
from pump.account import require_login, logout, users_dashboard
profile = require_login()
supabase: Client = init_connection(st.session_state.sniper_session['access_token'])

# --- Ícones Oficiais das Redes ---
def obter_icone_rede(rede):
    r = (rede or "").lower()
    if "solana" in r: return '<img src="https://cryptologos.cc/logos/solana-sol-logo.png?v=029" width="14" style="vertical-align:middle;"> Solana'
    elif "ethereum" in r: return '<img src="https://cryptologos.cc/logos/ethereum-eth-logo.png?v=029" width="14" style="vertical-align:middle;"> Ethereum'
    elif "polygon" in r: return '<img src="https://cryptologos.cc/logos/polygon-matic-logo.png?v=029" width="14" style="vertical-align:middle;"> Polygon'
    elif "avalanche" in r: return '<img src="https://cryptologos.cc/logos/avalanche-avax-logo.png?v=029" width="14" style="vertical-align:middle;"> Avalanche'
    elif "ronin" in r: return '⚔️ Ronin'
    elif "immutable" in r: return '🛡️ Immutable X'
    return f'⛓️ {rede}'

# --- Conversor de Data ---
def data_pt_para_iso(data_str):
    meses = {"jan":"01", "fev":"02", "mar":"03", "abr":"04", "mai":"05", "jun":"06", "jul":"07", "ago":"08", "set":"09", "out":"10", "nov":"11", "dez":"12"}
    try:
        partes = data_str.split()
        if len(partes) == 3:
            dia = partes[0].zfill(2)
            mes = meses.get(partes[1].lower(), "01")
            ano = partes[2]
            return f"{ano}-{mes}-{dia}T00:00:00"
    except: pass
    return ""

# --- Funções de Banco de Dados ---
def buscar_todos_jogos():
    res = supabase.table('crypto_games').select("*").order('id', desc=True).execute()
    return res.data or []

def apagar_jogo(jogo_id):
    supabase.table('crypto_games').delete().eq('id', jogo_id).execute()

def limpar_dashboard_inteiro():
    jogos = buscar_todos_jogos()
    status_protegidos = ['Aguardando Lançamento', 'Lançado', 'Projetos que Entrei', 'Free to Earn']
    for j in jogos:
        if j.get('kanban_status') not in status_protegidos:
            apagar_jogo(j['id'])
    st.toast('🚨 Tela de busca limpa!', icon='🗑️')

def atualizar_status_kanban(jogo_id, novo_status):
    res = supabase.table('crypto_games').update({'kanban_status': novo_status}).eq('id', jogo_id).execute()
    if res.data: st.toast(f'Movido para: {novo_status}', icon='✅')

def salvar_detalhes_kanban(jogo_id, data_str, anotacao_str):
    dados = {}
    if data_str is not None: dados['data_lancamento'] = data_str
    if anotacao_str is not None: dados['anotacoes'] = anotacao_str
    supabase.table('crypto_games').update(dados).eq('id', jogo_id).execute()
    st.toast('Alterações salvas!', icon='💾')

def inserir_projeto_manual(nome, rede, site_url, twitter_url, etapa):
    score = 65
    if site_url and len(site_url) > 5: score += 15
    if twitter_url and len(twitter_url) > 5: score += 10
    if rede in ["Solana", "Ronin"]: score += 5
    proj = {
        "nome": nome, "ticker": "A anunciar", "rede": rede, "alpha_score": min(score, 100),
        "estagio": "Manual", "investidores": "Manual", "site_url": site_url or "#",
        "twitter_url": twitter_url or "#", "data_publicacao": datetime.now().strftime("%d %b %Y"),
        "visualizacoes": "0", "video_url": "#", "kanban_status": etapa, "anotacoes": ""
    }
    supabase.table('crypto_games').insert(proj).execute()
    st.toast(f'✅ {nome} adicionado em {etapa}!', icon='🎯')

def extrair_nome_provavel(titulo, site_url):
    if site_url != "#":
        url_limpa = site_url.split('?')[0]
        nome_dominio = re.sub(r'https?://(www\.)?', '', url_limpa).split('/')[0].split('.')[0]
        blacklist = ['discord','twitter','facebook','youtube','gate','linktr','medium','coinmarketcap','coingecko','binance','bybit','telegram']
        if len(nome_dominio) > 2 and nome_dominio.lower() not in blacklist: return nome_dominio.capitalize()
    palavras = re.sub(r'[^a-zA-Z0-9\s]', '', titulo).split()
    stop_words = ['new','crypto','game','play','to','earn','free','solana','airdrop','the','best','review','tutorial','top','upcoming','update','novo','jogo','nft','pagando','ganhar','dinheiro','gratis','lançamento','analise']
    chaves = [p for p in palavras if p.lower() not in stop_words]
    return " ".join(chaves[0:3]).capitalize() if chaves else (" ".join(palavras[0:3]).capitalize() if palavras else "Unknown")

def buscar_projetos_reais(custom_query=None):
    if "YOUTUBE_API_KEY" not in st.secrets:
        st.error("⚠️ Chave do YouTube não encontrada.")
        return
    with st.spinner('Rastreando novos projetos Web3 no YouTube...'):
        try:
            youtube_key = st.secrets["YOUTUBE_API_KEY"]
            existentes_db = supabase.table('crypto_games').select("site_url", "video_url").execute()
            sites_existentes = [x['site_url'] for x in existentes_db.data if x.get('site_url') and x.get('site_url') != "#"]
            videos_existentes = [x['video_url'] for x in existentes_db.data if x.get('video_url') and x.get('video_url') != "#"]
            
            data_limite = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat("T", "seconds").replace("+00:00", "Z")
            query_padrao = '("novo jogo nft" OR "jogo nft" OR "crypto game" OR "play to earn" OR "mmorpg nft") (pagando OR ganhei dinheiro OR tokens OR token OR lançamento OR airdrop OR review)'
            query_final = custom_query if custom_query and len(custom_query.strip()) > 0 else query_padrao

            search_resp = requests.get("https://www.googleapis.com/youtube/v3/search", params={"part":"snippet", "q":query_final, "type":"video", "order":"date", "publishedAfter":data_limite, "maxResults":40, "key":youtube_key})
            if search_resp.status_code != 200: return st.error("Erro na API do YouTube.")
                
            video_ids = [item['id']['videoId'] for item in search_resp.json().get('items', [])]
            if not video_ids: return st.toast('Nenhum vídeo novo.', icon='⚠️')
                
            videos_resp = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part":"snippet,statistics", "id":",".join(video_ids), "key":youtube_key}).json()
            novos = 0
            meses_pt = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
            
            for item in videos_resp.get('items', []):
                vlink = f"https://www.youtube.com/watch?v={item.get('id')}"
                if vlink in videos_existentes: continue
                    
                snippet, stats = item.get('snippet', {}), item.get('statistics', {})
                titulo, desc = snippet.get('title', ''), snippet.get('description', '')
                views = stats.get('viewCount', '0')
                
                try:
                    dt = datetime.strptime(snippet.get('publishedAt', ''), "%Y-%m-%dT%H:%M:%SZ")
                    data_pub = f"{dt.day} {meses_pt[dt.month-1]} {dt.year}"
                except: data_pub = "Recente"
                    
                full_text = (titulo + " " + desc).lower()
                urls = re.findall(r'https?://[^\s)\]"]+', desc)
                site_url, twitter_url = "#", "#"
                
                for link in urls:
                    low = link.lower()
                    if "twitter.com" in low or "x.com" in low: twitter_url = link
                    elif any(b in low for b in ['discord','t.me','telegram','facebook','instagram','youtube','medium.com']): continue
                    elif any(ext in low for ext in [".fun",".io",".gg",".xyz",".net",".com","linktr.ee"]):
                        if site_url == "#": site_url = link
                        elif any(w in low for w in [".fun",".io",".xyz"]) and not any(w in site_url.lower() for w in [".fun",".io",".xyz"]): site_url = link
                
                if site_url == "#" or site_url in sites_existentes: continue
                
                nome = extrair_nome_provavel(titulo, site_url)
                rede = "Solana" if "solana" in full_text else "Ronin" if "ronin" in full_text else "Polygon" if "polygon" in full_text else "Ethereum"
                
                score = 65 
                if "whitelist" in full_text or "lista branca" in full_text: score += 10
                if "airdrop" in full_text: score += 10
                if twitter_url != "#": score += 15
                if int(views) > 1000: score += 10
                
                supabase.table('crypto_games').insert({"nome":nome[:25], "ticker":"A anunciar", "rede":rede, "alpha_score":min(score, 100), "estagio":"YouTube", "investidores":"YouTube", "twitter_url":twitter_url, "site_url":site_url, "data_publicacao":data_pub, "visualizacoes":views, "video_url":vlink, "kanban_status":"Radar", "anotacoes":""}).execute()
                sites_existentes.append(site_url)
                novos += 1
                
            if novos > 0: st.toast(f'{novos} projetos encontrados!', icon='🚀')
        except Exception as e: st.error(f"Erro na busca.")

# --- Lógica de Navegação e Acordeão ---
def nav_main(destino):
    st.session_state.modulo_ativo = destino
    if destino == "Game Sniper":
        st.session_state.menu_expandido = not st.session_state.menu_expandido
    else:
        st.session_state.menu_expandido = False

def nav_sub(destino):
    st.session_state.pagina = destino

# Configuração de Menus
nav_items_main = [
    ("nav_pump", "Pump Trader", "pump", "modulo_ativo"),
    ("nav_meme", "Dex Trade", "meme", "modulo_ativo"),
    ("nav_altcoin", "Altcoin Trader", "crypto", "modulo_ativo"),
    ("nav_game", "Game Sniper", "game", "modulo_ativo"),
]

nav_items_sub = [
    ("nav_sub_search", "Buscar projetos", "search", "pagina"),
    ("nav_sub_kanban", "Kanban", "kanban", "pagina"),
]

NAV_ICONS = {
    "pump": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "meme": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    "crypto": '<rect x="3" y="14" width="4" height="7" rx="1"/><rect x="10" y="9" width="4" height="12" rx="1"/><rect x="17" y="3" width="4" height="18" rx="1"/>',
    "game": '<path d="M6 7h12c2 0 3 2 3.5 5l.5 5c.2 2-2 3-3.5 1.5L16 16H8l-2.5 2.5C4 20 1.8 19 2 17l.5-5C3 9 4 7 6 7Z"/><path d="M7 10v5M4.5 12.5h5"/><circle cx="16" cy="11" r=".6"/><circle cx="19" cy="14" r=".6"/>',
    "search": '<circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/>',
    "kanban": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18M6 7v5M12 7v9M18 7v3"/>',
}

def svg_nav_uri(body):
    return 'data:image/svg+xml,' + quote('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + body + '</svg>', safe='')

sidebar_css = """
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
[data-testid="stSidebar"] :is(.st-key-nav_pump, .st-key-nav_meme, .st-key-nav_altcoin, .st-key-nav_game, .st-key-nav_sub_search, .st-key-nav_sub_kanban) { margin-bottom: 6px; }
[data-testid="stSidebar"] :is(.st-key-nav_pump, .st-key-nav_meme, .st-key-nav_altcoin, .st-key-nav_game, .st-key-nav_sub_search, .st-key-nav_sub_kanban) button { width: 100% !important; min-height: 47px !important; padding: 0 18px !important; border: 1px solid transparent !important; border-left: 1px solid transparent !important; border-radius: 9px !important; background: transparent !important; box-shadow: none !important; color: #ADBDCF !important; display: flex !important; align-items: center !important; justify-content: flex-start !important; gap: 16px !important; transition: background .18s ease, color .18s ease; }
[data-testid="stSidebar"] :is(.st-key-nav_pump, .st-key-nav_meme, .st-key-nav_altcoin, .st-key-nav_game, .st-key-nav_sub_search, .st-key-nav_sub_kanban) button p { margin: 0 !important; color: inherit !important; font-size: 14px !important; font-weight: 500 !important; line-height: 1.2 !important; text-align: left !important; white-space: nowrap; }
[data-testid="stSidebar"] :is(.st-key-nav_pump, .st-key-nav_meme, .st-key-nav_altcoin, .st-key-nav_game, .st-key-nav_sub_search, .st-key-nav_sub_kanban) button::before { content: ""; width: 21px; height: 21px; flex: 0 0 21px; background-color: currentColor; -webkit-mask: var(--nav-icon) center / contain no-repeat; mask: var(--nav-icon) center / contain no-repeat; }
[data-testid="stSidebar"] :is(.st-key-nav_pump, .st-key-nav_meme, .st-key-nav_altcoin, .st-key-nav_game, .st-key-nav_sub_search, .st-key-nav_sub_kanban) button:hover { color: #EEF5F7 !important; background: #142027 !important; }
[data-testid="stSidebar"] :is(.st-key-nav_pump, .st-key-nav_meme, .st-key-nav_altcoin, .st-key-nav_game, .st-key-nav_sub_search, .st-key-nav_sub_kanban) button:focus-visible { outline: 2px solid #00DCB0 !important; outline-offset: 3px; }

/* Indentação elegante pros submenus */
[data-testid="stSidebar"] :is(.st-key-nav_sub_search, .st-key-nav_sub_kanban) button { width: calc(100% - 24px) !important; margin-left: 24px !important; min-height: 40px !important; font-size: 13px !important; border-radius: 0 8px 8px 0 !important; border-left: 2px solid #1E242D !important; }
[data-testid="stSidebar"] :is(.st-key-nav_sub_search, .st-key-nav_sub_kanban) button:hover { border-left-color: #00E6A8 !important; }

[data-testid="stSidebar"] .st-key-sniper_footer { margin-top: auto !important; padding-top: 32px; }
.sniper-online { display: flex; align-items: center; justify-content: space-between; min-height: 44px; padding: 0 16px; color: #DCE6EE; font-size: 13px; }
.sniper-online-label { display: flex; align-items: center; gap: 14px; }
.sniper-online-dot { width: 12px; height: 12px; border-radius: 50%; background: #00DCB0; box-shadow: 0 0 0 6px rgba(0,220,176,.09); }
.sniper-online-chevron { color: #93A6BA; font-size: 22px; }
</style>
"""

icon_css = []
for key, label, icon, state_key in nav_items_main:
    selector = f'[data-testid="stSidebar"] .st-key-{key} button'
    icon_css.append(f'{selector} {{ --nav-icon: url("{svg_nav_uri(NAV_ICONS[icon])}"); }}')
    if st.session_state[state_key] == label:
        icon_css.append(selector + ''' { background: linear-gradient(90deg, #0B302F, #102729) !important; border-color: #123436 !important; border-left-color: #00DCB0 !important; color: #8AF5F0 !important; }''')

for key, label, icon, state_key in nav_items_sub:
    selector = f'[data-testid="stSidebar"] .st-key-{key} button'
    icon_css.append(f'{selector} {{ --nav-icon: url("{svg_nav_uri(NAV_ICONS[icon])}"); }}')
    if st.session_state[state_key] == label and st.session_state.modulo_ativo == "Game Sniper":
        icon_css.append(selector + ''' { background: #142027 !important; border-left-color: #00DCB0 !important; color: #8AF5F0 !important; }''')

st.markdown(sidebar_css + '<style>' + '\n'.join(icon_css) + '</style>', unsafe_allow_html=True)

with st.sidebar:
    with st.container(key="sniper_brand"):
        logo_path = Path(__file__).resolve().parent / "Crypto Sniper Logo.png"
        if logo_path.is_file():
            st.image(str(logo_path), use_container_width=True)
        else:
            st.markdown('''<div class="sniper-brand-fallback"><svg viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M32 10a15 15 0 1 0 0 20" stroke="#00DCB0" stroke-width="6"/><path d="M23 11a10 10 0 0 1 0 18" stroke="#F2F4F5" stroke-width="3"/><circle cx="19" cy="20" r="5" fill="#00DCB0"/></svg><span>Crypto Sniper</span></div>''', unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-section">MÓDULOS</div>', unsafe_allow_html=True)
    
    for key, label, icon, state_key in nav_items_main:
        if label == 'Game Sniper' and profile['role'] != 'admin':
            continue
        display_label = label
        if label == "Game Sniper":
            display_label = f"{label}  ▾" if not st.session_state.menu_expandido else f"{label}  ▴"
            
        st.button(display_label, key=key, use_container_width=True, on_click=nav_main, args=(label,))
        
        if label == "Game Sniper" and st.session_state.menu_expandido:
            for sub_key, sub_label, sub_icon, sub_state_key in nav_items_sub:
                st.button(sub_label, key=sub_key, use_container_width=True, on_click=nav_sub, args=(sub_label,))
        
    st.divider()
    st.caption(f"{profile['display_name']} · {'Administrador' if profile['role']=='admin' else 'Usuário'}")
    st.button('🔔 Notificações', key='nav_notifications', use_container_width=True, on_click=nav_main, args=('Notificações',))
    if profile['role'] == 'admin':
        st.button('👥 Usuários', key='nav_users', use_container_width=True, on_click=nav_main, args=('Usuários',))
    if st.button('Sair', key='sniper_logout', use_container_width=True):
        logout()
    with st.container(key="sniper_footer"):
        st.markdown('''<div class="sniper-online" role="status"><span class="sniper-online-label"><span class="sniper-online-dot" aria-hidden="true"></span><span>Crypto Sniper</span></span><span class="sniper-online-chevron" aria-hidden="true">›</span></div>''', unsafe_allow_html=True)

modulo = st.session_state.modulo_ativo
todos_jogos = []
if modulo == "Game Sniper":
    if profile['role'] != 'admin':
        st.error('O portfólio Game Sniper é exclusivo do administrador.')
        st.stop()
    if supabase is None:
        st.info("Configure SUPABASE_URL e SUPABASE_KEY para abrir o Game Sniper.")
        st.stop()
    todos_jogos = buscar_todos_jogos()

if modulo == 'Usuários':
    users_dashboard()

elif modulo == 'Notificações':
    st.title('Notificações')
    st.caption('O som e os avisos do navegador são ativados no Dex Trade. O Telegram funciona com o painel fechado.')
    from pump.telegram_ui import render_telegram_connection
    render_telegram_connection()

elif modulo == "Pump Trader":
    st.markdown("<div class='breadcrumb'>⚡ Pump Trader / <span>Em breve</span></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Pump Trader</h1><p class='sub-title'>Módulo dedicado aos lançamentos na Pump.fun (Em construção).</p>", unsafe_allow_html=True)

elif modulo == "Dex Trade":
    from pump.dashboard import render
    render()

elif modulo == "Altcoin Trader":
    st.markdown("<div class='breadcrumb'>📊 Altcoin Trader / <span>Em breve</span></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Altcoin Trader</h1><p class='sub-title'>Análise gráfica e rastreamento de altcoins em construção.</p>", unsafe_allow_html=True)

elif modulo == "Game Sniper":
    if st.session_state.pagina == "Buscar projetos":
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

        with st.expander("⚙️ Busca Manual (Palavras-chave personalizadas)"):
            c_kw, c_btn = st.columns([3, 1])
            with c_kw:
                custom_query = st.text_input("Termos de Busca", placeholder='Ex: "evermagic" OR "novo mmo nft"', label_visibility="collapsed")
            with c_btn:
                if st.button("⌖ Buscar Agora", use_container_width=True, type="primary"):
                    buscar_projetos_reais(custom_query)
                    st.rerun()

        if st.session_state.auto_sniper:
            st.markdown(f"<div class='sentinel-hud'><div class='sentinel-pulse'></div><div class='sentinel-text'>AUTO SNIPER ATIVO - PRÓXIMA VARREDURA EM: <span id='timer'>15:00</span></div></div>", unsafe_allow_html=True)
            st.markdown("<div style='display: none;'>", unsafe_allow_html=True)
            if st.button("TRIGGER_AUTOSNIPER", key="trigger_btn"):
                buscar_projetos_reais()
            st.markdown("</div>", unsafe_allow_html=True)
            
            js_timer = """
            <script>
                var timeLeft = 900;
                var timerId = setInterval(function() {
                    var m = Math.floor(timeLeft / 60);
                    var s = timeLeft % 60;
                    var display = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
                    var parentDoc = window.parent.document;
                    var timerSpan = parentDoc.getElementById('timer');
                    if(timerSpan) { timerSpan.innerHTML = display; }
                    if(timeLeft <= 0) {
                        clearInterval(timerId);
                        if(timerSpan) { timerSpan.innerHTML = "Buscando..."; }
                        var buttons = parentDoc.querySelectorAll('button');
                        buttons.forEach(function(btn) {
                            if(btn.innerText.includes('TRIGGER_AUTOSNIPER')) { btn.click(); }
                        });
                    }
                    timeLeft--;
                }, 1000);
                setTimeout(function() {
                    var parentDoc = window.parent.document;
                    var buttons = parentDoc.querySelectorAll('button');
                    buttons.forEach(function(btn) {
                        if(btn.innerText.includes('TRIGGER_AUTOSNIPER')) { btn.style.display = 'none'; }
                    });
                }, 100);
            </script>
            """
            components.html(js_timer, height=0, width=0)

        status_protegidos = ['Aguardando Lançamento', 'Lançado', 'Projetos que Entrei', 'Free to Earn']
        total_enc = len(todos_jogos)
        score_alto = len([j for j in todos_jogos if (j.get('alpha_score') or 0) >= 80])
        na_lista = len([j for j in todos_jogos if j.get('kanban_status') in status_protegidos])
        
        k1, k2, k3 = st.columns(3)
        with k1:
            st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>📄</div><div><p class='kpi-label'>Projetos encontrados</p><p class='kpi-val'>{total_enc}</p></div></div>", unsafe_allow_html=True)
        with k2:
            st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>⭐</div><div><p class='kpi-label'>Score acima de 80</p><p class='kpi-val'>{score_alto}</p></div></div>", unsafe_allow_html=True)
        with k3:
            st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>🔖</div><div><p class='kpi-label'>Na sua lista</p><p class='kpi-val'>{na_lista}</p></div></div>", unsafe_allow_html=True)

        f1, f2, f3, f4 = st.columns([3, 1.5, 1.5, 1.5])
        with f1:
            termo_busca = st.text_input("Buscar", placeholder="🔍  Buscar por nome...", label_visibility="collapsed")
        with f2:
            filtro_rede = st.selectbox("Rede", ["Todas as redes", "Solana", "Ethereum", "Ronin", "Polygon", "Immutable X", "Outra"], label_visibility="collapsed")
        with f3:
            filtro_status = st.selectbox("Status", ["Todos os status", "Não adicionados", "Na minha lista"], label_visibility="collapsed")
        with f4:
            ordem = st.selectbox("Ordem", ["↓↑ Mais recentes", "↓↑ Maior score", "↓↑ Mais visualizações"], label_visibility="collapsed")

        jogos_filtrados = todos_jogos
        if termo_busca:
            jogos_filtrados = [j for j in jogos_filtrados if termo_busca.lower() in j['nome'].lower()]
        if filtro_rede != "Todas as redes":
            jogos_filtrados = [j for j in jogos_filtrados if filtro_rede.lower() in (j.get('rede') or '').lower()]
        if filtro_status == "Não adicionados":
            jogos_filtrados = [j for j in jogos_filtrados if j.get('kanban_status') not in status_protegidos]
        elif filtro_status == "Na minha lista":
            jogos_filtrados = [j for j in jogos_filtrados if j.get('kanban_status') in status_protegidos]
        
        if "score" in ordem:
            jogos_filtrados = sorted(jogos_filtrados, key=lambda x: int(x.get('alpha_score') or 0), reverse=True)
        elif "visualizações" in ordem:
            jogos_filtrados = sorted(jogos_filtrados, key=lambda x: int(x.get('visualizacoes') or 0) if str(x.get('visualizacoes')).isdigit() else 0, reverse=True)

        st.markdown(f"<p style='font-size:13px; color:#848E9C; margin: 10px 0 15px 0;'>{len(jogos_filtrados)} projetos encontrados</p>", unsafe_allow_html=True)

        cols = st.columns(3)
        for idx, jogo in enumerate(jogos_filtrados):
            with cols[idx % 3]:
                score = jogo.get('alpha_score', 50)
                cor_score = "score-green" if score >= 80 else "score-yellow" if score >= 60 else "score-red"
                cor_barra = "progress-fill-green" if score >= 80 else "progress-fill-yellow" if score >= 60 else "progress-fill-red"
                views_raw = jogo.get('visualizacoes', '0')
                views_fmt = f"{int(views_raw):,}".replace(",", ".") if str(views_raw).isdigit() else views_raw
                icone_rede_html = obter_icone_rede(jogo.get('rede', 'Outra'))
                v_url = jogo.get('video_url', '#')
                
                card_html = (
                    f'<div class="sniper-card"><div class="card-top"><div>'
                    f'<p class="game-name">{jogo["nome"]}</p>'
                    f'<span class="badge-tba">A anunciar</span><br><div class="net-pill">{icone_rede_html}</div>'
                    f'</div><div class="score-wrapper"><div class="score-box {cor_score}">{score}</div>'
                    f'<span class="score-max">/100</span></div></div><div class="progress-bg">'
                    f'<div class="{cor_barra}" style="width: {score}%;"></div></div><div class="meta-line">'
                    f'<span>📅 Encontrado em {jogo.get("data_publicacao", "Recente")}</span><span>|</span>'
                    f'<span>👁️ {views_fmt} visualizações</span></div><div class="links-line">'
                    f'<a href="{jogo.get("twitter_url", "#")}" target="_blank">𝕏</a><span style="color:#262E3B;">|</span>'
                    f'<a href="{jogo.get("site_url", "#")}" target="_blank">🌐 Site oficial</a><span style="color:#262E3B;">|</span>'
                    f'<a href="{v_url}" target="_blank">↗ Fonte</a></div></div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                
                b_add, b_opt = st.columns([5, 1])
                ja_na_lista = jogo.get('kanban_status') in status_protegidos
                
                with b_add:
                    if ja_na_lista:
                        if st.button("✓  Adicionado", key=f"added_{jogo['id']}", use_container_width=True):
                            atualizar_status_kanban(jogo['id'], 'Radar')
                            st.rerun()
                    else:
                        if st.button("＋  Adicionar à lista", key=f"add_{jogo['id']}", use_container_width=True):
                            atualizar_status_kanban(jogo['id'], 'Aguardando Lançamento')
                            st.rerun()
                with b_opt:
                    st.markdown('<div class="btn-deletar-x">', unsafe_allow_html=True)
                    if st.button("✖", key=f"del_{jogo['id']}", use_container_width=True, help="Deletar projeto"):
                        apagar_jogo(jogo['id'])
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    elif st.session_state.pagina == "Kanban":
        col_k1, col_k2, col_k3 = st.columns([3.2, 1, 1])
        with col_k1:
            st.markdown("<div class='breadcrumb'>🎮 Game Sniper / <span>Kanban</span></div>", unsafe_allow_html=True)
            st.markdown("<h1 class='main-title'>Seu portfólio de projetos</h1><p class='sub-title'>Acompanhe e gerencie as suas posições e radares.</p>", unsafe_allow_html=True)
        with col_k2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🧭  Explorar projetos", use_container_width=True):
                st.session_state.pagina = "Buscar projetos"
                st.rerun()
        with col_k3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("＋  Adicionar projeto", type="primary", use_container_width=True):
                st.session_state.mostrar_form_manual = not st.session_state.mostrar_form_manual

        if st.session_state.mostrar_form_manual:
            with st.container():
                st.markdown("<div style='background:#12161C; border:1px solid #00E6A8; border-radius:10px; padding:15px; margin-bottom:20px;'>", unsafe_allow_html=True)
                with st.form("form_novo_kanban"):
                    st.subheader("➕ Novo Projeto no Kanban")
                    c1, c2 = st.columns(2)
                    m_nome = c1.text_input("Nome do Jogo")
                    m_rede = c2.selectbox("Rede", ["Solana", "Ethereum", "Ronin", "Immutable X", "Polygon", "Avalanche", "Outra"])
                    c3, c4, c5 = st.columns(3)
                    m_site = c3.text_input("Link do Site Oficial")
                    m_tw = c4.text_input("Link do X / Twitter")
                    m_etapa = c5.selectbox("Etapa Inicial", ["Aguardando Lançamento", "Lançado", "Projetos que Entrei", "Free to Earn"])
                    
                    if st.form_submit_button("Salvar Projeto", type="primary"):
                        if m_nome:
                            inserir_projeto_manual(m_nome, m_rede, m_site, m_tw, m_etapa)
                            st.session_state.mostrar_form_manual = False
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        jogos_ag = [j for j in todos_jogos if j.get('kanban_status') == 'Aguardando Lançamento']
        jogos_lanc = [j for j in todos_jogos if j.get('kanban_status') == 'Lançado']
        jogos_en = [j for j in todos_jogos if j.get('kanban_status') == 'Projetos que Entrei']
        jogos_fr = [j for j in todos_jogos if j.get('kanban_status') == 'Free to Earn']

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>⏳</div><div><p class='kpi-label'>Aguardando</p><p class='kpi-val'>{len(jogos_ag)}</p></div></div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>🚀</div><div><p class='kpi-label'>Lançados</p><p class='kpi-val'>{len(jogos_lanc)}</p></div></div>", unsafe_allow_html=True)
        with m3:
            st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>💼</div><div><p class='kpi-label'>Que Entrei</p><p class='kpi-val'>{len(jogos_en)}</p></div></div>", unsafe_allow_html=True)
        with m4:
            st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>🎮</div><div><p class='kpi-label'>Free to Earn</p><p class='kpi-val'>{len(jogos_fr)}</p></div></div>", unsafe_allow_html=True)

        kf1, kf2, kf3 = st.columns([3.5, 1.5, 1])
        with kf1:
            k_busca = st.text_input("Buscar na lista", placeholder="🔍  Buscar no Kanban...", label_visibility="collapsed")
        with kf2:
            k_rede = st.selectbox("Rede Kanban", ["Todas as redes", "Solana", "Ethereum", "Ronin", "Polygon", "Immutable X", "Outra"], label_visibility="collapsed")
        with kf3:
            modo_vis = st.selectbox("Visão", ["⊞ Quadro", "☰ Lista"], label_visibility="collapsed")

        if k_busca:
            jogos_ag = [j for j in jogos_ag if k_busca.lower() in j['nome'].lower()]
            jogos_lanc = [j for j in jogos_lanc if k_busca.lower() in j['nome'].lower()]
            jogos_en = [j for j in jogos_en if k_busca.lower() in j['nome'].lower()]
            jogos_fr = [j for j in jogos_fr if k_busca.lower() in j['nome'].lower()]
        if k_rede != "Todas as redes":
            jogos_ag = [j for j in jogos_ag if k_rede.lower() in (j.get('rede') or '').lower()]
            jogos_lanc = [j for j in jogos_lanc if k_rede.lower() in (j.get('rede') or '').lower()]
            jogos_en = [j for j in jogos_en if k_rede.lower() in (j.get('rede') or '').lower()]
            jogos_fr = [j for j in jogos_fr if k_rede.lower() in (j.get('rede') or '').lower()]

        st.markdown("<br>", unsafe_allow_html=True)

        def desenhar_card_kanban(jogo, status_atual):
            score = jogo.get('alpha_score', 50)
            cor_score = "score-green" if score >= 80 else "score-yellow" if score >= 60 else "score-red"
            icone_rede = obter_icone_rede(jogo.get('rede', 'Outra'))
            
            dt_txt = jogo.get('data_lancamento') or "Data a confirmar"
            if status_atual != 'Aguardando Lançamento' and jogo.get('data_lancamento'): 
                dt_txt = f"Lançado: {jogo['data_lancamento']}"
                
            nota_txt = jogo.get('anotacoes') or "Adicionar uma anotação..."
            link_acao = f"<a href='{jogo.get('site_url', '#')}' target='_blank' class='k-action-link'>Acessar ↗</a>"
            
            iso_date = data_pt_para_iso(jogo.get('data_lancamento', ''))
            countdown_html = ""
            if status_atual == 'Aguardando Lançamento' and iso_date:
                countdown_html = f"<div class='k-countdown' data-target='{iso_date}'>⏳ Calculando...</div>"

            k_html = (
                f'<div class="k-card"><div class="card-top"><div style="display:flex; gap:10px; align-items:center;">'
                f'<span style="color:#474D57; font-size:16px;">⠿</span><div>'
                f'<p class="game-name" style="font-size:14px; margin-bottom:4px;">{jogo["nome"]}</p>'
                f'<div class="net-pill">{icone_rede}</div></div></div><div class="score-box {cor_score}" '
                f'style="font-size:12px; padding:4px 8px;">{score}</div></div><div class="k-info-line">'
                f'<span>📅 {dt_txt}</span></div>{countdown_html}<div class="k-note-line" '
                f'style="margin-top:12px; padding-top:8px; border-top:1px solid #1E242D;">'
                f'<span>📝 {nota_txt[:28]}</span>{link_acao}</div></div>'
            )
            st.markdown(k_html, unsafe_allow_html=True)
            
            with st.popover("⚙️ Gerenciar Card", use_container_width=True):
                st.markdown(f"**{jogo['nome']}**")
                todas_etapas = ["Aguardando Lançamento", "Lançado", "Projetos que Entrei", "Free to Earn"]
                idx_atual = todas_etapas.index(status_atual) if status_atual in todas_etapas else 0
                nova_etapa = st.selectbox("Mover para:", todas_etapas, index=idx_atual, key=f"mv_{jogo['id']}")
                if nova_etapa != status_atual:
                    atualizar_status_kanban(jogo['id'], nova_etapa)
                    st.rerun()
                    
                nova_data = st.date_input("Data", key=f"dt_{jogo['id']}")
                nova_nota = st.text_input("Anotação", value=jogo.get('anotacoes') or "", key=f"nt_{jogo['id']}")
                
                if st.button("💾 Salvar Detalhes", key=f"sv_{jogo['id']}", type="primary", use_container_width=True):
                    meses_pt = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
                    dt_formatada = f"{nova_data.day} {meses_pt[nova_data.month-1]} {nova_data.year}"
                    salvar_detalhes_kanban(jogo['id'], dt_formatada, nova_nota)
                    st.rerun()
                st.divider()
                if st.button("❌ Remover do Kanban", key=f"rm_{jogo['id']}", use_container_width=True):
                    atualizar_status_kanban(jogo['id'], 'Radar')
                    st.rerun()
            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        col_ag, col_la, col_en, col_fr = st.columns(4)
        with col_ag:
            st.markdown(f"<div class='kanban-header'><p class='kanban-header-title' style='color:#FCD535;'>🟡 Aguardando <span class='count-pill'>{len(jogos_ag)}</span></p></div>", unsafe_allow_html=True)
            for j in jogos_ag:
                desenhar_card_kanban(j, 'Aguardando Lançamento')

        with col_la:
            st.markdown(f"<div class='kanban-header'><p class='kanban-header-title' style='color:#00E6A8;'>🟢 Lançados <span class='count-pill'>{len(jogos_lanc)}</span></p></div>", unsafe_allow_html=True)
            for j in jogos_lanc:
                desenhar_card_kanban(j, 'Lançado')

        with col_en:
            st.markdown(f"<div class='kanban-header'><p class='kanban-header-title' style='color:#9B51E0;'>🟣 Que Entrei <span class='count-pill'>{len(jogos_en)}</span></p></div>", unsafe_allow_html=True)
            for j in jogos_en:
                desenhar_card_kanban(j, 'Projetos que Entrei')

        with col_fr:
            st.markdown(f"<div class='kanban-header'><p class='kanban-header-title' style='color:#2D9CDB;'>🔵 Free to Earn <span class='count-pill'>{len(jogos_fr)}</span></p></div>", unsafe_allow_html=True)
            for j in jogos_fr:
                desenhar_card_kanban(j, 'Free to Earn')

        js_kanban = """
        <script>
            function updateTimers() {
                var parent = window.parent.document;
                var timers = parent.querySelectorAll('.k-countdown');
                var now = new Date().getTime();
                timers.forEach(function(t) {
                    var targetStr = t.getAttribute('data-target');
                    if(!targetStr) return;
                    var target = new Date(targetStr).getTime();
                    var diff = target - now;
                    if(diff <= 0) {
                        t.innerHTML = "🚀 CHEGOU A HORA!";
                        t.style.borderColor = "#FCD535";
                        t.style.color = "#FCD535";
                        return;
                    }
                    var d = Math.floor(diff / (1000 * 60 * 60 * 24));
                    var h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    var m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                    var s = Math.floor((diff % (1000 * 60)) / 1000);
                    
                    var out = "⏳ ";
                    if (d > 0) out += d + "d ";
                    out += (h < 10 ? "0"+h : h) + "h " + (m < 10 ? "0"+m : m) + "m " + (s < 10 ? "0"+s : s) + "s";
                    t.innerHTML = out;
                });
            }
            setInterval(updateTimers, 1000);
            updateTimers();
        </script>
        """
        components.html(js_kanban, height=0, width=0)

