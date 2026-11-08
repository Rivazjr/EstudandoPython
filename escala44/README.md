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

## Publicação com banco neste PC

A arquitetura escolhida mantém SQLite e o servidor Python neste computador. A Vercel serve a interface e encaminha `/api/*` pelo gateway `api/index.py` para o endereço HTTPS definido em `ESCALA_BACKEND_URL`. Cookies de sessão são mantidos no domínio da interface, com HttpOnly, SameSite=Strict e Secure. O gateway bloqueia redirecionamentos externos e requisições POST de outra origem.

O servidor local escuta somente em 127.0.0.1:8080. O túnel Cloudflare expõe esse servidor por HTTPS sem abrir portas no roteador. O arquivo do banco nunca é enviado à Vercel ou ao GitHub.

Para iniciar o servidor:

```bash
python3 app.py
```

Em outro terminal, inicie o cliente Cloudflare baixado nesta pasta:

```bash
./cloudflared tunnel --url http://127.0.0.1:8080 --protocol http2 --no-autoupdate
```

O cliente pode ser baixado do projeto oficial https://github.com/cloudflare/cloudflared/releases. Ele não é incluído no GitHub.

**O endereço do túnel rápido muda ao reiniciar.** Atualize `ESCALA_BACKEND_URL` na Vercel e faça novo deploy quando isso acontecer. O computador, o servidor e o túnel precisam permanecer ativos. Este túnel não tem garantia de disponibilidade; para um endereço estável, use um túnel nomeado em uma conta Cloudflare com domínio próprio.

A chave para criar o primeiro administrador é a `.setup-key` deste PC. Leia-a localmente e use na tela “Primeira instalação”; ela é apagada após a configuração. Nunca a inclua em commits.

Vercel: equipe wanz2, projeto escala44. O Supabase escala44 foi criado antes da decisão de manter o banco local; ele contém apenas tabelas vazias e não é usado pela aplicação atual. Custo informado na criação: US$ 0/mês.

A interface não foi validada visualmente em navegador neste ambiente. O teste automatizado cobre as regras do servidor local. Não foi configurado deploy automático a partir do GitHub.

Endereço publicado: https://escala44.vercel.app
Código: https://github.com/Rivazjr/EstudandoPython/tree/escala44/escala44

Foram verificados HTTP 200 da página, JavaScript, CSS e status da API, além de HTTP 401 para consulta sem sessão.
