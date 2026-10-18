import streamlit as st
from supabase import create_client, Client
import requests
import re
from datetime import datetime, timedelta, timezone

# --- Configuração da Página ---
st.set_page_config(page_title="Crypto Sniper", layout="wide", initial_sidebar_state="expanded")

# --- Conexão Segura com Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- Controle de Estado de Navegação ---
if 'pagina' not in st.session_state:
    st.session_state.pagina = "Buscar projetos"
if 'mostrar_form_manual' not in st.session_state:
    st.session_state.mostrar_form_manual = False

# --- Estilização CSS (Tema Dark & Teal SaaS + Menu Lateral Customizado) ---
css = """
<style>
/* Fundo Geral e Sidebar */
.stApp { background-color: #0B0E11; color: #EAECEF; }
[data-testid="stSidebar"] { background-color: #080A0C; border-right: 1px solid #14181F; }
.block-container { padding-top: 1.8rem !important; max-width: 96% !important; }

/* =========================================================
   ESTILOS GERAIS DOS CARDS E BOTÕES
   ========================================================= */
.breadcrumb { font-size: 13px; color: #848E9C; margin-bottom: 15px; font-weight: 500; }
.breadcrumb span { color: #00E6A8; font-weight: 600; }
.main-title { font-size: 32px; font-weight: 800; color: #FFFFFF; margin: 0 0 4px 0; letter-spacing: -0.5px; }
.sub-title { font-size: 15px; color: #848E9C; margin-bottom: 24px; }

.kpi-card { background-color: #12161C; border: 1px solid #1E242D; border-radius: 12px; padding: 18px 20px; display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.kpi-icon { width: 46px; height: 46px; border-radius: 10px; background-color: #192028; display: flex; align-items: center; justify-content: center; font-size: 20px; border: 1px solid #252E3A; }
.kpi-label { font-size: 13px; color: #848E9C; margin: 0 0 2px 0; }
.kpi-val { font-size: 26px; font-weight: 800; color: #FFFFFF; margin: 0; line-height: 1.1; }

.sniper-card { background-color: #12161C; border: 1px solid #1E242D; border-radius: 12px; padding: 18px; margin-bottom: 8px; transition: border-color 0.2s; }
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

.kanban-header { background-color: #12161C; border: 1px solid #1E242D; border-radius: 10px; padding: 12px 16px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }
.kanban-header-title { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px; margin: 0; }
.count-pill { background-color: #1E242D; color: #848E9C; font-size: 12px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }

.k-card { background-color: #12161C; border: 1px solid #1E242D; border-radius: 10px; padding: 16px; margin-bottom: 6px; }
.k-info-line { font-size: 12px; color: #848E9C; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; }
.k-note-line { font-size: 12px; color: #6C7582; margin-top: 6px; display: flex; justify-content: space-between; align-items: center; font-style: italic; }
.k-action-link { color: #00E6A8 !important; text-decoration: none; font-weight: 600; font-size: 12px; }

div.stButton > button { background-color: #161B22; color: #EAECEF; border: 1px solid #262E3B; border-radius: 8px; font-weight: 600; font-size: 13px; padding: 0.45rem 1rem; transition: all 0.2s; }
div.stButton > button:hover { border-color: #00E6A8; color: #00E6A8; background-color: #121D1B; }
div.stButton > button[kind="primary"] { background-color: #00E6A8 !important; color: #06110E !important; border: none !important; font-weight: 700 !important; }
div.stButton > button[kind="primary"]:hover { background-color: #00C892 !important; box-shadow: 0 0 15px rgba(0, 230, 168, 0.35); }
[data-testid="stPopover"] > button { background: transparent !important; border: 1px solid #1E242D !important; color: #848E9C !important; padding: 2px 10px !important; min-height: 32px !important; }
[data-testid="stPopover"] > button:hover { border-color: #00E6A8 !important; color: #FFF !important; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- Ícones Oficiais das Redes (HTML) ---
def obter_icone_rede(rede):
    r = (rede or "").lower()
    if "solana" in r:
        return '<img src="https://cryptologos.cc/logos/solana-sol-logo.png?v=029" width="14" style="vertical-align:middle;"> Solana'
    elif "ethereum" in r:
        return '<img src="https://cryptologos.cc/logos/ethereum-eth-logo.png?v=029" width="14" style="vertical-align:middle;"> Ethereum'
    elif "polygon" in r:
