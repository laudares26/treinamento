"""Load test for LMS IDE-SP API (T-18.2 — simula 10.000+ usuarios simultaneos).

Uso — modo Web UI (interativo):
    pip install locust
    locust -f scripts/locustfile.py --host=https://api-treinamento-dev.ge21gt.cloud
    # Abra http://localhost:8089 e configure usuarios/spawn rate.

Uso — modo headless (CI/automacao, ramp-up ate 10k):
    locust -f scripts/locustfile.py --host=https://api-treinamento-dev.ge21gt.cloud \
        --headless -u 10000 -r 50 --run-time 30m \
        --csv=results/locust-10k

Requisitos:
    - Usuarios PRE-criados (opcional): gere com scripts/prepare_load_users.py e
      passe a lista com --credentials-file. Sem arquivo, cada usuario registra
      a propria conta no on_start (mais pesado, nao recomendado para 10k).
    - O endpoint /api/v1/cursos/{id}/consumo precisa de inscricao; o cenario
      `consumir_curso` usa o curso 1 (ajuste via --env CURSO_ID ou edite abaixo).

Metricas coletadas por padrao (locust): RPS, latencia media, p50/p95/p99,
numero de falhas. Exporte com --csv para analise.
"""

import argparse
import json
import os
import random
import uuid
from pathlib import Path

from locust import HttpUser, between, task

# Curso usado no cenario de consumo (pode sobrescrever via env).
CURSO_ID = int(os.getenv("CURSO_ID", "1"))

# Conjunto de cursos/trilhas/avaliacoes existentes no ambiente (para listagem
# realista). Se vazio, usa endpoints genericos.
CURSOS_CATALOGO = [int(x) for x in os.getenv("CURSOS_CATALOGO", "").split(",") if x]


def _load_credentials(path: str | None) -> list[dict]:
    """Carrega lista de credenciais {email, senha} de um arquivo JSON/CSV.

    Formato JSON: [{"email": "...", "senha": "..."}, ...]
    Formato CSV: email,senha (uma por linha, cabecalho opcional).
    """
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo de credenciais nao encontrado: {path}")
    creds: list[dict] = []
    if p.suffix.lower() == ".json":
        creds = json.loads(p.read_text())
    else:
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.lower().startswith("email"):
                continue
            email, _, senha = line.partition(",")
            creds.append({"email": email.strip(), "senha": senha.strip()})
    if not creds:
        raise ValueError(f"Arquivo de credenciais vazio: {path}")
    return creds


class LMSUser(HttpUser):
    """Carga de 10k usuarios simulados contra a API do LMS."""

    # Ramp-up de 10k usuarios em ~3-5 min com wait_time entre 1 e 5s por tarefa.
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.email = None
        self.senha = None
        self.token = None
        self.user_id = None
        self.curso_id = CURSO_ID
        self._credenciais_pool: list[dict] | None = None

    def on_start(self):
        """Login (ou registro+login) ao iniciar o usuario simulado."""
        # 1) Tenta usar o pool de credenciais pre-criadas (recomendado p/ 10k).
        pool = self._get_pool()
        if pool:
            cred = random.choice(pool)
            self.email = cred["email"]
            self.senha = cred["senha"]
        else:
            # 2) Sem pool: registra conta nova (pesado; nao use p/ 10k).
            self.email = f"loadtest_{uuid.uuid4().hex[:8]}@test.com"
            self.senha = "Test@123456"
            self.client.post(
                "/api/v1/auth/registro",
                json={
                    "nome_completo": "Load Test User",
                    "email": self.email,
                    "senha": self.senha,
                    "aceite_lgpd": True,
                },
            )
        self._login()

    def _get_pool(self) -> list[dict]:
        if self._credenciais_pool is None:
            path = os.getenv("CREDENTIALS_FILE")
            self._credenciais_pool = _load_credentials(path)
        return self._credenciais_pool

    def _login(self):
        r = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "senha": self.senha},
            name="/api/v1/auth/login",
        )
        if r.status_code == 200:
            data = r.json()
            self.token = data.get("access_token")
            self.user_id = data.get("usuario_id") or data.get("user_id")

    def _auth(self) -> dict:
        """Header de autenticacao (token JWT), se houver."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # ---- Cenarios (peso = probabilidade relativa) ----

    @task(1)
    def login(self):
        """Autenticacao (bcrypt e caro; peso baixo para nao dominar a medicao)."""
        self._login()

    @task(4)
    def listar_cursos(self):
        if not self.token:
            return
        self.client.get("/api/v1/cursos", name="/api/v1/cursos", headers=self._auth())

    @task(2)
    def listar_trilhas(self):
        if not self.token:
            return
        self.client.get("/api/v1/trilhas", name="/api/v1/trilhas", headers=self._auth())

    @task(2)
    def meu_progresso(self):
        if self.token:
            self.client.get("/api/v1/dashboard/meu-progresso", name="/api/v1/dashboard/meu-progresso", headers=self._auth())

    @task(1)
    def perfil(self):
        if self.token:
            self.client.get("/api/v1/usuarios/me", name="/api/v1/usuarios/me", headers=self._auth())

    @task(2)
    def listar_avaliacoes(self):
        if not self.token:
            return
        self.client.get("/api/v1/avaliacoes", name="/api/v1/avaliacoes", headers=self._auth())

    @task(1)
    def gamificacao_niveis(self):
        if not self.token:
            return
        self.client.get("/api/v1/gamificacao/niveis", name="/api/v1/gamificacao/niveis", headers=self._auth())

    @task(1)
    def listar_sessoes(self):
        if not self.token:
            return
        self.client.get("/api/v1/sessoes", name="/api/v1/sessoes", headers=self._auth())

    @task(2)
    def consumir_curso(self):
        """Fluxo real de consumo: arvore + consumo de um curso (T-18.1 E2E)."""
        if not self.token:
            return
        self.client.get(f"/api/v1/cursos/{self.curso_id}/arvore", name="/api/v1/cursos/{id}/arvore", headers=self._auth())
        self.client.get(f"/api/v1/cursos/{self.curso_id}/consumo", name="/api/v1/cursos/{id}/consumo", headers=self._auth())

    @task(1)
    def inscrever_e_consultar(self):
        """Inscreve-se em um curso do catalogo e consulta o progresso."""
        if not self.token:
            return
        curso_id = random.choice(CURSOS_CATALOGO) if CURSOS_CATALOGO else self.curso_id
        self.client.post(
            "/api/v1/cursos/inscricoes",
            json={"curso_id": curso_id},
            name="/api/v1/cursos/inscricoes",
            headers=self._auth(),
        )
        self.client.get("/api/v1/cursos/inscricoes/minhas", name="/api/v1/cursos/inscricoes/minhas", headers=self._auth())

    @task(1)
    def certificados_meus(self):
        if self.token:
            self.client.get("/api/v1/certificados/meus", name="/api/v1/certificados/meus", headers=self._auth())

    @task(1)
    def notificacoes(self):
        if self.token:
            self.client.get("/api/v1/notificacoes", name="/api/v1/notificacoes", headers=self._auth())

    def on_stop(self):
        """Limpeza: se registrou conta propria (sem pool), remove no final."""
        if self.user_id and self.token and not self._get_pool():
            self.client.delete(f"/api/v1/usuarios/{self.user_id}", name="/api/v1/usuarios/{id}", headers=self._auth())


def main() -> None:
    """CLI auxiliar para preparar o arquivo de credenciais de carga (10k).

    Uso:
        python scripts/locustfile.py --generate 10000 --output creds.json
    Gera 10k credenciais ficticias (nao cria contas; o script de seed
    scripts/prepare_load_users.py registra-as no ambiente antes do teste).
    """
    parser = argparse.ArgumentParser(description="Prepara credenciais de carga do locust.")
    parser.add_argument("--generate", type=int, help="Quantidade de credenciais a gerar")
    parser.add_argument("--output", default="load_creds.json", help="Arquivo de saida")
    args = parser.parse_args()
    if not args.generate:
        parser.print_help()
        return
    creds = [
        {"email": f"carga_{i:05d}@test.com", "senha": "Test@123456"}
        for i in range(args.generate)
    ]
    Path(args.output).write_text(json.dumps(creds, indent=2))
    print(f"Geradas {len(creds)} credenciais em {args.output}")


if __name__ == "__main__":
    main()