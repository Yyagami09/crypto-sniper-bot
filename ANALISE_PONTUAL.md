# Analisar contrato

Em **Dex Sniper → Analisar contrato**, selecione a rede, escolha Análise geral, Riscos do contrato ou Possível reentrada e cole o contrato do token ou um link HTTPS de par no DEX Screener. O link precisa corresponder à rede escolhida. Tokens EVM são validados por endereço de 20 bytes; links podem conter IDs de pools de 32 bytes. Solana usa endereços Base58.

A consulta funciona fora do radar e não adiciona moedas ao acompanhamento, altera critérios, cria episódios de teste ou envia Telegram. O resultado fica na sessão do usuário, com contrato, rede e horário explícitos. Uma nova consulta limpa o resultado anterior, inclusive se falhar, para evitar apresentar dados antigos como uma nova análise. Após três minutos, o resultado recebe aviso de desatualização.

## Fontes e verificações

O DEX Screener fornece o mercado. Para um contrato, é escolhida a pool de maior liquidez dentre as que identificam o token como ativo base. Para um link de par, o par informado é respeitado. Se a fonte não encontrar o token nessa cobertura, o usuário é orientado a conferir rede/contrato ou colar o link do par. Não são misturados contratos ou redes nem usados links de origem arbitrária.

Na Solana, permissões do mint, LP e a amostra de detentores são consultadas no RPC público. Relatórios de risco válidos do cache do radar são reaproveitados por até 30 minutos; sem relatório utilizável, a consulta tenta o RugCheck público uma vez. A LP é reavaliada com contas atuais; falhas deixam os itens pendentes. A primeira leitura de detentores mostra saldos, sem afirmar compras, vendas ou movimento de baleias. Uma análise pontual não detecta slow rug ao longo do tempo.

Nas demais redes integradas, a cobertura é de mercado e histórico quando disponível; contrato, LP, concentração e RugCheck continuam sem verificação adaptada. Ausência de dados não recebe aprovação.

## Gráfico e possível reentrada

Análise geral e Possível reentrada tentam consultar até 60 candles de um minuto do token e da pool selecionada no GeckoTerminal público, em USD. O foco Riscos do contrato evita essa chamada adicional. Apenas candles completos são usados; o candle em formação e dados inválidos são descartados.

A leitura de reentrada exige pelo menos 20 candles recentes e não aceita lacunas maiores que três minutos. Sem histórico suficiente, o resultado diz expressamente que faltam dados, sem estimar níveis a partir de market cap ou volume atual.

Quando possível, mostra fechamentos em um gráfico de linha e referências inferior/superior das até 30 últimas observações, excluindo os três candles mais recentes. Também informa se as mínimas dos últimos três candles aumentaram, se o último fechamento superou a máxima anterior, a distância da máxima observada na janela e a comparação do volume dos cinco candles recentes com os cinco anteriores. São descrições de uma amostra, não suportes, resistências, pontos de entrada, alvos ou stops confirmados. Os níveis estão em preço USD, não market cap.

A conclusão é baseada em regras transparentes. Não há interpretação livre por IA, ordens de compra/venda, promessa de rentabilidade, simulação de execução ou repetição automática de consultas.

## Acesso e limites

O endpoint reutiliza a autenticação de `sniper-account`, valida o JWT com Auth e exige conta ativa antes de qualquer consulta. Um RPC restrito ao serviço reserva atomicamente uma consulta por usuário a cada 30 segundos. Dados inválidos são rejeitados antes da reserva. O limite protege as fontes gratuitas e não garante disponibilidade ou cota. O banco guarda apenas o horário da tentativa no perfil; o relatório não é salvo no feed público ou no histórico compartilhado.

A interface faz a consulta somente ao enviar o formulário. Alterar campos, navegar ou abrir o submenu não dispara chamadas de análise. Tokens de serviço, segredos de Telegram e relatórios brutos do cache não são devolvidos ao cliente.

## Card de conclusão e pontuação

A interface mostra uma conclusão separada da nota: Favorável para observar, Atenção, Desfavorável na triagem ou Dados insuficientes. No foco de riscos, o destaque favorável se limita à triagem de risco, sem avaliar momento de entrada. Uma restrição prevalece sobre qualquer nota; conclusão incompleta, rede sem cobertura e consulta antiga nunca recebem destaque favorável. Após três minutos, a pontuação da consulta deixa de valer e os itens ficam pendentes.

A nota mede aderência, sem estimar lucro, segurança ou probabilidade de sucesso. Pesos: emissão 10, congelamento 10, programa/extensões 5, RugCheck 10, LP protegida 15, Top 10 fora das pools 10, participação do criador na LP de referência 10, liquidez 10, vendas registradas 5, giro volume/liquidez 5, três mínimas ascendentes 5 e volume dos candles recentes 5. No foco de risco, os dois itens de candles são excluídos e a soma de 90 pontos é normalizada para 100. Pendências e avisos recebem zero, sem redistribuir peso entre os demais itens. A composição aparece por item.

Os limites de risco existentes são mantidos: LP reportada com proteção de pelo menos 90%, concentração externa Top 10 de até 50%, participação do criador na LP de referência de até 10%, liquidez mínima de US$ 25 mil. LP exige consulta em cadeia recente (até 120 segundos), além de relatório válido por até 30 minutos. O giro de volume de até 5 vezes a liquidez atende, entre 5 e 10 recebe atenção, acima de 10 é restrição experimental. Isso não comprova manipulação. Uma venda reportada não simula execução. Três mínimas ascendentes e volume de cinco candles igual ou superior aos cinco anteriores são hipóteses locais de observação, sem comprovar reversão. Os filtros não foram calibrados para rentabilidade.

A mudança é de apresentação; não altera o radar, as chamadas às fontes, a autenticação, os alertas ou a execução de ordens.
