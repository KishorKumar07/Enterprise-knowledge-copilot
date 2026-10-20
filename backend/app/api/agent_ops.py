"""Read-only views over the agent_runs/agent_steps audit trail (see
app/agents/tracing.py) — the in-product complement to the Phoenix trace UI
and Grafana dashboards, scoped to the current user's organization.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.agent_run import AgentRun
from app.models.user import User
from app.schemas.agent_ops import AgentOpsStats, AgentRunDetailOut, AgentRunOut

router = APIRouter(prefix="/api/admin/agent-runs", tags=["agent-ops"])


@router.get("", response_model=list[AgentRunOut])
async def list_agent_runs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentRun]:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.organization_id == current_user.organization_id)
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.get("/stats", response_model=AgentOpsStats)
async def get_agent_ops_stats(
    window_minutes: int = Query(default=60, ge=1, le=10080),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentOpsStats:
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    result = await db.execute(
        select(
            func.count(AgentRun.id),
            func.count(AgentRun.id).filter(AgentRun.status == "error"),
            func.avg(AgentRun.latency_ms),
            func.percentile_cont(0.95).within_group(AgentRun.latency_ms),
        ).where(AgentRun.organization_id == current_user.organization_id, AgentRun.started_at >= since)
    )
    total_runs, error_count, avg_latency_ms, p95_latency_ms = result.one()

    return AgentOpsStats(
        window_minutes=window_minutes,
        total_runs=total_runs or 0,
        error_count=error_count or 0,
        error_rate=(error_count / total_runs) if total_runs else 0.0,
        avg_latency_ms=float(avg_latency_ms) if avg_latency_ms is not None else None,
        p95_latency_ms=float(p95_latency_ms) if p95_latency_ms is not None else None,
    )


@router.get("/{run_id}", response_model=AgentRunDetailOut)
async def get_agent_run(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRun:
    result = await db.execute(
        select(AgentRun).options(selectinload(AgentRun.steps)).where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None or run.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found.")
    return run
