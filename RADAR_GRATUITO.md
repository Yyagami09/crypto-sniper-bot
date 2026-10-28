# Radar gratuito — já ativado

O Dex Trade usa **DEX Screener + GeckoTerminal + RPC público da Solana**. Não requer API Key de mercado, carteira, depósito ou saldo mínimo. A coleta GMGN está desativada nesta instalação.

O painel continua no Streamlit e a coleta roda no Supabase a cada **5 minutos**, mesmo com a aba fechada. Nenhuma nova assinatura foi contratada. O funcionamento depende das cotas gratuitas e disponibilidade dos provedores, que podem mudar ou limitar respostas.

## O que funciona

- Descobre uma amostra de pools novas no GeckoTerminal e perfis recentes do DEX Screener. Perfis podem ser promocionais e não significam lançamentos novos.
- Mantém até 30 tokens e consulta suas pools em lote.
- Exibe preço, volume de 5 minutos, liquidez, contagem de compras/vendas, variação e idade da pool.
- Identifica FDV separadamente de market cap quando só a primeira avaliação está disponível.
- Consulta na Solana as permissões de emissão e congelamento. Programa ou extensões não reconhecidas ficam pendentes.
- Registra **sinais de mercado com risco parcial** após duas consultas dentro dos critérios, espaçadas por pelo menos quatro minutos.
- Registra perda das condições e lacunas de dados. Não compra ou vende tokens.
- Compara preços observados após 15 minutos e uma hora, quando há nova consulta da mesma pool na janela prevista. Isso não representa lucro de execução.

## Cobertura parcial de risco

Concentração por carteira, insiders, bundles, volume artificial e retirada de liquidez não são auditados. Não há nota de segurança ou probabilidade de lucro. A relação de compras/vendas usa **quantidade de transações**, não valores financeiros comprados e vendidos.

Duas consultas não são evidências estatísticas independentes. O horário mostrado é o da consulta, não garantia de atualização na origem. A descoberta não cobre todo o mercado. O RPC público é compartilhado, tem limites e não tem garantia de disponibilidade.

Os critérios são experimentais. O sistema ainda não demonstrou rentabilidade e deve ser validado em modo de observação antes de qualquer uso de dinheiro real. As variações de preço não incluem taxas, slippage, impacto de ordem ou possibilidade de venda.

## Painel sem nova credencial

O painel reutiliza **SUPABASE_URL e SUPABASE_KEY** já existentes. Não precisa adicionar `PUMP_SUPABASE_KEY` nem chave administrativa.

A tabela `pump_market_feed` contém somente o **feed compartilhado de dados e sinais públicos de mercado** e exige uma conta ativa para leitura nesta instalação. Carteiras pessoais, notas privadas, configurações, segredos e detalhes de entrega não fazem parte desse feed. Só o servidor escreve. `pump_radar_state` e Vault continuam protegidos. O código filtra explicitamente os campos publicados e não publica histórico privado antigo.

Painel: https://crypto-sniper-bot-usqhaaoh9qf5fseenn2dj6.streamlit.app/

## Telegram gratuito e opcional

Entre no painel e abra **Notificações**. O assistente orienta a criar um bot gratuito no BotFather, colar a chave em um campo protegido, abrir o link e tocar em Iniciar. O ID da conversa é identificado automaticamente. A conexão fica vinculada ao usuário e a chave é criptografada no Vault. Não precisa informar telefone, senha do Telegram ou código de login. Há botões para teste e desconexão.

Não exige SOL. Sem configurar Telegram, os alertas continuam no painel. O envio automático só inclui eventos criados depois da conexão, expira após 30 minutos e faz até três tentativas. Uma falha entre envio e gravação pode duplicar uma mensagem. Não publique credenciais no GitHub ou no chat. A configuração global legada do Vault continua compatível, mas não é usada pelo assistente pessoal.

No **Dex Trade**, use **Ativar e testar som** e, se desejar, **Ativar notificações do navegador**. São opções desta página, dependem das permissões do navegador/Windows e podem parar se a aba for suspensa ou fechada. O primeiro carregamento não dispara alertas antigos. Para avisos com o painel fechado, use Telegram. Veja [ACESSO_E_ALERTAS.md](ACESSO_E_ALERTAS.md).

## Operação

O job conserva o nome legado `pump-radar-every-minute`, mas a expressão atual é `*/5 * * * *`: roda a cada cinco minutos. Chama a função `pump-radar` com autenticação interna gerada no Vault. O gateway JWT fica desativado porque a função valida seu próprio segredo de máquina.

Uma execução não se sobrepõe à outra. Mantém até 60 observações por token e até 400 alertas internos; o feed mostra os últimos 100. Mudança da pool principal reinicia a confirmação. Para pausar, desative o job na área Cron do Supabase. Não rode o worker Python legado simultaneamente.

O Game Sniper e seus registros foram preservados como espaço exclusivo do administrador. Contas comuns não têm acesso a esse portfólio. O radar é compartilhado e as conexões do Telegram são pessoais.

## Código e testes

Perfil ativo: `supabase/functions/pump-radar/free-core.ts`; coletor: `index.ts`. `core.ts` mantém utilitários e perfil GMGN legado, que não coleta dados nesta instalação. O processo Python legado não está ativado.

Infraestrutura versionada: `supabase_pump.sql`, `supabase_runtime.sql`, `free_market.sql` e `users_notifications.sql`. Não reaplique sem conferir as migrações existentes. Limites ficam em `freeRules`, exigindo novo deploy quando alterados.

```bash
python -m pytest -q
node --test tests/core.test.mjs tests/free-core.test.mjs tests/notifications.test.mjs
```

Fontes oficiais:

- https://docs.dexscreener.com/api/reference
- https://docs.dexscreener.com/
- https://support.coingecko.com/articles/6867086195-does-geckoterminal-have-an-api
- https://solana.com/docs/rpc/http/getmultipleaccounts
- https://solana.com/docs/references/clusters
