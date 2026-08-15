from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.connectors import google_drive
from app.core.config import get_settings
from app.core.database import get_db
from app.core.encryption import encrypt_value
from app.ingestion.google_drive_ingestion import run_google_drive_sync
from app.models.connection import Connection
from app.models.knowledge_source import KnowledgeSource
from app.models.sync_job import SyncJob
from app.models.user import User
from app.schemas.sources import (
    ConnectionStatusOut,
    DriveFolderOut,
    KnowledgeSourceOut,
    SelectFoldersRequest,
    SyncJobOut,
)
from app.services.connection_tokens import ConnectionUnavailableError, get_valid_google_access_token
from app.services.oauth_state import create_oauth_state, verify_oauth_state

router = APIRouter(prefix="/api/sources/google-drive", tags=["google-drive"])
settings = get_settings()

PROVIDER = "google_drive"


async def _get_connection(db: AsyncSession, organization_id: UUID) -> Connection | None:
    result = await db.execute(
        select(Connection).where(
            Connection.organization_id == organization_id,
            Connection.provider == PROVIDER,
            Connection.status != "disconnected",
        )
    )
    return result.scalar_one_or_none()


@router.get("/authorize")
async def authorize(current_user: User = Depends(get_current_user)) -> RedirectResponse:
    if not google_drive.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Drive integration is not configured yet.",
        )
    state = create_oauth_state(current_user.id, PROVIDER)
    return RedirectResponse(google_drive.build_authorize_url(state))


@router.get("/callback")
async def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    redirect_base = f"{settings.frontend_origin}/app/sources"

    if error or not code or not state:
        return RedirectResponse(f"{redirect_base}?google_drive=denied")

    user_id = verify_oauth_state(state, PROVIDER)
    if not user_id:
        return RedirectResponse(f"{redirect_base}?google_drive=error")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return RedirectResponse(f"{redirect_base}?google_drive=error")

    try:
        tokens = await google_drive.exchange_code_for_tokens(code)
        email = await google_drive.get_account_email(tokens.access_token)
    except google_drive.GoogleDriveError:
        return RedirectResponse(f"{redirect_base}?google_drive=error")

    connection = await _get_connection(db, user.organization_id)
    if connection is None:
        connection = Connection(organization_id=user.organization_id, provider=PROVIDER)
        db.add(connection)

    connection.status = "connected"
    connection.account_label = email
    connection.encrypted_access_token = encrypt_value(tokens.access_token)
    connection.encrypted_refresh_token = (
        encrypt_value(tokens.refresh_token) if tokens.refresh_token else connection.encrypted_refresh_token
    )
    connection.token_expires_at = tokens.expires_at
    connection.scopes = tokens.scope
    connection.last_error = None

    await db.commit()
    return RedirectResponse(f"{redirect_base}?google_drive=connected")


@router.get("", response_model=ConnectionStatusOut)
async def get_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConnectionStatusOut:
    connection = await _get_connection(db, current_user.organization_id)
    if connection is None:
        return ConnectionStatusOut(connected=False, configured=google_drive.is_configured())

    sources_result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.organization_id == current_user.organization_id,
            KnowledgeSource.connection_id == connection.id,
        )
    )
    sources = sources_result.scalars().all()

    job_result = await db.execute(
        select(SyncJob)
        .where(SyncJob.connection_id == connection.id, SyncJob.status.in_(["queued", "running"]))
        .order_by(SyncJob.started_at.desc())
        .limit(1)
    )
    active_job = job_result.scalar_one_or_none()

    return ConnectionStatusOut(
        connected=connection.status == "connected",
        configured=True,
        status=connection.status,
        account_label=connection.account_label,
        last_error=connection.last_error,
        sources=[KnowledgeSourceOut.model_validate(s) for s in sources],
        active_sync_job_id=active_job.id if active_job else None,
    )


@router.get("/folders", response_model=list[DriveFolderOut])
async def list_folders(
    parent_id: str = Query(default="root"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DriveFolderOut]:
    connection = await _get_connection(db, current_user.organization_id)
    if connection is None or connection.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Drive is not connected.",
        )

    try:
        access_token = await get_valid_google_access_token(db, connection)
        folders = await google_drive.list_folders(access_token, parent_id)
    except ConnectionUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except google_drive.GoogleDriveError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return [DriveFolderOut(id=f.id, name=f.name, parent_id=f.parent_id) for f in folders]


@router.post("/folders", response_model=list[KnowledgeSourceOut])
async def select_folders(
    payload: SelectFoldersRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeSourceOut]:
    connection = await _get_connection(db, current_user.organization_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Drive is not connected.")

    existing_result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.organization_id == current_user.organization_id,
            KnowledgeSource.connection_id == connection.id,
        )
    )
    existing = {s.external_id: s for s in existing_result.scalars().all()}
    selected_ids = {f.id for f in payload.folders}

    for external_id, source in existing.items():
        if external_id not in selected_ids:
            await db.delete(source)

    for folder in payload.folders:
        if folder.id in existing:
            existing[folder.id].name = folder.name
            existing[folder.id].path = folder.path
        else:
            db.add(
                KnowledgeSource(
                    organization_id=current_user.organization_id,
                    connection_id=connection.id,
                    provider=PROVIDER,
                    type="folder",
                    external_id=folder.id,
                    name=folder.name,
                    path=folder.path,
                )
            )

    await db.commit()

    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.organization_id == current_user.organization_id,
            KnowledgeSource.connection_id == connection.id,
        )
    )
    return [KnowledgeSourceOut.model_validate(s) for s in result.scalars().all()]


@router.post("/sync", response_model=SyncJobOut, status_code=status.HTTP_201_CREATED)
async def start_sync(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncJob:
    connection = await _get_connection(db, current_user.organization_id)
    if connection is None or connection.status != "connected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Drive is not connected.")

    sources_result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.connection_id == connection.id, KnowledgeSource.enabled.is_(True)
        )
    )
    if not sources_result.scalars().all():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one folder before syncing.",
        )

    job = SyncJob(
        organization_id=current_user.organization_id,
        connection_id=connection.id,
        provider=PROVIDER,
        status="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(
        run_google_drive_sync, current_user.organization_id, connection.id, job.id
    )

    return job


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    connection = await _get_connection(db, current_user.organization_id)
    if connection:
        await db.delete(connection)
        await db.commit()
