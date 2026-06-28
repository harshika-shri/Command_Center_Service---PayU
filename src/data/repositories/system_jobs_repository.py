from __future__ import annotations

from datetime import date
from typing import cast

from sqlalchemy import select

from src.data.models.postgres.system_jobs import SystemJob
from src.data.repositories.base_repo import BaseRepository

OVERDUE_REFRESH_JOB_NAME = "overdue_refresh"


class SystemJobsRepository(BaseRepository):
    async def get_job_for_update(
        self,
        job_name: str,
    ) -> SystemJob | None:
        result = await self.execute(
            select(
                SystemJob,
            )
            .where(
                SystemJob.job_name == job_name,
            )
            .with_for_update(),
        )

        return cast(SystemJob | None, result.scalar_one_or_none())

    async def update_last_run_date(
        self,
        job: SystemJob,
        run_date: date,
    ) -> None:
        job.last_run_date = run_date
        await self.session.flush()
