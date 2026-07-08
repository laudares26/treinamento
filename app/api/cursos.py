import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.curso import AulaSincrona, Curso, Inscricao, MensagemCurso, Modulo, ProgressoUnidade, Unidade
from app.schemas.curso import (
    AulaSincronaCreate, AulaSincronaRead, AulaSincronaUpdate,
    CursoCreate, CursoRead, CursoUpdate,
    CursoArvoreRead, ModuloArvoreRead, CursoArvoreItem,
    InscricaoCreate, InscricaoRead,
    MensagemCursoCreate, MensagemCursoRead,
    ModuloCreate, ModuloRead, ModuloUpdate,
    ProgressoUnidadeCreate, ProgressoUnidadeRead, ProgressoUnidadeUpdate,
    ReorderItem,
    UnidadeCreate, UnidadeRead, UnidadeUpdate,
)
from app.models.usuario import Usuario
from app.schemas.curso import (
    AulaSincronaCreate, AulaSincronaRead, AulaSincronaUpdate,
    CursoCreate, CursoRead, CursoUpdate,
    CursoArvoreRead, ModuloArvoreRead, CursoArvoreItem,
    InscricaoCreate, InscricaoRead,
    ModuloCreate, ModuloRead, ModuloUpdate,
    ProgressoUnidadeCreate, ProgressoUnidadeRead, ProgressoUnidadeUpdate,
    ReorderItem,
    UnidadeCreate, UnidadeRead, UnidadeUpdate,
)

router = APIRouter(prefix="/cursos", tags=["Cursos"])


# --- Cursos ---

@router.get("", response_model=list[CursoRead])
async def listar_cursos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    trilha_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    stmt = select(Curso)
    if trilha_id is not None:
        stmt = stmt.where(Curso.trilha_id == trilha_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("", response_model=CursoRead, status_code=status.HTTP_201_CREATED)
async def criar_curso(
    payload: CursoCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    if payload.pre_requisito_curso_id:
        result = await db.execute(select(Curso).where(Curso.id == payload.pre_requisito_curso_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Curso pre-requisito nao encontrado")
    curso = Curso(**payload.model_dump())
    db.add(curso)
    await db.commit()
    await db.refresh(curso)
    return curso


@router.get("/{curso_id}", response_model=CursoRead)
async def obter_curso(
    curso_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Curso).where(Curso.id == curso_id))
    curso = result.scalar_one_or_none()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso nao encontrado")
    return curso


@router.patch("/{curso_id}", response_model=CursoRead)
async def atualizar_curso(
    curso_id: int,
    payload: CursoUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Curso).where(Curso.id == curso_id))
    curso = result.scalar_one_or_none()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso nao encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(curso, field, value)
    await db.commit()
    await db.refresh(curso)
    return curso


@router.delete("/{curso_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_curso(
    curso_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Curso).where(Curso.id == curso_id))
    curso = result.scalar_one_or_none()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso nao encontrado")
    await db.delete(curso)
    await db.commit()


@router.get("/{curso_id}/arvore", response_model=CursoArvoreRead)
async def arvore_curso(
    curso_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(Curso).where(Curso.id == curso_id)
        .options(selectinload(Curso.modulos).selectinload(Modulo.unidades))
    )
    curso = result.scalar_one_or_none()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso nao encontrado")
    modulos = [
        ModuloArvoreRead(
            id=m.id, titulo=m.titulo, ordem=m.ordem,
            unidades=[
                CursoArvoreItem(
                    id=u.id, titulo=u.titulo, tipo=u.tipo, ordem=u.ordem,
                    conteudo_url=u.conteudo_url, url_externa=u.url_externa,
                ) for u in m.unidades
            ],
        ) for m in sorted(curso.modulos, key=lambda x: x.ordem)
    ]
    return CursoArvoreRead(id=curso.id, titulo=curso.titulo, modulos=modulos)


# --- Modulos ---

@router.get("/{curso_id}/modulos", response_model=list[ModuloRead])
async def listar_modulos(
    curso_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Modulo).where(Modulo.curso_id == curso_id).order_by(Modulo.ordem))
    return result.scalars().all()


@router.post("/modulos", response_model=ModuloRead, status_code=status.HTTP_201_CREATED)
async def criar_modulo(
    payload: ModuloCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    modulo = Modulo(**payload.model_dump())
    db.add(modulo)
    await db.commit()
    await db.refresh(modulo)
    return modulo


@router.patch("/modulos/{modulo_id}", response_model=ModuloRead)
async def atualizar_modulo(
    modulo_id: int,
    payload: ModuloUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Modulo).where(Modulo.id == modulo_id))
    modulo = result.scalar_one_or_none()
    if not modulo:
        raise HTTPException(status_code=404, detail="Modulo nao encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(modulo, field, value)
    await db.commit()
    await db.refresh(modulo)
    return modulo


@router.delete("/modulos/{modulo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_modulo(
    modulo_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Modulo).where(Modulo.id == modulo_id))
    modulo = result.scalar_one_or_none()
    if not modulo:
        raise HTTPException(status_code=404, detail="Modulo nao encontrado")
    await db.delete(modulo)
    await db.commit()


@router.patch("/modulos/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reordenar_modulos(
    payload: list[ReorderItem],
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    ids = [item.id for item in payload]
    result = await db.execute(select(Modulo).where(Modulo.id.in_(ids)))
    modulos = {m.id: m for m in result.scalars().all()}
    for item in payload:
        if item.id in modulos:
            modulos[item.id].ordem = item.ordem
    await db.commit()


# --- Unidades ---

@router.get("/modulos/{modulo_id}/unidades", response_model=list[UnidadeRead])
async def listar_unidades(
    modulo_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Unidade).where(Unidade.modulo_id == modulo_id).order_by(Unidade.ordem))
    return result.scalars().all()


@router.post("/unidades", response_model=UnidadeRead, status_code=status.HTTP_201_CREATED)
async def criar_unidade(
    payload: UnidadeCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    unidade = Unidade(**payload.model_dump())
    db.add(unidade)
    await db.commit()
    await db.refresh(unidade)
    return unidade


@router.patch("/unidades/{unidade_id}", response_model=UnidadeRead)
async def atualizar_unidade(
    unidade_id: int,
    payload: UnidadeUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Unidade).where(Unidade.id == unidade_id))
    unidade = result.scalar_one_or_none()
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade nao encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(unidade, field, value)
    await db.commit()
    await db.refresh(unidade)
    return unidade


@router.delete("/unidades/{unidade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_unidade(
    unidade_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Unidade).where(Unidade.id == unidade_id))
    unidade = result.scalar_one_or_none()
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade nao encontrada")
    await db.delete(unidade)
    await db.commit()


@router.patch("/unidades/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reordenar_unidades(
    payload: list[ReorderItem],
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    ids = [item.id for item in payload]
    result = await db.execute(select(Unidade).where(Unidade.id.in_(ids)))
    unidades = {u.id: u for u in result.scalars().all()}
    for item in payload:
        if item.id in unidades:
            unidades[item.id].ordem = item.ordem
    await db.commit()


# --- Aulas Síncronas ---

@router.get("/{curso_id}/aulas", response_model=list[AulaSincronaRead])
async def listar_aulas(
    curso_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(AulaSincrona).where(AulaSincrona.curso_id == curso_id).order_by(AulaSincrona.data_hora)
    )
    return result.scalars().all()


@router.post("/{curso_id}/aulas", response_model=AulaSincronaRead, status_code=status.HTTP_201_CREATED)
async def criar_aula(
    curso_id: int,
    payload: AulaSincronaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    aula = AulaSincrona(**payload.model_dump(), criado_por=current_user.id)
    db.add(aula)
    await db.commit()
    await db.refresh(aula)
    return aula


@router.get("/aulas/proximas", response_model=list[AulaSincronaRead])
async def aulas_proximas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from datetime import datetime, timezone
    result = await db.execute(
        select(AulaSincrona)
        .where(AulaSincrona.data_hora >= datetime.now(timezone.utc))
        .order_by(AulaSincrona.data_hora)
        .limit(20)
    )
    return result.scalars().all()


@router.patch("/aulas/{aula_id}", response_model=AulaSincronaRead)
async def atualizar_aula(
    aula_id: int,
    payload: AulaSincronaUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(AulaSincrona).where(AulaSincrona.id == aula_id))
    aula = result.scalar_one_or_none()
    if not aula:
        raise HTTPException(status_code=404, detail="Aula nao encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(aula, field, value)
    await db.commit()
    await db.refresh(aula)
    return aula


@router.delete("/aulas/{aula_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_aula(
    aula_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(AulaSincrona).where(AulaSincrona.id == aula_id))
    aula = result.scalar_one_or_none()
    if not aula:
        raise HTTPException(status_code=404, detail="Aula nao encontrada")
    await db.delete(aula)
    await db.commit()


# --- Chat SSE ---

@router.get("/{curso_id}/chat/stream")
async def stream_chat(
    curso_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    from fastapi.responses import StreamingResponse
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

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --- Chat ---

@router.get("/{curso_id}/chat", response_model=list[dict])
async def listar_chat(
    curso_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    from app.models.curso import MensagemCurso
    result = await db.execute(
        select(MensagemCurso)
        .where(MensagemCurso.curso_id == curso_id)
        .order_by(MensagemCurso.criado_em.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    msgs = result.scalars().all()
    msgs.reverse()
    return [{"id": m.id, "usuario_id": str(m.usuario_id), "texto": m.texto, "criado_em": m.criado_em.isoformat()} for m in msgs]


@router.post("/{curso_id}/chat", status_code=status.HTTP_201_CREATED)
async def enviar_mensagem(
    curso_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.models.curso import MensagemCurso
    texto = payload.get("texto", "").strip()
    if not texto:
        raise HTTPException(status_code=422, detail="Texto nao pode ser vazio")
    if len(texto) > 2000:
        raise HTTPException(status_code=422, detail="Texto muito longo (max 2000)")
    msg = MensagemCurso(curso_id=curso_id, usuario_id=current_user.id, texto=texto)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return {"id": msg.id, "usuario_id": str(msg.usuario_id), "texto": msg.texto, "criado_em": msg.criado_em.isoformat()}


# --- Inscricoes ---

@router.post("/inscricoes", response_model=InscricaoRead, status_code=status.HTTP_201_CREATED)
async def inscrever(
    payload: InscricaoCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    curso = await db.execute(select(Curso).where(Curso.id == payload.curso_id))
    curso = curso.scalar_one_or_none()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso nao encontrado")
    if curso.pre_requisito_curso_id:
        prereq = await db.execute(
            select(Inscricao).where(
                Inscricao.curso_id == curso.pre_requisito_curso_id,
                Inscricao.usuario_id == payload.usuario_id,
                Inscricao.status == "concluido",
            )
        )
        if not prereq.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Pre-requisito nao concluido")
    inscricao = Inscricao(**payload.model_dump())
    db.add(inscricao)
    await db.commit()
    await db.refresh(inscricao)
    return inscricao


@router.get("/inscricoes/{usuario_id}", response_model=list[InscricaoRead])
async def listar_inscricoes_usuario(
    usuario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Inscricao).where(Inscricao.usuario_id == usuario_id))
    return result.scalars().all()


# --- Progresso ---

@router.post("/progresso", response_model=ProgressoUnidadeRead, status_code=status.HTTP_201_CREATED)
async def criar_progresso(
    payload: ProgressoUnidadeCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    progresso = ProgressoUnidade(**payload.model_dump())
    db.add(progresso)
    await db.commit()
    await db.refresh(progresso)
    return progresso


@router.patch("/progresso/{progresso_id}", response_model=ProgressoUnidadeRead)
async def atualizar_progresso(
    progresso_id: int,
    payload: ProgressoUnidadeUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(ProgressoUnidade).where(ProgressoUnidade.id == progresso_id))
    progresso = result.scalar_one_or_none()
    if not progresso:
        raise HTTPException(status_code=404, detail="Progresso nao encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(progresso, field, value)
    await db.commit()
    await db.refresh(progresso)
    return progresso
