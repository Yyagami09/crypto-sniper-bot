# Crypto Sniper

Painel Streamlit com Game Sniper e radar GMGN no módulo Pump Trader.

O radar roda em uma função agendada no Supabase, independente da sessão do navegador. Para concluir a ativação com sua própria chave de consulta e notificações opcionais, siga [ATIVAR_RADAR.md](ATIVAR_RADAR.md).

Triagem por critérios experimentais, com registro de origem, horário e informações ausentes. Não executa negociações.

## Desenvolvimento

Use Python 3.12, instale `requirements-dev.txt` e execute:

```bash
python -m pytest -q
node --test tests/core.test.mjs
streamlit run app.py
```

O teste TypeScript usa Node.js 24. A demonstração no Pump Trader é identificada e usa dados fictícios isolados do banco real.
