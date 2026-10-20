# Fluxo — Gerenciador de tarefas

Aplicação em português com FastAPI, SQLite e interface responsiva.

## Iniciar no Windows

Instale Python 3.11 ou superior e dê dois cliques em `iniciar.bat`. Na primeira execução, é necessário acesso à internet para instalar dependências. Mantenha a janela aberta enquanto usa a aplicação. Acesse http://127.0.0.1:8000 e crie sua conta.

Alternativa pelo terminal, dentro desta pasta:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## Recursos

- Cadastro, login e logout; senhas protegidas com scrypt.
- Sessões de sete dias em cookies HttpOnly e SameSite.
- Tarefas privadas por usuário, com título, descrição, prazo e prioridade.
- Status A fazer, Em andamento e Concluída, alterados em Editar.
- Busca, filtros por prioridade, tarefas de hoje e tarefas em atraso.
- Edição, exclusão com confirmação e indicadores de progresso.
- Dados persistidos no arquivo `tarefas.db`, criado automaticamente.
- Documentação da API em http://127.0.0.1:8000/docs.

## Dados e hospedagem

Faça backup de `tarefas.db` com a aplicação encerrada. Para alterar a localização do banco, configure TASK_DB com o caminho desejado.

Esta entrega usa servidor local. Para disponibilizar na internet, configure hospedagem Python com HTTPS, armazenamento persistente e COOKIE_SECURE=1. Antes de uso público, adicione limitação de tentativas de login e recuperação/verificação de e-mail. Não há recuperação de senha nesta versão.

## Verificação

Fluxos da API testados: cadastro, e-mail duplicado, login, logout, persistência, criação/edição/exclusão, datas e status inválidos, isolamento entre duas contas e bloqueio de requisições de outra origem. Interface sem verificação visual automatizada.
