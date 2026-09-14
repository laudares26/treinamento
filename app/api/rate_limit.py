"""Shared rate limiter instance for the application.

O rate limit pode ser desligado via env `RATE_LIMIT_ENABLED=false` (usado no
teste de carga local, onde o limite por IP invalida a medicao). Em producao
permanece ativo (default `true`).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/day", "50/hour"],
    enabled=settings.RATE_LIMIT_ENABLED,
)