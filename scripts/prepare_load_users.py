"""Registra em lote os usuarios de carga para o teste de 10k (T-18.2).

Uso:
    python scripts/prepare_load_users.py --creds load_creds.json \
        --api https://api-treinamento-dev.ge21gt.cloud

O que faz:
    1. Lê o arquivo de credenciais gerado por `python scripts/locustfile.py --generate`.
    2. Registra cada email no endpoint /api/v1/auth/registro (aceite LGPD).
    3. Aprova os usuários (status_credenciamento -> aprovado) via admin, para que
       possam logar durante o teste. Requer um token de admin no arquivo .env
       (ADMIN_TOKEN) ou via --admin-token.

Nota: o registro cria solicitacao pendente; o locust precisa de contas APROVADAS
para logar. Use o token de um administrador_geral para aprovar em lote.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

API = "https://api-treinamento-dev.ge21gt.cloud"


async def registrar(creds: list[dict], client: httpx.AsyncClient) -> tuple[int, int]:
    ok = 0
    falhas = 0
    for cred in creds:
        r = await client.post(
            f"{API}/api/v1/auth/registro",
            json={
                "nome_completo": "Carga Load",
                "email": cred["email"],
                "senha": cred["senha"],
                "aceite_lgpd": True,
            },
        )
        if r.status_code in (201, 409):  # 409 = ja existe (idempotente)
            ok += 1
        else:
            falhas += 1
            print(f"falha registro {cred['email']}: {r.status_code} {r.text[:120]}")
    return ok, falhas


async def aprovar(creds: list[dict], client: httpx.AsyncClient) -> int:
    """Aprova os usuarios recém-registrados (exige token admin no header).

    Fluxo: cada registro retorna a solicitacao pendente; aprova via
    POST /credenciamento/solicitacoes/{id}/aprovar.
    """
    aprovados = 0
    for cred in creds:
        r = await client.post(
            f"{API}/api/v1/auth/registro",
            json={
                "nome_completo": "Carga Load",
                "email": cred["email"],
                "senha": cred["senha"],
                "aceite_lgpd": True,
            },
        )
        if r.status_code not in (201, 409):
            continue
        data = r.json()
        solicitacao_id = data.get("solicitacao_id")
        if not solicitacao_id:
            continue
        r2 = await client.post(
            f"{API}/api/v1/credenciamento/solicitacoes/{solicitacao_id}/aprovar",
            json={"observacao": "carga"},
        )
        if r2.status_code == 200:
            aprovados += 1
    return aprovados


async def main(creds_path: str, admin_token: str | None) -> None:
    creds = json.loads(Path(creds_path).read_text())
    print(f"Registrando e aprovando {len(creds)} usuarios em {API} ...")
    headers = {}
    if admin_token:
        headers["Authorization"] = f"Bearer {admin_token}"
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        ok, falhas = await registrar(creds, client)
        print(f"Registro: {ok} ok, {falhas} falhas")
        if admin_token:
            n = await aprovar(creds, client)
            print(f"Aprovados: {n}")
        else:
            print("ADMIN_TOKEN ausente — aprovacao pulada. As contas ficam pendentes e o locust nao loga.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--creds", default="load_creds.json")
    parser.add_argument("--api", default=API)
    parser.add_argument("--admin-token", default=None)
    args = parser.parse_args()
    API = args.api
    asyncio.run(main(args.creds, args.admin_token or None))