# Crypto Sniper

Painel Streamlit com Game Sniper e radar gratuito de mercado no módulo Dex Trade.

O radar usa DEX Screener, GeckoTerminal e RPC público da Solana. Roda a cada cinco minutos no Supabase, independente do navegador. Não requer depósito, carteira ou chave GMGN. Veja funcionamento e Telegram opcional em [RADAR_GRATUITO.md](RADAR_GRATUITO.md).

Triagem por critérios experimentais, com registro de origem, horário e informações ausentes. Não executa negociações.

Login por convite via Supabase Auth, administração de usuários e notificações pessoais: [ACESSO_E_ALERTAS.md](ACESSO_E_ALERTAS.md). Senhas e conexões não são versionadas. Contas comuns acessam o radar; Game Sniper e administração são exclusivos do admin.

## Desenvolvimento

Use Python 3.12, instale `requirements-dev.txt` e execute:

```bash
python -m pytest -q
node --test tests/core.test.mjs tests/free-core.test.mjs tests/notifications.test.mjs
streamlit run app.py
```

O teste TypeScript usa Node.js 24. A demonstração no Dex Trade é identificada e usa dados fictícios isolados do banco real. Para executar localmente, configure Supabase e entre com uma conta criada pelo administrador.
