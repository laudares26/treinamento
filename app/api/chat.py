import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.curso import MensagemCurso
from app.models.usuario import Usuario
from app.schemas.curso import MensagemCursoCreate, MensagemCursoRead

router = APIRouter(prefix="/cursos/{curso_id}/chat", tags=["Chat"])


@router.post("", response_model=MensagemCursoRead, status_code=status.HTTP_201_CREATED)
async def enviar_mensagem(
    curso_id: int,
    payload: MensagemCursoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    msg = MensagemCurso(
        curso_id=curso_id,
        usuario_id=current_user.id,
        texto=payload.texto,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


@router.get("", response_model=list[MensagemCursoRead])
async def listar_mensagens(
    curso_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(MensagemCurso)
        .where(MensagemCurso.curso_id == curso_id)
        .order_by(MensagemCurso.criado_em.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    msgs = result.scalars().all()
    msgs.reverse()
    return msgs


@router.get("/stream")
async def stream_mensagens(
    curso_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    last_id = 0

    async def event_generator():
        nonlocal last_id
        while True:
            if await request.is_disconnected():
                break
            result = await db.execute(
                select(MensagemCurso)
                .where(MensagemCurso.curso_id == curso_id, MensagemCurso.id > last_id)
                .order_by(MensagemCurso.criado_em)
            )
            novas = result.scalars().all()
            for msg in novas:
                last_id = msg.id
                data = {
                    "id": msg.id,
                    "usuario_id": str(msg.usuario_id),
                    "texto": msg.texto,
                    "criado_em": msg.criado_em.isoformat(),
                }
                yield f"data: {json.dumps(data)}\n\n"
            import asyncio
            await asyncio.sleep(1)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")
