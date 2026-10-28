# Crypto Sniper

Painel Streamlit com Game Sniper e radar gratuito de mercado no módulo Dex Sniper.

O radar usa DEX Screener, GeckoTerminal e RPC público da Solana. Roda a cada minuto no Supabase, independente do navegador. Não requer depósito, carteira ou chave GMGN. Veja funcionamento e Telegram opcional em [RADAR_GRATUITO.md](RADAR_GRATUITO.md).

Triagem por critérios experimentais, com registro de origem, horário e informações ausentes. Não executa negociações.

A camada `risk-v1` retém sinais por risco de LP/concentração/atividade atípica. Inclui indicadores complementares de grandes detentores e indícios de retirada gradual de liquidez. Limites e cobertura em [RISCO_E_CARTEIRAS.md](RISCO_E_CARTEIRAS.md).

Login por convite via Supabase Auth, administração de usuários e notificações pessoais: [ACESSO_E_ALERTAS.md](ACESSO_E_ALERTAS.md). Senhas e conexões não são versionadas. Contas comuns acessam o radar; Game Sniper e administração são exclusivos do admin.

## Desenvolvimento

Use Python 3.12, instale `requirements-dev.txt` e execute:

```bash
python -m pytest -q
node --test tests/core.test.mjs tests/free-core.test.mjs tests/notifications.test.mjs tests/risk-whales.test.mjs tests/networks.test.mjs tests/early.test.mjs tests/manual.test.mjs
streamlit run app.py
```

O teste TypeScript usa Node.js 24. A demonstração no Dex Sniper é identificada e usa dados fictícios isolados do banco real. Para executar localmente, configure Supabase e entre com uma conta criada pelo administrador.

O seletor de redes do Dex Sniper inclui Robinhood Chain e outras sete redes além da Solana. Fora da Solana, o modo é de observação de mercado, sem confirmação ou alertas automáticos até adaptação dos verificadores de risco. Veja as diferenças em [RADAR_GRATUITO.md](RADAR_GRATUITO.md#redes-no-dex-sniper).

Teste de descoberta antecipada: veja [EXPERIMENTO_ANTECIPADO.md](EXPERIMENTO_ANTECIPADO.md). A escolha de modo é por conta; Clássico mantém as regras anteriores.

Consulta sob demanda em **Dex Sniper → Analisar contrato**: contrato ou link de par, foco em análise geral, riscos ou possível reentrada. Veja [ANALISE_PONTUAL.md](ANALISE_PONTUAL.md).
