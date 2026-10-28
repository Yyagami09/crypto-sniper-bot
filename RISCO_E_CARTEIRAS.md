# Camada de risco e grandes detentores

Perfil `risk-v1`, separado dos sete critérios de atividade. O score de mercado não é uma nota de segurança. Dados essenciais de risco ausentes deixam o token pendente, sem confirmação ou destaque dourado no radar.

## Regras experimentais de retenção

- Alertas `danger` do RugCheck retêm o sinal. Avisos `warn` ficam visíveis.
- A pool escolhida por liquidez deve ter LP reportada como travada/queimada em pelo menos 90%. Relatório de outra pool não serve como verificação.
- Concentração reportada do Top 10, agrupada por proprietário e excluindo contas/autoridades de pools conhecidas no relatório, acima de 50% retém o sinal.
- O mint de LP e uma amostra de até três contas de LP são consultados novamente na Solana. Participação estimada do criador acima de 10% da oferta de referência da LP retém o sinal. O percentual de tokens circulantes é mostrado separadamente: possuir 100% dos tokens ainda circulantes não significa necessariamente controlar 100% de uma pool com LP previamente queimada.
- Giro de volume em cinco minutos acima de dez vezes a liquidez retém o sinal como atividade atípica. É uma heurística não calibrada; não comprova wash trading. Acima de cinco vezes gera aviso.
- Em caso de dados ausentes, falha de API ou RPC, a avaliação fica pendente. A primeira consulta válida após ativar esta versão reinicia a confirmação; sinais anteriores não são automaticamente promovidos pela nova política.

As verificações básicas de mint/freeze, extensões não reconhecidas e queda de liquidez continuam ativas. Não há auditoria completa, garantia contra honeypot, simulação de venda, verificação de todas as carteiras ou rastreamento independente de insiders/bundles. Relatórios críticos em cache podem gerar falsos positivos até atualizarem. Falta de alerta externo não prova ausência de risco.

## APIs e cadência

O coletor continua a cada cinco minutos, sem depósito, assinatura ou nova chave. Consulta até dez relatórios RugCheck por ciclo, serializados e com limite de tempo. O cache local de relatório expira após 30 minutos; o provedor pode servir seu próprio cache. O painel distingue consulta do relatório e consulta da LP. Na primeira ativação, alguns tokens podem precisar de vários ciclos para obter dados.

As consultas de contas de LP e detentores são agrupadas em lotes de até 100 no RPC público da Solana. Consultas incompletas não liberam sinais. O feed só recebe o resumo criado pelo coletor; não publica respostas brutas do provedor ou caches internos.

## Movimentação de grandes carteiras

Indicador complementar, sem adicionar pontos aos sete critérios e sem bloquear um sinal por si só. Monitora uma amostra de até cinco contas dos maiores detentores fora das pools, agrupadas por proprietário. Destaca quem tem pelo menos 1% da oferta ou saldo estimado de pelo menos US$ 10 mil. Não é uma busca de todas as carteiras com grande patrimônio na rede.

Compara saldos atuais na Solana com a leitura anterior entre quatro e vinte minutos. A primeira leitura fica aguardando comparação. Falhas de RPC não são tratadas como saldo zero. Uma conta confirmadamente encerrada pode indicar redução para zero. Mudanças na amostra reiniciam a comparação para não gerar fluxos fictícios. Uma alta de preço sem mudança de tokens não aparece como entrada.

O painel mostra aumento/redução de saldo, quantidade de tokens e valor estimado ao preço consultado. Isso pode ser transferência entre contas, envio para exchange, airdrop ou outras operações; não comprova compra/venda ou intenção. Não há notificações externas novas só por esse indicador.

## Indícios de slow rug

Dois mecanismos distintos, ambos experimentais:

1. **Possível retirada gradual de liquidez:** quatro observações ao longo de 12–30 minutos, com três reduções consecutivas no supply de tokens de LP (queda acumulada de pelo menos 5%) e queda de pelo menos 10% em cada uma das duas reservas da pool. Mudança de pool reinicia a janela; lacunas grandes impedem o diagnóstico. Esse padrão retém o sinal e informa que é compatível com retirada gradual, sem declarar fraude.
2. **Redução gradual de grandes detentores:** três reduções consecutivas de saldo, acumulando ao menos 10% do saldo inicial e 0,5% da oferta do token, em 12–60 minutos. Mostra um aviso complementar por carteira. Pode ser transferência ou distribuição legítima e não altera a nota ou o bloqueio por si só.

São observações de estados entre consultas, não leitura de todas as transações de retirada ou venda. Queima voluntária de LP, operações legítimas e mudanças de reservas podem afetar as leituras. A combinação reduz confusões com simples queda de preço, mas não elimina falsos positivos ou falsos negativos. Dados insuficientes aparecem como coleta em andamento; ausência de padrão não significa ausência de slow rug.

## Histórico e alertas

Os achados das últimas 24 horas permanecem no histórico com os dados originais. Confirmações antigas sem a camada de risco são identificadas como anteriores à política. A situação atual pode estar bloqueada ou pendente. O histórico dourado não indica aprovação atual.

O envio de novas candidatas ao Telegram exige a nova camada revisada e que o token continue confirmado na mesma pool. Uma tentativa atrasada não deve enviar uma candidata que perdeu as condições. Avisos de perda de condições e indisponibilidade continuam funcionando.

## Código

- `risk.ts`: relatório resumido, política de LP/concentração/atividade e consultas agrupadas.
- `whales.ts`: amostra e comparação de saldos públicos.
- `trends.ts`: observações de LP e reservas por pool.
- `free-core.ts`: aplica o veto de risco antes da confirmação.
- `pump/criteria.py`: mantém a nota oculta enquanto o risco não permite a triagem.
- `pump/radar_cards.py`: indicadores, limites, avisos e carteiras nos detalhes.

Referências: https://fluxrpc.com/docs/rugcheck/getTokenReport e https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_SWAP_README.md
