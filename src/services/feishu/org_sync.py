"""Organization synchronization service for Feishu data.

This module provides the core business logic for synchronizing department
and employee data from Feishu to the local database.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Set

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Department, Employee
from src.models.sync_log import SyncLog
from src.schemas.feishu import FeishuDepartmentRaw, FeishuUserRaw
from src.schemas.organization import SyncStats
from src.services.feishu.client import FeishuClient

logger = structlog.get_logger()


class OrganizationSyncService:
    """Service for synchronizing organization structure from Feishu.

    Handles both full and incremental synchronization of departments
    and employees with proper transaction management and error handling.

    Example:
        >>> async with AsyncSession(engine) as session:
        ...     service = OrganizationSyncService(feishu_client, session)
        ...     result = await service.full_sync()
        ...     print(f"Created: {result.records_created}")
    """

    def __init__(
        self,
        feishu_client: FeishuClient,
        db_session: AsyncSession,
    ):
        """Initialize sync service.

        Args:
            feishu_client: Configured Feishu API client
            db_session: Database session for persistence
        """
        self._client = feishu_client
        self._session = db_session
        self._logger = logger.bind(component="OrganizationSyncService")

    async def full_sync(self) -> SyncLog:
        """Perform full synchronization of all organization data.

        Fetches all departments and employees from Feishu and
        updates the local database. Marks records not present
        in Feishu as inactive.

        Returns:
            SyncLog with detailed statistics
        """
        self._logger.info("starting_full_sync")

        # Create sync log entry
        sync_log = SyncLog(
            sync_type="full",
            entity_type="all",
            status="in_progress",
        )
        self._session.add(sync_log)
        await self._session.commit()

        try:
            # Sync departments first (employees depend on them)
            dept_stats = await self._sync_all_departments()

            # Then sync employees
            employee_stats = await self._sync_all_employees()

            # Combine statistics
            sync_log.records_fetched = (
                dept_stats.records_fetched + employee_stats.records_fetched
            )
            sync_log.records_created = (
                dept_stats.records_created + employee_stats.records_created
            )
            sync_log.records_updated = (
                dept_stats.records_updated + employee_stats.records_updated
            )
            sync_log.records_deactivated = (
                dept_stats.records_deactivated + employee_stats.records_deactivated
            )

            # Handle departed employees (mark as inactive)
            deactivated = await self._handle_departed_employees()
            sync_log.records_deactivated += deactivated

            sync_log.complete("success")
            self._logger.info(
                "full_sync_completed",
                departments_fetched=dept_stats.records_fetched,
                employees_fetched=employee_stats.records_fetched,
                created=sync_log.records_created,
                updated=sync_log.records_updated,
                deactivated=sync_log.records_deactivated,
            )

        except Exception as e:
            self._logger.exception("full_sync_failed", error=str(e))
            sync_log.complete("failed", error_message=str(e))
            await self._session.commit()
            raise

        await self._session.commit()
        return sync_log

    async def incremental_sync(
        self,
        since: Optional[datetime] = None,
    ) -> SyncLog:
        """Perform incremental synchronization.

        Only fetches and updates records changed since the last sync.
        If no timestamp provided, uses last 24 hours.

        Args:
            since: Timestamp for incremental sync (default: 24h ago)

        Returns:
            SyncLog with detailed statistics
        """
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        self._logger.info("starting_incremental_sync", since=since.isoformat())

        sync_log = SyncLog(
            sync_type="incremental",
            entity_type="all",
            status="in_progress",
        )
        self._session.add(sync_log)
        await self._session.commit()

        try:
            # For incremental sync, we still fetch all and compare timestamps
            # Feishu API doesn't support updated_since filter directly
            dept_stats = await self._sync_all_departments_incremental(since)
            employee_stats = await self._sync_all_employees_incremental(since)

            sync_log.records_fetched = (
                dept_stats.records_fetched + employee_stats.records_fetched
            )
            sync_log.records_created = (
                dept_stats.records_created + employee_stats.records_created
            )
            sync_log.records_updated = (
                dept_stats.records_updated + employee_stats.records_updated
            )
            sync_log.records_deactivated = (
                dept_stats.records_deactivated + employee_stats.records_deactivated
            )

            sync_log.complete("success")
            self._logger.info(
                "incremental_sync_completed",
                departments_fetched=dept_stats.records_fetched,
                employees_fetched=employee_stats.records_fetched,
                created=sync_log.records_created,
                updated=sync_log.records_updated,
            )

        except Exception as e:
            self._logger.exception("incremental_sync_failed", error=str(e))
            sync_log.complete("failed", error_message=str(e))
            await self._session.commit()
            raise

        await self._session.commit()
        return sync_log

    async def _sync_all_departments(self) -> SyncStats:
        """Sync all departments from Feishu.

        Returns:
            Statistics for the sync operation
        """
        stats = SyncStats()

        self._logger.info("fetching_departments")
        feishu_depts = await self._client.list_departments()
        stats.records_fetched = len(feishu_depts)

        self._logger.info("departments_fetched", count=len(feishu_depts))

        # Get existing departments for comparison
        result = await self._session.execute(select(Department))
        existing_depts: List[Department] = result.scalars().all()
        existing_map = {d.feishu_dept_id: d for d in existing_depts}

        # Build parent-child relationships
        # We need to process departments in order (parents before children)
        dept_map = {d.department_id: d for d in feishu_depts}

        # Sort by hierarchy level to ensure parents are processed first
        sorted_depts = self._sort_departments_by_hierarchy(feishu_depts)

        for feishu_dept in sorted_depts:
            await self._upsert_department(feishu_dept, existing_map, stats)

        return stats

    async def _sync_all_departments_incremental(
        self,
        since: datetime,
    ) -> SyncStats:
        """Sync departments changed since timestamp."""
        stats = SyncStats()

        feishu_depts = await self._client.list_departments()
        stats.records_fetched = len(feishu_depts)

        # Get existing departments
        result = await self._session.execute(select(Department))
        existing_depts: List[Department] = result.scalars().all()
        existing_map = {d.feishu_dept_id: d for d in existing_depts}

        # Only process changed departments
        sorted_depts = self._sort_departments_by_hierarchy(feishu_depts)

        for feishu_dept in sorted_depts:
            existing = existing_map.get(feishu_dept.department_id)

            # Check if changed (always process new departments)
            if existing is None or self._department_changed(existing, feishu_dept):
                await self._upsert_department(feishu_dept, existing_map, stats)

        return stats

    async def _sync_all_employees(self) -> SyncStats:
        """Sync all employees from Feishu.

        Returns:
            Statistics for the sync operation
        """
        stats = SyncStats()

        self._logger.info("fetching_employees")
        feishu_users = await self._client.list_users()
        stats.records_fetched = len(feishu_users)

        self._logger.info("employees_fetched", count=len(feishu_users))

        # Get existing employees
        result = await self._session.execute(select(Employee))
        existing_employees: List[Employee] = result.scalars().all()
        existing_map = {e.feishu_user_id: e for e in existing_employees}

        active_user_ids: Set[str] = set()

        for feishu_user in feishu_users:
            active_user_ids.add(feishu_user.user_id)
            await self._upsert_employee(feishu_user, existing_map, stats)

        return stats

    async def _sync_all_employees_incremental(
        self,
        since: datetime,
    ) -> SyncStats:
        """Sync employees changed since timestamp."""
        stats = SyncStats()

        feishu_users = await self._client.list_users()
        stats.records_fetched = len(feishu_users)

        # Get existing employees
        result = await self._session.execute(select(Employee))
        existing_employees: List[Employee] = result.scalars().all()
        existing_map = {e.feishu_user_id: e for e in existing_employees}

        for feishu_user in feishu_users:
            existing = existing_map.get(feishu_user.user_id)

            # Process new or changed employees
            if existing is None or self._employee_changed(existing, feishu_user):
                await self._upsert_employee(feishu_user, existing_map, stats)

        return stats

    async def _upsert_department(
        self,
        feishu_dept: FeishuDepartmentRaw,
        existing_map: dict,
        stats: SyncStats,
    ) -> Department:
        """Insert or update a single department."""
        existing = existing_map.get(feishu_dept.department_id)

        if existing:
            # Update existing
            existing.name = feishu_dept.name
            existing.parent_id = feishu_dept.parent_department_id
            existing.order = feishu_dept.order
            existing.is_active = True  # Reactivate if previously deactivated
            existing.sync_updated_at = datetime.utcnow()
            stats.records_updated += 1
            self._logger.debug("department_updated", dept_id=feishu_dept.department_id)
            return existing
        else:
            # Create new
            dept = Department(
                feishu_dept_id=feishu_dept.department_id,
                name=feishu_dept.name,
                parent_id=feishu_dept.parent_department_id,
                order=feishu_dept.order,
                is_active=True,
                sync_updated_at=datetime.utcnow(),
            )
            self._session.add(dept)
            stats.records_created += 1
            self._logger.debug("department_created", dept_id=feishu_dept.department_id)
            return dept

    async def _upsert_employee(
        self,
        feishu_user: FeishuUserRaw,
        existing_map: dict,
        stats: SyncStats,
    ) -> Employee:
        """Insert or update a single employee."""
        existing = existing_map.get(feishu_user.user_id)

        # Extract avatar URL if available
        avatar_url = None
        if feishu_user.avatar:
            avatar_url = (
                feishu_user.avatar.avatar_240
                or feishu_user.avatar.avatar_72
                or feishu_user.avatar.avatar_origin
            )

        if existing:
            # Update existing
            existing.name = feishu_user.name
            existing.email = feishu_user.email
            existing.mobile = feishu_user.mobile
            existing.job_title = feishu_user.job_title
            existing.employee_no = feishu_user.employee_no
            existing.avatar_url = avatar_url
            existing.department_ids = feishu_user.department_ids
            existing.is_active = feishu_user.status == 1
            existing.is_admin = feishu_user.is_tenant_manager or False
            existing.sync_updated_at = datetime.utcnow()
            stats.records_updated += 1
            self._logger.debug("employee_updated", user_id=feishu_user.user_id)
            return existing
        else:
            # Create new
            employee = Employee(
                feishu_user_id=feishu_user.user_id,
                name=feishu_user.name,
                email=feishu_user.email,
                mobile=feishu_user.mobile,
                job_title=feishu_user.job_title,
                employee_no=feishu_user.employee_no,
                avatar_url=avatar_url,
                department_ids=feishu_user.department_ids,
                is_active=feishu_user.status == 1,
                is_admin=feishu_user.is_tenant_manager or False,
                sync_updated_at=datetime.utcnow(),
            )
            self._session.add(employee)
            stats.records_created += 1
            self._logger.debug("employee_created", user_id=feishu_user.user_id)
            return employee

    async def _handle_departed_employees(self) -> int:
        """Mark employees not in Feishu as inactive.

        Returns:
            Number of employees deactivated
        """
        # Get all active employees from database
        result = await self._session.execute(
            select(Employee).where(Employee.is_active == True)
        )
        db_employees: List[Employee] = result.scalars().all()

        # Get all active employees from Feishu
        feishu_users = await self._client.list_users()
        feishu_user_ids = {u.user_id for u in feishu_users}

        deactivated_count = 0

        for employee in db_employees:
            if employee.feishu_user_id not in feishu_user_ids:
                employee.is_active = False
                employee.sync_updated_at = datetime.utcnow()
                deactivated_count += 1
                self._logger.info(
                    "employee_deactivated",
                    user_id=employee.feishu_user_id,
                    name=employee.name,
                )

        self._logger.info(
            "departed_employees_handled",
            deactivated_count=deactivated_count,
        )

        return deactivated_count

    def _sort_departments_by_hierarchy(
        self,
        departments: List[FeishuDepartmentRaw],
    ) -> List[FeishuDepartmentRaw]:
        """Sort departments so parents come before children.

        This ensures we can properly establish parent-child relationships
        in the database.
        """
        dept_map = {d.department_id: d for d in departments}

        def get_level(dept_id: str, visited: Set[str] = None) -> int:
            """Get hierarchy level of a department."""
            if visited is None:
                visited = set()

            if dept_id in visited:
                return 0  # Circular reference, treat as root

            visited.add(dept_id)

            dept = dept_map.get(dept_id)
            if not dept or not dept.parent_department_id:
                return 0

            return 1 + get_level(dept.parent_department_id, visited)

        return sorted(departments, key=lambda d: get_level(d.department_id))

    def _department_changed(
        self,
        existing: Department,
        feishu_dept: FeishuDepartmentRaw,
    ) -> bool:
        """Check if department data has changed."""
        return (
            existing.name != feishu_dept.name
            or existing.parent_id != feishu_dept.parent_department_id
            or existing.order != feishu_dept.order
            or not existing.is_active
        )

    def _employee_changed(
        self,
        existing: Employee,
        feishu_user: FeishuUserRaw,
    ) -> bool:
        """Check if employee data has changed."""
        # Simple comparison of key fields
        return (
            existing.name != feishu_user.name
            or existing.email != feishu_user.email
            or existing.job_title != feishu_user.job_title
            or existing.department_ids != feishu_user.department_ids
            or existing.is_active != (feishu_user.status == 1)
        )

    async def get_last_sync_time(self) -> Optional[datetime]:
        """Get timestamp of last successful sync."""
        from sqlalchemy import desc

        result = await self._session.execute(
            select(SyncLog)
            .where(SyncLog.status == "success")
            .order_by(desc(SyncLog.completed_at))
            .limit(1)
        )
        sync_log = result.scalar_one_or_none()

        return sync_log.completed_at if sync_log else None
