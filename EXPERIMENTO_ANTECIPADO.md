# Descoberta antecipada — early-v1

Experimento limitado à Solana. Não é recomendação de investimento, classificação de moeda segura ou detector comprovado de pontos de entrada. Não executa operações e não usa novos serviços pagos.

## Modo e reversão

Em **Dex Sniper → Opções → Modo do radar**, escolha **Antecipado · experimental** ou **Clássico** e aplique. A preferência persiste por conta no servidor e determina a visualização e os avisos pessoais no Telegram, inclusive com o painel fechado. Em Operação do experimento, **Voltar ao Clássico** aplica a reversão diretamente.

O administrador foi incluído no teste; as outras contas conservam o modo Clássico por padrão. A versão anterior de referência é o commit `40322b9968315f456d2c5dbc161b60b5c631afbb`. Os sete critérios, a confirmação de quatro minutos e o histórico de achados do Clássico permanecem em paralelo, sem substituir ou reinterpretar os registros anteriores.

Quando nenhuma conta ativa usa o experimento, não são consultadas as dez posições adicionais e não são gerados novos avisos experimentais. Relatórios coletados durante o teste podem continuar no cache até a expiração normal. A alternância de modo não reconstrói alertas anteriores nem envia os avisos do outro modo.

## Descoberta e evidências

Além das 30 posições do radar clássico, até dez posições recebem outras descobertas recentes do GeckoTerminal e dos perfis do DEX Screener. O conjunto adicional pode renovar posições após dez minutos. Isso é uma amostra, não uma busca completa da blockchain; perfis podem ser promocionais e fontes podem limitar respostas. Os relatórios de risco compartilham o orçamento de dez chamadas por cinco minutos, sem expansão da cota. Com mais tokens, alguns podem esperar mais pelo relatório.

Toda moeda com preço consultável passa a ter primeira leitura do teste: preço, liquidez, avaliação e horário. Não há piso de MC, alta obrigatória, volume mínimo de US$ 5 mil ou idade mínima de 15 minutos para observação. MC e FDV continuam distintos. Não se presume descoberta no lançamento.

O aviso de **triagem inicial atendida** exige, em duas consultas válidas separadas por pelo menos 45 segundos, normalmente um minuto:

- Mint/freeze desabilitados e extensões reconhecidas.
- Liquidez de pelo menos US$ 25 mil.
- Ausência de queda superior a 20% da liquidez em relação à primeira leitura ou à leitura anterior. É restrição de triagem, não prova de retirada de liquidez.
- Camada `risk-v1` revisada parcialmente, incluindo consulta atual da LP.
- Pelo menos uma venda registrada pelo provedor. Isso não é simulação de venda nem demonstra que qualquer carteira consegue vender.

Uma lacuna maior que três minutos ou falha reinicia a sequência. LP, concentração e alertas críticos continuam retendo os avisos. Nenhuma nova nota 100/100 é produzida pelo experimento. A separação entre segurança e força do movimento é explícita; o teste ainda não audita compradores únicos, organicidade, vínculos entre carteiras, bundles, insiders ou vendas simuladas. Esses dados ausentes não são apresentados como verificações aprovadas.

O aviso inicial é retido quando o preço já subiu mais de 50% desde a primeira leitura ou mais de 40% nos cinco minutos reportados. Esses limites são hipóteses sem calibração. Se a moeda já subiu antes da descoberta, o experimento pode não reconhecer esse trecho. A triagem atendida não representa entrada favorável.

Um aviso inicial é emitido por episódio de token/pool. Mudanças posteriores para restrição, pendência ou movimento avançado podem emitir aviso identificado, limitado a uma mudança a cada dez minutos. Não é instrução de saída. Alertas pessoais seguem a preferência salva e o horário de ativação. O bot global legado continua clássico.

## Comparação e cobertura

A tabela `dex_early_trials` mantém episódios de primeira leitura por até sete dias. A interface mostra os últimos cem, incluindo pendentes e bloqueados. Registra o primeiro aviso antecipado, a primeira confirmação clássica observada após o início do episódio, variações de preço em 15 minutos e uma hora quando houver consulta na janela (até três minutos de tolerância) e extremos de preço observados em relação à primeira leitura. Não mede lucro realizável, taxas, slippage ou impacto da ordem. Moedas já confirmadas no Clássico antes do episódio não recebem uma confirmação clássica artificial na ativação do teste.

A saída do radar é registrada como cobertura interrompida. Uma moeda não acompanhada não é tratada como resultado zero, fracasso ou sucesso. Não há índice de acerto calculado nem promessa de superioridade. Tokens que as fontes nunca descobriram e episódios sem preço utilizável não aparecem na amostra. A cache de episódios em execução é limitada a 300 registros/24h; registros já persistidos no banco têm retenção de sete dias.

A gravação é feita somente pelo serviço de coleta. Usuários ativos podem ler os registros de mercado; não podem gravar ou alterar a preferência de terceiros. A troca de modo passa pela autenticação existente e atualiza apenas a conta do próprio usuário.

## Cores e revisão do gráfico

Verde, **Vale abrir o gráfico**, destaca apenas a triagem inicial atendida e recente (até dois minutos). São possíveis oportunidades para análise manual, sem sinal de compra. Azul indica observação, cinza falta de dados, amarelo movimento avançado na janela observada e vermelho restrição identificada. As demais cores ficam recolhidas para priorizar o que merece revisão. O Telegram e o navegador usam o mesmo aviso de revisão de gráfico. Os critérios do experimento não mudam por causa das cores; não há garantia de segurança ou de preço favorável.
