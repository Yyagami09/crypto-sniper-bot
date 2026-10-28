# Radar gratuito — já ativado

O Dex Trade usa **DEX Screener + GeckoTerminal + RPC público da Solana**. Não requer API Key de mercado, carteira, depósito ou saldo mínimo. A coleta GMGN está desativada nesta instalação.

A versão atual também consulta relatórios públicos RugCheck e saldos de uma amostra de grandes detentores. Risco, limitações, cache e indícios de slow rug estão documentados em [RISCO_E_CARTEIRAS.md](RISCO_E_CARTEIRAS.md). A camada de risco é obrigatória para novas confirmações; o indicador de carteiras é complementar.

O painel continua no Streamlit e a coleta roda no Supabase a cada **1 minuto**, mesmo com a aba fechada. Nenhuma nova assinatura foi contratada. O funcionamento depende das cotas gratuitas e disponibilidade dos provedores, que podem mudar ou limitar respostas.

## O que funciona

- Descobre uma amostra de pools novas no GeckoTerminal e perfis recentes do DEX Screener. Perfis podem ser promocionais e não significam lançamentos novos.
- Mantém até 30 tokens e consulta suas pools em lote.
- Exibe preço, volume de 5 minutos, liquidez, contagem de compras/vendas, variação e idade da pool.
- Identifica FDV separadamente de market cap quando só a primeira avaliação está disponível.
- Consulta na Solana as permissões de emissão e congelamento. Programa ou extensões não reconhecidas ficam pendentes.
- Registra **sinais de mercado com risco parcial** após duas consultas dentro dos critérios, espaçadas por pelo menos quatro minutos.
- Registra perda das condições e lacunas de dados. Não compra ou vende tokens.
- Compara preços observados após 15 minutos e uma hora, quando há nova consulta da mesma pool na janela prevista. Isso não representa lucro de execução.

## Cards e aderência aos critérios

O Dex Trade abre em cards, com três colunas no computador, agrupados em sinais confirmados, aguardando confirmação e em observação. Dados insuficientes, rejeitadas e fila ficam recolhidos. Há busca por nome/ticker/contrato, filtros por situação, ordenação por aderência/liquidez/volume/consulta e alternância para tabela.

A nota é `arredondar(100 × critérios atendidos ÷ 7)`, com pesos iguais: liquidez, volume de 5 minutos, quantidade de transações, relação de quantidade de compras/vendas, variação de 5 minutos, idade da pool e faixa de avaliação (market cap ou FDV identificado). Os limites vêm das regras publicadas pelo coletor. Idade e valores são avaliados no horário da consulta, não recalculados como se fossem novas observações. Seis de sete critérios resultam em 86/100.

A nota não estima lucro, segurança ou probabilidade de alta. Não modifica o coletor nem confirma alertas: 100/100 na primeira consulta continua aguardando a segunda consulta válida. Restrições, dados essenciais ausentes e consultas antigas não recebem nota numérica. Candidatas com consulta antiga passam para a área de dados insuficientes na visualização. Os detalhes mostram cada critério, valor, limite, motivos do coletor, histórico e dados brutos.

Sinais confirmados recebem um card dourado **Achado no garimpo**, com brilho e uma breve animação de partículas. As animações respeitam a preferência de movimento reduzido do sistema. Somente confirmações válidas recebem esse destaque no radar.

## Achados nas últimas 24 horas

A aba **Achados · 24h** mantém um card dourado para cada evento de confirmação durante as 24 horas seguintes ao sinal, mesmo se a moeda perder os critérios, for rejeitada ou sair do radar atual. O prazo começa na confirmação original; novas varreduras não o renovam. Uma nova confirmação com ID distinto tem seu próprio registro.

O card preserva os dados e as regras da confirmação, com a legenda **Aderência na confirmação**. A situação mais recente disponível aparece separadamente, incluindo ausência de nova consulta. Manter o dourado no histórico não significa que a moeda continua atendendo aos critérios. O histórico não simula operações ou lucro.

Os eventos ficam na tabela `pump_signal_history`, com leitura para contas ativas e escrita exclusiva do coletor. O RPC de publicação grava histórico e feed na mesma transação; repetir o mesmo evento não altera o registro original. Cada publicação remove registros com mais de 24 horas, e as regras de acesso também excluem registros expirados da leitura, mesmo se o coletor estiver pausado. A interface pagina 30 eventos por vez, sem depender do limite de 100 alertas do feed. A demonstração usa apenas eventos simulados locais.

## Cobertura parcial de risco

Há triagem de concentração reportada, LP e atividade atípica, mas não auditoria completa de carteiras, insiders, bundles, volume artificial ou retirada de liquidez. Não há nota de segurança ou probabilidade de lucro. A relação de compras/vendas usa **quantidade de transações**, não valores financeiros comprados e vendidos. Venda não é simulada.

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

O job conserva o nome legado `pump-radar-every-minute`, mas a expressão atual é `* * * * *`: roda a cada minuto. Chama a função `pump-radar` com autenticação interna gerada no Vault. O gateway JWT fica desativado porque a função valida seu próprio segredo de máquina.

Uma execução não se sobrepõe à outra. Mantém até 60 observações por token e até 400 alertas internos; o feed mostra os últimos 100. Mudança da pool principal reinicia a confirmação. Para pausar, desative o job na área Cron do Supabase. Não rode o worker Python legado simultaneamente.

O Game Sniper e seus registros foram preservados como espaço exclusivo do administrador. Contas comuns não têm acesso a esse portfólio. O radar é compartilhado e as conexões do Telegram são pessoais.

## Código e testes

Perfil ativo: `supabase/functions/pump-radar/free-core.ts`; coletor: `index.ts`. `core.ts` mantém utilitários e perfil GMGN legado, que não coleta dados nesta instalação. O processo Python legado não está ativado.

Infraestrutura versionada: `supabase_pump.sql`, `supabase_runtime.sql`, `free_market.sql`, `users_notifications.sql` e `signal_history.sql`. Não reaplique sem conferir as migrações existentes. Limites ficam em `freeRules`, exigindo novo deploy quando alterados.

```bash
python -m pytest -q
node --test tests/core.test.mjs tests/free-core.test.mjs tests/notifications.test.mjs tests/risk-whales.test.mjs
```

Fontes oficiais:

- https://docs.dexscreener.com/api/reference
- https://docs.dexscreener.com/
- https://support.coingecko.com/articles/6867086195-does-geckoterminal-have-an-api
- https://solana.com/docs/rpc/http/getmultipleaccounts
- https://solana.com/docs/references/clusters

### Frequência e atraso dos alertas

A partir de 28/10/2026, mercado, permissões, LP e saldos da amostra de detentores são consultados a cada minuto. O painel aberto busca o feed a cada 15 segundos. Atrasos dos provedores e o tempo de coleta se somam a esses intervalos; isso não equivale a dados em tempo real.

A confirmação conserva um mínimo de quatro minutos entre a primeira observação válida e a confirmação, com consultas intermediárias válidas. Uma falha reinicia a janela. Sinais já confirmados continuam ativos enquanto as condições se mantêm e as consultas não têm lacunas grandes. A janela de slow rug também permanece em 12–30 minutos, amostrada a cada quatro minutos; não é reduzida pela coleta rápida.

O RugCheck usa cache de até 30 minutos, teto de dez requisições em janela móvel de cinco minutos e até quatro por execução. Falhas recebem espera progressiva para dar vez aos demais tokens. Relatório vencido ou ausente mantém a avaliação pendente. O painel informa a duração de cada coleta. Erros gerais aguardam dois minutos antes de tentar novamente. Telegram prioriza eventos novos e repete falhas transitórias a partir de um minuto, respeitando `retry_after` no envio pessoal. Permanecem até três tentativas e expiração de 30 minutos.

### Redes no Dex Sniper

O seletor **Rede blockchain** abre feeds separados de Solana, Robinhood Chain, Ethereum, Base, BNB Chain, Arbitrum, Polygon, Avalanche e Optimism. Esta é a lista inicial integrada; não representa todas as redes do DEX Screener. Os IDs são explícitos e correspondem às redes dos provedores. Cada usuário pode navegar sem mudar a visualização dos demais.

Solana mantém os critérios, a triagem de risco, as confirmações, o histórico de 24 horas e as notificações existentes. As demais redes têm **observação de mercado**, com preço, volume, liquidez, transações, avaliação e contagem dos sete critérios. Não têm triagem de LP, permissões, honeypot, grandes carteiras ou slow rug, nem confirmação dourada, histórico de achados ou alertas automáticos. Os limites de mercado são inicialmente os mesmos da Solana e ainda não foram calibrados por rede.

A coleta adicional ocorre no servidor, depois da publicação primária e do envio de alertas da Solana. São até 15 tokens por rede adicional, com descoberta por pools novas e perfis recentes; isso não cobre todos os tokens de cada rede. As consultas usam lotes pequenos, timeout de 3 segundos por chamada e orçamento global para evitar concorrência com a varredura seguinte. Uma fonte lenta pode adiar uma rede; a tela informa horário, falhas e leituras antigas. O seletor muda a visualização, não desativa a coleta das outras redes. Telegram continua seguindo os sinais da Solana, independentemente da rede que está aberta na tela.

Robinhood usa a rede principal (`robinhood` no DEX Screener/GeckoTerminal), não a testnet. Tokens têm endereços EVM de 20 bytes; IDs de pools de 32 bytes, usados por protocolos como Uniswap v4, também são aceitos para o gráfico. A identidade inclui a rede para evitar misturar contratos iguais em blockchains diferentes.

O front-end consulta somente os campos do feed Solana ou somente o feed da rede escolhida, em vez de baixar todas as redes a cada atualização. Dados adicionais são publicados pelo mesmo processo autenticado, com as políticas de acesso existentes.
