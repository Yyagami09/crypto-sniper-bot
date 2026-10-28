# Ativar o radar GMGN

> **LEGADO — desativado nesta instalação.** O radar agora funciona sem depósito ou chave GMGN. Siga [RADAR_GRATUITO.md](RADAR_GRATUITO.md). As instruções abaixo são apenas referência da versão anterior.

O painel continua no Streamlit. A função `pump-radar` e o agendamento `pump-radar-every-minute` ficam no Supabase. Nenhuma VPS é necessária para esta versão.

## Configuração indispensável

1. Crie sua API Key **somente consulta** na GMGN: https://gmgn.ai/ai.
2. No projeto Supabase, abra **Vault** e crie um segredo chamado exatamente **gmgn_api_key**, com sua API Key como valor. Não inclua aspas no valor. O próximo ciclo de um minuto já tentará consultar os dados. Não use a chave pública de teste em produção.
3. Abra **Pump Trader** no Streamlit. Se aparecer uma mensagem de permissão de leitura, em **Manage app → Settings → Secrets** acrescente `PUMP_SUPABASE_KEY` com a chave legacy `service_role` (JWT) do mesmo projeto. Preserve as entradas atuais, incluindo YouTube. Se a entrada `SUPABASE_KEY` já for uma chave de servidor com essa permissão, ela será reutilizada.

Essa chave do Supabase fica no servidor Streamlit. Nunca a coloque no GitHub, no navegador ou em mensagens. O adaptador Python atual espera uma chave legacy JWT, não `sb_secret_...`.

O projeto: https://supabase.com/dashboard/project/qcetrltyhmtrgtijuiri

O painel: https://crypto-sniper-bot-usqhaaoh9qf5fseenn2dj6.streamlit.app/

Nenhuma frase de recuperação, chave privada de carteira ou permissão de negociação é necessária.

## Telegram opcional

No Vault do mesmo projeto, acrescente:

| Nome | Valor |
|---|---|
| `pump_telegram_bot_token` | Token do seu bot pessoal |
| `pump_telegram_chat_id` | ID da sua conversa privada com o bot |

Abra o bot no Telegram e envie `/start`. O envio será ativado no próximo ciclo. Sem esses segredos, os alertas ficam somente no painel. Nunca configure um destinatário de terceiros sem autorização.

## Funcionamento

- Descoberta: lista de moedas recém-migradas e Trending de cinco minutos da GMGN.
- Ciclo a cada minuto, até seis moedas por execução e 30 em acompanhamento, sem sobrepor varreduras.
- Limite de duração: o ciclo encerra a seleção antecipadamente se necessário. Cada moeda pode levar vários minutos para ser reavaliada.
- Confirmação em duas consultas, alertas com cooldown de 30 minutos por moeda/tipo e no máximo 30 observações por moeda.
- Consulta de segurança complementada por indicadores recentes de mercado; dados ausentes não viram zero.
- Alertas de candidata aos critérios, perda das condições e lacuna de consulta. Não são ordens nem acompanhamento de uma posição sua.
- Critérios experimentais. Esta versão não contém análise de narrativa por IA, execução de ordens, backtest ou promessa de retorno.
- Se ocorrer limite/autenticação da API, o radar pausa por dez minutos. Confira o status no painel; indisponibilidade total não tem um canal independente de notificação nesta versão.
- As janelas de volume podem se sobrepor. Duas consultas não são duas evidências estatísticas independentes.
- O horário registrado é o da consulta, não garantia de atualização do dado na origem.

## Proteção e manutenção

A tabela `pump_radar_state` só admite acesso de servidor. A autenticação entre Cron e Edge Function usa um segredo interno gerado no Vault (`pump_cron_token`), independente de suas chaves GMGN. A função valida esse segredo; o JWT do gateway está desativado porque a função possui autenticação própria.

As tabelas do Game Sniper não foram alteradas. O app original não tem autenticação de usuários para um SaaS público; mantenha o acesso do Streamlit restrito conforme o uso pretendido.

Para pausar varreduras, desative `pump-radar-every-minute` na área Cron do Supabase. O código em `pump/worker.py` é a alternativa Python para hospedagem própria; **não o inicie simultaneamente** com o Cron nesta instalação.

Os arquivos SQL versionam a infraestrutura. Não os execute novamente sem conferir as migrações existentes. Atualizações da Edge Function devem continuar usando o código de `supabase/functions/pump-radar/` e manter a validação do segredo interno.

Testes locais: `python -m pytest -q` e `node --test tests/core.test.mjs` (Node.js 24).
