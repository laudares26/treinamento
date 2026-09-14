# US-18 — T-18.1: Relatório de Aceitação (Testes de Integração)

**Sprint 6 · Branch:** `feature/us-18`
**Data:** 11/09/2026
**Contexto:** Suíte completa de testes rodada contra o banco PostgreSQL de teste (`TEST_DATABASE_URL`, database-2).

---

## Resultado Geral

| Métrica | Valor |
|---|---|
| Arquivos de teste | 35 |
| Testes executados | ~305 |
| Falhas pendentes | 0 |
| Skips | 0 (após os fixes desta sprint) |

## Resultado por arquivo

### Autenticação, RBAC e infraestrutura

| Arquivo | Resultado |
|---|---|
| `test_auth.py` | 11/11 ✅ |
| `test_rbac.py` | 10/10 ✅ |
| `test_imports.py` + `test_health.py` | 9/9 ✅ |
| `test_boot.py` | 3/3 ✅ |
| `test_health.py` (deteccao de schema atrasado) | ✅ |

### Cursos, trilhas, avaliações

| Arquivo | Resultado |
|---|---|
| `test_cursos.py` | 13/13 ✅ |
| `test_trilhas.py` | 14/14 ✅ |
| `test_avaliacoes.py` | 22/22 ✅ |
| `test_us05.py` | 10/10 ✅ |
| `test_us07.py` | 15/15 ✅ |
| `test_us08_avaliacoes.py` | 7/7 ✅ |
| `test_issues_0708_01.py` | 9/9 ✅ |

### Conteúdos, upload, SCORM

| Arquivo | Resultado |
|---|---|
| `test_us06.py` | 25/25 ✅ |
| `test_chunked_upload.py` | 3/3 ✅ |

### Aulas ao vivo, sessões, presença, chat, fórum

| Arquivo | Resultado |
|---|---|
| `test_us11.py` | 12/12 ✅ |
| `test_us11_fixes.py` | 15/15 ✅ |
| `test_us12.py` | 12/12 ✅ |
| `test_us13.py` | REST ✅ + WS ✅ |
| `test_us14.py` | 25/25 ✅ |
| `test_sessoes.py` | 8/8 ✅ |
| `test_comunicacao.py` | 12/12 ✅ |

### Gamificação, dashboards, certificados, auditoria

| Arquivo | Resultado |
|---|---|
| `test_gamificacao.py` | 34/34 ✅ |
| `test_gamificacao_engine.py` | 16/16 ✅ |
| `test_dashboard.py` | 14/14 ✅ |
| `test_certificados.py` | 7/7 ✅ |
| `test_us15.py` | 8/8 ✅ (após fix) |
| `test_us16.py` | 16/16 ✅ |
| `test_us17.py` | 7/7 ✅ |
| `test_us28_notificacoes.py` | 7/7 ✅ |

### Issues corrigidas anteriormente (regressão)

| Arquivo | Resultado |
|---|---|
| `test_bug_fix_18.py` | 2/2 ✅ |
| `test_issue21_perfis.py` | 6/6 ✅ |
| `test_issue22_validacao.py` | 6/6 ✅ |
| `test_issue23_telefone.py` | 5/5 ✅ |
| `test_issue41_cascade_delete.py` | 4/4 ✅ |
| `test_issue43_filtro_perfil.py` | 4/4 ✅ |

---

## Achados corrigidos nesta sprint (T-18.6)

### 1. WebSocket: testes não executavam (conflito de loop)

- **Sintoma:** todos os testes de WS do `test_us13.py` e `test_us11_fixes.py` falhavam com `RuntimeError: attached to a different loop`.
- **Causa raiz:** `TestClient(app)` (síncrono) rodava o `lifespan`/`engine` global numa thread/loop diferente do pytest-asyncio.
- **Correção:** novo fixture `ws_client` em `tests/conftest.py` — cliente WebSocket ASGI async que roda a app no mesmo loop do pytest (sem thread, sem lifespan, sem cruzar loops). Suporta query string e subprotocolo para o token.
- **Resultado:** 13 testes WS passam juntos, de forma determinística (antes: 0 executavam).

### 2. Validação pública de certificado não devolvia o hash

- **Sintoma:** `test_us15.py::test_validar_publico_por_hash` falhava com `KeyError: 'hash_validacao'`.
- **Causa raiz:** `GET /certificados/validar/{hash}` usava o schema `CertificadoPublicoRead`, que não incluía `hash_validacao` na resposta.
- **Correção:** adicionado `hash_validacao: str` ao schema (`app/schemas/certificado.py`) e preenchido no endpoint (`app/api/certificados.py`).
- **Resultado:** `test_us15.py` 8/8.

---

## Notas operacionais

- **Setup do banco é caro:** cada arquivo de teste reexecuta o `db_setup` session-scoped (create_all + seeds) — cada arquivo leva ~2-10 min. A suíte completa leva ~1h40. Recomenda-se rodar arquivo a arquivo ou em blocos por domínio.
- **Flakiness de lote:** arquivos grandes (muitos testes com `client`) podem travar por acúmulo de engines quando rodados de uma vez; rodar em blocos menores resolve. Os testes WS, após o fix, são determinísticos.
- **Ruff:** os arquivos de teste têm violações **pré-existentes** (E402 imports de módulo, F401 imports não usados, E501 linhas longas). O código novo desta sprint está 100% limpo.

## Conclusão

Todos os fluxos de integração entre módulos funcionam em conjunto: autenticação → RBAC → cursos → trilhas → avaliações → upload → aulas ao vivo → chat → fórum → gamificação → dashboards → certificados → auditoria → notificações. Sem falhas pendentes.
