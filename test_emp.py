"""Check employee data."""
import asyncio
from src.database import database
from sqlalchemy import select
from src.models.organization import Employee

async def test():
    database.initialize()
    async with database.session_factory() as db:
        result = await db.execute(select(Employee))
        emps = result.scalars().all()
        for e in emps:
            print(f"Employee: {e.name}, is_active: {e.is_active}, dept_ids: {e.department_ids}")

if __name__ == "__main__":
    asyncio.run(test())
