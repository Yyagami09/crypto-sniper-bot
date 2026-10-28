# Acesso e alertas

## Contas

O painel exige login por usuário e senha, com Supabase Auth. O nome de usuário é mapeado internamente a um endereço reservado `.invalid`, sem e-mails enviados. A chave administrativa permanece apenas nas Edge Functions. Não existe cadastro público com acesso: só usuários com perfil ativo criado pelo administrador entram no painel.

O admin vê **Usuários**, com lista de contas, criação, redefinição de senha e desativação/reativação. Novas contas são sempre comuns. A API também verifica o perfil do administrador, independentemente da interface. Desativar uma conta bloqueia os dados no banco e as operações no backend, inclusive para tokens de acesso ainda válidos. A própria conta do admin é protegida contra desativação pela interface. As senhas iniciais são entregues separadamente; nunca estão neste repositório.

Cada conta pode alterar a própria senha em **Notificações → Alterar minha senha**. Não há recuperação por e-mail porque o login atual usa nomes de usuário; o administrador redefine a senha das contas comuns. A sessão fica no servidor Streamlit e pode exigir novo login ao atualizar/fechar a página. Clientes Auth não são compartilhados entre usuários.

Contas comuns acessam os dados e sinais compartilhados do Dex Trade e sua conexão pessoal. O portfólio Game Sniper existente e sua edição são exclusivos do admin. Os 44 registros existentes não foram migrados nem removidos.

## Som e notificações do navegador

Em **Dex Trade**, clique em **Ativar e testar som**. O clique libera e testa o áudio. Opcionalmente ative as notificações do navegador, aceitando a permissão do site. Confira volume, permissões e Não Perturbe do Windows. Se o ambiente não permitir a notificação, o controle informa a limitação.

O painel compara os IDs dos eventos recebidos, ignora o histórico no primeiro carregamento, não repete o mesmo evento nesta página e ignora eventos com mais de 15 minutos. Sinais confirmados, condições perdidas e indisponibilidade de dados podem avisar; avisos simultâneos são agrupados em um som/notificação. Demonstração e dados reais usam controles isolados.

O painel consulta o feed a cada 15 segundos enquanto a sessão funciona. Não é push independente da página: suspensão/fechamento da aba, mudança de módulo, perda de conexão ou repouso podem interromper os avisos. As opções precisam ser ativadas novamente numa nova página/sessão. O coletor continua rodando no Supabase.

## Conectar Telegram

1. Abra **Notificações** com seu login.
2. Abra o BotFather oficial, envie `/newbot` e crie um bot dedicado.
3. Cole a chave do bot no campo protegido e clique em **Preparar conexão**.
4. Abra o link gerado e toque em **Iniciar** no Telegram. O link expira em 15 minutos.
5. Volte ao painel e clique em **Já toquei em Iniciar — confirmar conexão**.
6. Use **Enviar teste ao meu Telegram** para conferir entrega, som e notificações no celular/Windows.

Não basta fornecer um número de telefone: um bot precisa que o usuário abra a conversa. O assistente identifica automaticamente a conversa privada pelo comando `/start` com um código único e recente, confirma o remetente e não coleta o número ou credenciais da conta Telegram. Bots com webhook já configurado são rejeitados, sem alterar a integração existente. Use um bot por conta; não conecte o mesmo bot a dois usuários.

O token é criptografado no Supabase Vault. Chat ID, conexão, segredo e histórico de entregas não são expostos no feed nem a outros usuários. A confirmação não envia mensagem sozinha; o botão de teste envia uma mensagem explicitamente identificada como teste. O coletor envia os novos alertas reais após a conexão, mesmo com a página fechada. Não envia eventos simulados ou anteriores à conexão. Há limite de tentativas, até 10 envios por ciclo e expiração de 30 minutos. Entrega é ao menos uma vez: timeouts podem causar duplicação. Bloqueio do bot ou token inválido desativa os envios até reconectar.

**Desconectar meu Telegram** desativa a conexão e substitui a chave armazenada por uma string vazia no Vault. Isso não revoga a chave no Telegram; revogue pelo BotFather se necessário. Notificações dependem do aplicativo Telegram e das permissões do sistema. Sem conexão Telegram, o radar continua funcionando.

## Backend

- `sniper-account`: valida cada JWT com Supabase Auth e exige perfil ativo no banco. Gerencia contas (admin), senhas próprias e conexão/teste/desconexão pessoal.
- `sniper_profiles`: usuários leem apenas o próprio perfil; somente backend escreve funções e privilégios.
- `sniper_telegram` / `sniper_deliveries`: acesso exclusivo do backend. Funções do Vault têm execução revogada para `anon` e `authenticated`, com verificação adicional de `service_role`.
- `pump-radar`: coleta a cada 5 minutos e entrega eventos novos às conexões ativas, com registros de tentativas por usuário/evento. Credenciais nunca entram no feed de mercado.
- `users_notifications.sql`: referência da migração já aplicada em partes nomeadas. Não reaplicar sobre a instalação atual.

As contas iniciais foram provisionadas pela API administrativa do Supabase, não por inserções diretas em `auth.users`. O bootstrap exige o segredo interno do cron e se recusa a rodar depois de existir qualquer perfil. Nenhuma senha é retornada por APIs de lista de usuários.
