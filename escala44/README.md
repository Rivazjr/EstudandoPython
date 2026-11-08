# Escala 44 — 44º BPM / Pará

Aplicação local com Python 3.10 ou superior, sem dependências externas. Inclui servidor HTTP, banco SQLite e interface responsiva em português.

## Executar

```bash
cd /home/rivazhome/escala44
python3 app.py
```

Abra http://127.0.0.1:8080 no navegador do mesmo computador.

No primeiro início, o sistema gera `.setup-key`. Em outro terminal, leia a chave:

```bash
cat /home/rivazhome/escala44/.setup-key
```

Na tela “Primeira instalação”, informe a chave, seu email, CPF válido e uma senha com pelo menos 10 caracteres. Esse cadastro será o administrador. A chave é removida após a configuração. Entre e defina seu nome de guerra.

Policiais usam “Solicitar acesso” e aguardam aprovação em Administração. O nome de guerra é escolhido após o primeiro login aprovado. Não existem usuários ou senhas padrão.

## Regras implementadas

- Polícia Mais Forte: capacidade inicial **diária** de 11 cotas em Salinópolis, 60 em São João de Pirabas e 60 em Santarém Novo.
- Escola Segura: capacidade inicial **mensal** de 240 cotas em Salinópolis, 60 em São João de Pirabas e 60 em Santarém Novo; reservas apenas de segunda a sexta. Feriados não são tratados nesta versão.
- A interpretação de diária/mensal pode ser ajustada na administração para cada operação e município, em cada mês.
- O administrador configura limites **mensais por policial e por operação**, separando segunda a sexta e sábados/domingos. Limites iniciais provisórios: 4 em dias de semana e 2 em fins de semana; configure antes de liberar o efetivo. Escola Segura nunca aceita fins de semana, independentemente do limite.
- Os limites por policial abrangem os três municípios juntos. Eles não podem ser ampliados trocando o município.
- Uma reserva por policial, operação e data, em qualquer município. As duas operações têm controles independentes: esta versão permite um serviço em cada operação na mesma data. Não existe controle de horário ou sobreposição entre operações.
- Datas passadas são bloqueadas. Cancelar libera a cota. Alterações de capacidade/limites preservam reservas anteriores; se o novo limite for menor que a ocupação, novas reservas ficam bloqueadas.
- O mês novo começa com as capacidades e limites iniciais; não copia automaticamente as alterações do mês anterior.
- Reservas concorrentes são serializadas no banco. A restrição de unicidade também é aplicada pelo SQLite.
- Administração inclui aprovação do efetivo, regras por mês, escala consolidada e exportação CSV.

## Persistência e implantação

Os dados ficam em `data.sqlite3`. Preserve esse arquivo e faça cópias de segurança. Não o publique junto do código. As senhas usam PBKDF2-SHA256 com salt aleatório; sessões ficam no servidor, com cookies HttpOnly e SameSite=Strict.

A aplicação está preparada para execução local. Para disponibilização institucional, precisa de hospedagem Python com disco persistente, HTTPS e proxy reverso com proteção contra tentativas repetidas de login. A interface foi publicada em https://escala44.vercel.app e conectada ao servidor deste PC por túnel HTTPS. A validação visual em navegador não foi realizada neste ambiente. Não há recuperação automática de senha, envio de emails, segundo fator, trilha de auditoria ou cadastro de feriados nesta versão.

Configuração por variáveis de ambiente:

- `PORT`: porta, padrão 8080.
- `ESCALA_HOST`: endereço de escuta, padrão 127.0.0.1.
- `ESCALA_DB`: caminho do banco, padrão data.sqlite3 ao lado de app.py.
- `ESCALA_HTTPS=1`: habilita o atributo Secure no cookie; use quando servido por HTTPS.

## Verificação

```bash
python3 -m unittest -v test_app.py
```

O teste usa banco temporário e servidor em loopback. Verifica instalação do administrador, autenticação, aprovação, permissões, nome de guerra, disputa pela última cota, duplicidade, limite mensal, cancelamento e capacidade mensal do Escola Segura. Não altera dados reais.

## Servidor automático e acesso pela Vercel

A interface está em https://escala44.vercel.app. O servidor Python e o banco SQLite ficam neste PC.

O agendador cron do usuário inicia o supervisor ao ligar o PC, sem depender de abrir o chat ou fazer login. Ele também verifica a cada minuto se o supervisor está ativo. O supervisor verifica os processos e a conexão a cada 15 segundos. Um bloqueio de arquivo impede a execução de supervisores duplicados. Se o supervisor encerrar abruptamente, sua próxima execução limpa os processos filhos antigos antes de abrir novos.

A configuração está no bloco `ESCALA44 AUTO` do crontab do usuário e é reproduzida em `ops/escala44.cron`. As entradas anteriores do crontab são preservadas. O serviço cron do sistema está habilitado e ativo. O antigo serviço systemd de usuário foi desabilitado; a inicialização atual não exige `loginctl enable-linger` nem senha administrativa.

```bash
crontab -l
tail -40 /home/rivazhome/escala44/service.log
```

Para suspender essa inicialização, remova o bloco `ESCALA44 AUTO` usando `crontab -e` e encerre o supervisor. Um desligamento normal do supervisor encerra também o servidor e o túnel.

### Recuperação da conexão

`ops/supervisor.py` acompanha o servidor e o cliente Cloudflare Tunnel. Ele testa o acesso local e público e reinicia processos que falharem. A cada 15 segundos, comunica o endereço atual a uma função de registro no Supabase. A Vercel consulta esse registro a cada chamada e deixa de depender de um endereço fixo ou de novo deploy para reconectar. A interface tenta reconectar a cada 15 segundos quando exibe indisponibilidade.

O Supabase guarda somente **um endereço de túnel e a data do último sinal de funcionamento**. Cadastros, CPFs, senhas e agendamentos ficam exclusivamente no SQLite local. A tabela técnica tem RLS e não oferece acesso público direto. A função de registro exige uma chave exclusiva. Sua impressão SHA-256 está na implementação; a chave em si fica apenas no arquivo local `.connection-key` (permissão 0600) e em variável sensível de produção na Vercel. O servidor local exige essa chave nas chamadas encaminhadas. Ela não vai para o navegador nem para o GitHub.

Os endereços registrados expiram após 3 minutos sem sinal. A Vercel retorna uma mensagem de indisponibilidade quando o PC está desligado ou sem rede. A descoberta usa o projeto Supabase já criado (`mgvnrmzfnttwzvwqaozd`), sem transferir o banco de agendamentos para ele.

### Disponibilidade

O PC precisa estar ligado, acordado e conectado à internet. Reinício automático reduz interrupções de processos; não elimina quedas de energia, suspensão, falhas de rede nem indisponibilidade de serviços externos. O túnel rápido Cloudflare é temporário e não oferece garantia de disponibilidade. A descoberta automática permite trocar seu endereço sem intervenção manual. Após uma queda do supervisor, o cron pode levar até cerca de um minuto para iniciá-lo novamente, mais o tempo de estabelecer o túnel. Não é uma solução com SLA.

### Arquivos e instalação

- `ops/escala44.cron`: inicialização no boot e verificação periódica.
- `ops/supervisor.py`: supervisão permanente e registro do túnel.
- `ops/registry.ts`: função técnica de descoberta, autenticada com chave exclusiva.
- `ops/escala44.service`: alternativa systemd, desabilitada neste PC.
- `api/index.py`: gateway da Vercel.
- `.connection-key`, `.setup-key`, `data.sqlite3`, `.supervisor*`: arquivos locais privados, excluídos do GitHub.

Ao instalar em outro computador, ajuste os caminhos absolutos do crontab e preserve o banco e as chaves em local seguro. O cliente `cloudflared` é obtido de https://github.com/cloudflare/cloudflared/releases e não é versionado.

### Verificações realizadas

```bash
python3 -m unittest -v test_app.py test_gateway.py
```

Os testes verificam as regras de reserva, permissões, segurança do gateway e falhas de conexão. A API publicada respondeu HTTP 200 a uma consulta autenticada e retornou os 10 agendamentos existentes. Um teste operacional interrompeu o supervisor e conferiu a recuperação do acesso pela Vercel com um novo endereço de túnel e a preservação das reservas. O boot real do computador e a interface visual em navegador não foram testados.

Código: https://github.com/Rivazjr/EstudandoPython/tree/escala44/escala44
