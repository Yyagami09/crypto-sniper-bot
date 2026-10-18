            ja_na_lista = jogo.get('kanban_status') in ['Aguardando Lançamento', 'Lançado']
            
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
                with st.popover("•••", use_container_width=True):
                    st.markdown(f"**{jogo['nome']}**")
                    if st.button("🗑️ Deletar projeto", key=f"del_{jogo['id']}", use_container_width=True):
                        apagar_jogo(jogo['id'])
                        st.rerun()
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

# ==========================================
# TELA 2: GAME SNIPER -> KANBAN
# ==========================================
elif st.session_state.pagina == "Kanban":
    col_k1, col_k2, col_k3 = st.columns([3.2, 1, 1])
    with col_k1:
        st.markdown("<div class='breadcrumb'>🎮 Game Sniper / <span>Kanban</span></div>", unsafe_allow_html=True)
        st.markdown("<h1 class='main-title'>Seu radar de projetos</h1><p class='sub-title'>Organize os jogos que você quer acompanhar.</p>", unsafe_allow_html=True)
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
                st.subheader("➕ Novo Projeto no Radar")
                c1, c2 = st.columns(2)
                m_nome = c1.text_input("Nome do Jogo")
                m_rede = c2.selectbox("Rede", ["Solana", "Ethereum", "Ronin", "Immutable X", "Polygon", "Avalanche", "Outra"])
                c3, c4, c5 = st.columns(3)
                m_site = c3.text_input("Link do Site Oficial")
                m_tw = c4.text_input("Link do X / Twitter")
                m_etapa = c5.selectbox("Etapa Inicial", ["Aguardando Lançamento", "Lançado"])
                
                if st.form_submit_button("Salvar Projeto", type="primary"):
                    if m_nome:
                        inserir_projeto_manual(m_nome, m_rede, m_site, m_tw, m_etapa)
                        st.session_state.mostrar_form_manual = False
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    jogos_ag = [j for j in todos_jogos if j.get('kanban_status') == 'Aguardando Lançamento']
    jogos_lanc = [j for j in todos_jogos if j.get('kanban_status') == 'Lançado']
    total_acomp = len(jogos_ag) + len(jogos_lanc)

    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>🔖</div><div><p class='kpi-label'>Acompanhando</p><p class='kpi-val'>{total_acomp}</p></div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>⏳</div><div><p class='kpi-label'>Aguardando lançamento</p><p class='kpi-val'>{len(jogos_ag)}</p></div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='kpi-card'><div class='kpi-icon'>🚀</div><div><p class='kpi-label'>Lançados</p><p class='kpi-val'>{len(jogos_lanc)}</p></div></div>", unsafe_allow_html=True)

    kf1, kf2, kf3 = st.columns([3.5, 1.5, 1])
    with kf1: k_busca = st.text_input("Buscar na lista", placeholder="🔍  Buscar na sua lista...", label_visibility="collapsed")
    with kf2: k_rede = st.selectbox("Rede Kanban", ["Todas as redes", "Solana", "Ethereum", "Ronin", "Polygon", "Immutable X", "Outra"], label_visibility="collapsed")
    with kf3: modo_vis = st.selectbox("Visão", ["⊞ Quadro", "☰ Lista"], label_visibility="collapsed")

    if k_busca:
        jogos_ag = [j for j in jogos_ag if k_busca.lower() in j['nome'].lower()]
        jogos_lanc = [j for j in jogos_lanc if k_busca.lower() in j['nome'].lower()]
    if k_rede != "Todas as redes":
        jogos_ag = [j for j in jogos_ag if k_rede.lower() in (j.get('rede') or '').lower()]
        jogos_lanc = [j for j in jogos_lanc if k_rede.lower() in (j.get('rede') or '').lower()]

    st.markdown("<br>", unsafe_allow_html=True)

    def desenhar_card_kanban(jogo, lancado=False):
        score = jogo.get('alpha_score', 50)
        cor_score = "score-green" if score >= 80 else "score-yellow" if score >= 60 else "score-red"
        icone_rede = obter_icone_rede(jogo.get('rede', 'Outra'))
        
        dt_txt = jogo.get('data_lancamento') or ("Lançado recentemente" if lancado else "Lançamento a confirmar")
        if lancado and jogo.get('data_lancamento'): dt_txt = f"Lançado em {jogo['data_lancamento']}"
        
        nota_txt = jogo.get('anotacoes') or ("Revisar novidades do projeto" if lancado else "Adicionar uma anotação...")
        link_acao = f"<a href='{jogo.get('site_url', '#')}' target='_blank' class='k-action-link'>{'Acessar jogo ↗' if lancado else 'Ver projeto →'}</a>"
        
        k_html = f"""<div class="k-card"><div class="card-top"><div style="display:flex; gap:10px; align-items:center;"><span style="color:#474D57; font-size:16px;">⠿</span><div><p class="game-name" style="font-size:16px; margin-bottom:4px;">{jogo['nome']}</p><div class="net-pill">{icone_rede}</div></div></div><div class="score-box {cor_score}" style="font-size:14px; padding:4px 8px;">{score}</div></div><div class="k-info-line"><span>📅 {dt_txt}</span><span>{'' if lancado else '➕ Definir data'}</span></div><div class="k-note-line"><span>📝 {nota_txt[:38]}</span>{link_acao}</div></div>"""
        st.markdown(k_html, unsafe_allow_html=True)
        
        c_act1, c_act2 = st.columns([4, 1])
        with c_act1:
            if not lancado:
                if st.button("🚀 Marcar como Lançado", key=f"to_l_{jogo['id']}", use_container_width=True):
                    atualizar_status_kanban(jogo['id'], 'Lançado')
                    st.rerun()
            else:
                if st.button("⏳ Voltar para Aguardando", key=f"to_a_{jogo['id']}", use_container_width=True):
                    atualizar_status_kanban(jogo['id'], 'Aguardando Lançamento')
                    st.rerun()
        with c_act2:
            with st.popover("•••", use_container_width=True):
                st.markdown(f"**Editar {jogo['nome']}**")
                nova_data = st.date_input("Data de Lançamento", key=f"dt_{jogo['id']}")
                nova_nota = st.text_input("Anotação", value=jogo.get('anotacoes') or "", key=f"nt_{jogo['id']}")
                if st.button("💾 Salvar", key=f"sv_{jogo['id']}", type="primary", use_container_width=True):
                    meses_pt = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
                    dt_formatada = f"{nova_data.day} {meses_pt[nova_data.month-1]} {nova_data.year}"
                    salvar_detalhes_kanban(jogo['id'], dt_formatada, nova_nota)
                    st.rerun()
                st.divider()
                if st.button("❌ Remover do Kanban", key=f"rm_{jogo['id']}", use_container_width=True):
                    atualizar_status_kanban(jogo['id'], 'Radar')
                    st.rerun()
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

    col_esq, col_dir = st.columns(2)
    with col_esq:
        st.markdown(f"<div class='kanban-header'><p class='kanban-header-title' style='color:#FCD535;'>🟡 Aguardando lançamento <span class='count-pill'>{len(jogos_ag)}</span></p></div>", unsafe_allow_html=True)
        for j in jogos_ag: desenhar_card_kanban(j, lancado=False)

    with col_dir:
        st.markdown(f"<div class='kanban-header'><p class='kanban-header-title' style='color:#00E6A8;'>🟢 Projetos lançados <span class='count-pill'>{len(jogos_lanc)}</span></p></div>", unsafe_allow_html=True)
        for j in jogos_lanc: desenhar_card_kanban(j, lancado=True)
