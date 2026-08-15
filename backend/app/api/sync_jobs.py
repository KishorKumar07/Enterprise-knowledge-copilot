from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.sync_job import SyncJob
from app.models.user import User
from app.schemas.sources import SyncJobOut

router = APIRouter(prefix="/api/sync-jobs", tags=["sync-jobs"])


@router.get("/{job_id}", response_model=SyncJobOut)
async def get_sync_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncJob:
    job = await db.get(SyncJob, job_id)
    if job is None or job.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync job not found.")
    return job
