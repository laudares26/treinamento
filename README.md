# LMS IDE-SP — Backend API

Plataforma de Capacitação e Treinamento do Projeto IDE-SP.

## Stack

- **Python 3.12** + **FastAPI**
- **PostgreSQL 15+** com schema `lms`
- **SQLAlchemy 2.0** (async) + **Alembic** (async migrations)
- **JWT** (python-jose) + **bcrypt** (passlib)
- Deploy via **fly.io** (Docker, porta 8080)

## Setup Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edite DATABASE_URL e SECRET_KEY
alembic upgrade head
psql $DATABASE_URL -f scripts/init_db.sql   # schema lms, extensões, seeds, índices
uvicorn app.main:app --reload
```

> O app também auto-cria tabelas e seeds (perfis, níveis, permissões RBAC) no startup via FastAPI lifespan. O passo `alembic upgrade head` + `init_db.sql` é opcional em dev, mas obrigatório em staging/prod.

**Arquivo `.env`:**
| Variável | Default | Descrição |
|----------|---------|-----------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/lms_idesp` | Conexão com PostgreSQL |
| `SECRET_KEY` | `change-me-in-production` | Chave para assinar JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Expiração do token |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Origens permitidas |

## Endpoints

Acesse `/docs` (Swagger UI) ou `/redoc`.

### Autenticação e Credenciamento

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/auth/registro` | Cria conta com perfil **participante** (ativa imediatamente, exige `aceite_lgpd=true`) |
| POST | `/api/v1/auth/registro-com-perfil` | Cria conta com **solicitação pendente** — precisa aprovação (exige `aceite_lgpd=true`) |
| POST | `/api/v1/auth/login` | Login → JWT |
| POST | `/api/v1/auth/logout` | Logout (cliente remove token) |
| POST | `/api/v1/auth/esqueci-senha` | Envia link de redefinição por email |
| POST | `/api/v1/auth/redefinir-senha` | Redefine senha com token recebido |
| GET | `/api/v1/credenciamento/solicitacoes/pendentes` | Lista solicitações aguardando aprovação |
| POST | `/api/v1/credenciamento/solicitacoes/{id}/aprovar` | Aprova solicitação |
| POST | `/api/v1/credenciamento/solicitacoes/{id}/rejeitar` | Rejeita solicitação |

### Usuários e RBAC

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/usuarios` | Lista usuários (filtro: `?perfil_nome=instrutor`) |
| GET | `/api/v1/usuarios/me` | Dados do usuário logado |
| GET | `/api/v1/usuarios/{id}` | Obter usuário por ID |
| PATCH | `/api/v1/usuarios/{id}` | Atualizar usuário |
| DELETE | `/api/v1/usuarios/{id}` | Excluir usuário |
| POST | `/api/v1/usuarios/criar-subordinado` | **[Gestor]** Cria conta participante já aprovada |
| GET | `/api/v1/usuarios/perfis/todos` | Lista todos os perfis |
| POST | `/api/v1/usuarios/perfis` | Criar perfil |
| PATCH | `/api/v1/usuarios/perfis/{id}` | Atualizar perfil |
| DELETE | `/api/v1/usuarios/perfis/{id}` | Excluir perfil (impedido se houver usuários vinculados) |
| POST | `/api/v1/usuarios/perfis/atribuir` | Atribuir perfil a usuário |

### Sandbox do Instrutor

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/sandbox/iniciar` | Inicia sessão de teste |
| POST | `/api/v1/sandbox/{id}/encerrar` | Encerra sessão e descarta dados |
| GET | `/api/v1/sandbox/ativo` | Verifica se há sessão ativa |
| GET | `/api/v1/sandbox/sessoes` | Histórico de sessões |

### Cursos (US-05)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET/POST | `/api/v1/cursos` | Listar/criar cursos (valida pré-requisito) |
| GET/PATCH/DELETE | `/api/v1/cursos/{id}` | Obter/atualizar/excluir curso |
| GET | `/api/v1/cursos/{id}/arvore` | Árvore aninhada: curso → módulos → unidades |
| GET/POST | `/api/v1/cursos/{id}/modulos` | Listar/criar módulos |
| PATCH/DELETE | `/api/v1/cursos/modulos/{id}` | Atualizar/excluir módulo |
| PATCH | `/api/v1/cursos/modulos/reorder` | Reordenar módulos em lote |
| GET | `/api/v1/cursos/modulos/{modulo_id}/unidades` | Listar unidades |
| POST/PATCH/DELETE | `/api/v1/cursos/unidades/{id}` | CRUD de unidades |
| PATCH | `/api/v1/cursos/unidades/reorder` | Reordenar unidades em lote |
| GET/POST | `/api/v1/cursos/{id}/aulas` | Listar/criar aulas síncronas |
| PATCH/DELETE | `/api/v1/cursos/aulas/{id}` | Atualizar/excluir aula |
| GET | `/api/v1/cursos/aulas/proximas` | Próximas aulas do usuário logado |
| GET/POST | `/api/v1/cursos/{id}/chat` | Histórico (paginado) / enviar mensagem |
| GET | `/api/v1/cursos/{id}/chat/stream` | SSE — mensagens em tempo real (event-stream) |
| POST | `/api/v1/cursos/inscricoes` | Inscrever (valida pré-requisito concluído, 403 se não) |

**Chat:** Contínuo por curso (estilo WhatsApp). 1 tabela `mensagens_curso`. Histórico completo no PostgreSQL. SSE pra tempo real — conexão HTTP aberta, servidor empurra mensagens novas instantaneamente, cliente reconecta automático.

**Armazenamento:** PDFs, vídeos e materiais ficam em storage externo (S3). O banco guarda só a URL em `conteudo_url TEXT`. Upload é implementação futura.

**XR:** `url_externa TEXT` na Unidade redireciona para plataforma externa do grupo XR.

### Domínios Funcionais (CRUD base)

| Prefixo | Domínio |
|---------|---------|
| `/api/v1/trilhas` | Trilhas de aprendizagem |
| `/api/v1/conteudos` | Conteúdos e materiais complementares |
| `/api/v1/avaliacoes` | Avaliações, questões, alternativas, respostas, resultados |
| `/api/v1/gamificacao` | XP, badges, missões, streaks, leaderboard |
| `/api/v1/sessoes` | Sessões ao vivo e presença |
| `/api/v1/comunicacao` | Chat e fórum |
| `/api/v1/certificados` | Modelos e emissão de certificados |
| `/api/v1/dashboard` | Analytics e métricas |

## Arquitetura

```
app/
├── api/           # FastAPI route modules (1 por domínio)
├── models/        # SQLAlchemy models (schema lms)
├── schemas/       # Pydantic v2 schemas
├── services/      # Lógica de negócio
├── config.py      # Settings via .env
├── database.py    # Async engine + session factory
└── main.py        # Entrypoint + lifespan
```

## Controle de Acesso (RBAC)

**6 perfis** com permissões granulares seeded no startup:

| Perfil | Acesso |
|--------|--------|
| `administrador_geral` | Todas as permissões (23) |
| `administrador` | Quase todas (mesmo escopo do geral) |
| `instrutor` | Criar/editar avaliações, comentários, cursos + sandbox |
| `auditor` | Apenas visualização de relatórios/dashboards |
| `gestor` | Criar subordinados, visualizar relatórios, **sem** criar avaliações/comentários |
| `participante` | Inscrever-se em cursos, responder avaliações, visualizar |

Uso em endpoints:
```python
from app.services.rbac import Permissoes
from app.api.deps import require_permissao

@router.post("/avaliacoes")
async def criar_avaliacao(
    ...,
    _: Usuario = Depends(require_permissao(Permissoes.AVALIACAO_CRIAR)),
):
```

## Fluxo de Credenciamento

1. Usuário registra com perfil → solicitação **pendente** (usuário inativo)
2. Superior hierárquico lista pendentes → aprova/rejeita
3. Usuário aprovado vira **ativo** com perfil atribuído
4. Middleware `require_credenciamento` bloqueia não aprovados

Hierarquia: `admin_geral > admin > instrutor > gestor > participante`

## Perfis Públicos

- `/health` → `{"status": "ok"}`
- `/docs` → Swagger UI
- `/redoc` → ReDoc

## Deploy (fly.io)

```bash
fly launch
fly postgres create --name lms-idesp-db --region gru
fly postgres attach lms-idesp-db
fly secrets set SECRET_KEY="sua-chave-secreta"
fly deploy
```

CI/CD em `.github/workflows/`: `ci.yml` (valida imports) + `deploy.yml` (fly deploy em push para `main`).

## Modelo de Dados

29 tabelas no schema `lms`, organizadas em 10 domínios.
Veja `scripts/init_db.sql` para DDL completo, extensões (`pgcrypto`, `citext`), seeds e índices.

## Progresso

**23/72 tarefas do roadmap concluídas (31.9%).** US-01 (fundação) ✅, US-02 (credenciamento) ✅, US-03 (RBAC) ✅, US-04 (trilhas) ✅, US-05 (cursos avançado) ✅.
