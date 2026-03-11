"""Test database content."""
import asyncio
from src.database import database
from sqlalchemy import select
from src.models.organization import Department, Employee

async def test():
    database.initialize()
    async with database.session_factory() as db:
        result = await db.execute(select(Department))
        depts = result.scalars().all()
        print(f"Departments: {len(depts)}")
        for d in depts:
            print(f"  - {d.name} (feishu_id: {d.feishu_dept_id})")

        result = await db.execute(select(Employee))
        emps = result.scalars().all()
        print(f"Employees: {len(emps)}")
        for e in emps:
            print(f"  - {e.name} (depts: {e.department_ids})")

if __name__ == "__main__":
    asyncio.run(test())
