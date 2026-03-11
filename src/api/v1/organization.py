"""Organization API routes.

This module provides RESTful endpoints for querying organization structure
including departments and employees.
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.models.organization import Department, Employee
from src.schemas.organization import (
    DepartmentResponse,
    DepartmentTreeResponse,
    EmployeeDetailResponse,
    EmployeeListResponse,
    EmployeeResponse,
    PaginatedResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/organization", tags=["organization"])


@router.get("/departments", response_model=List[DepartmentResponse])
async def list_departments(
    include_inactive: bool = Query(
        default=False,
        description="Include inactive departments",
    ),
    db: AsyncSession = Depends(get_db),
) -> List[DepartmentResponse]:
    """List all departments.

    Args:
        include_inactive: Whether to include inactive departments
        db: Database session

    Returns:
        List of departments
    """
    logger.info("listing_departments", include_inactive=include_inactive)

    query = select(Department)
    if not include_inactive:
        query = query.where(Department.is_active == True)
    query = query.order_by(Department.order)

    result = await db.execute(query)
    departments = result.scalars().all()

    # Convert to response model with employee count
    response_depts = []
    for dept in departments:
        # Count employees in this department
        # Use PostgreSQL JSONB contains operator or fallback to Python filtering
        try:
            emp_count_result = await db.execute(
                select(func.count(Employee.id)).where(
                    Employee.department_ids.cast(str).like(f'%{dept.feishu_dept_id}%'),
                    Employee.is_active == True,
                )
            )
            emp_count = emp_count_result.scalar() or 0
        except Exception as e:
            logger.warning("employee_count_query_failed", error=str(e))
            # Fallback: fetch all and filter in Python
            all_emps_result = await db.execute(select(Employee))
            all_emps = all_emps_result.scalars().all()
            emp_count = sum(
                1 for e in all_emps
                if e.is_active and dept.feishu_dept_id in (e.department_ids or [])
            )

        response_depts.append(
            DepartmentResponse(
                id=dept.id,
                feishu_dept_id=dept.feishu_dept_id,
                name=dept.name,
                order=dept.order,
                is_active=dept.is_active,
                parent_id=dept.parent_id,
                children=[],  # Will be populated below
                employee_count=emp_count,
                created_at=dept.created_at,
                updated_at=dept.updated_at,
            )
        )

    logger.info("departments_listed", count=len(response_depts))
    return response_depts


@router.get("/departments/tree", response_model=DepartmentTreeResponse)
async def get_department_tree(
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> DepartmentTreeResponse:
    """Get department hierarchy as a tree structure.

    Returns departments nested by parent-child relationships.

    Args:
        include_inactive: Whether to include inactive departments
        db: Database session

    Returns:
        Nested department tree
    """
    logger.info("getting_department_tree", include_inactive=include_inactive)

    query = select(Department)
    if not include_inactive:
        query = query.where(Department.is_active == True)

    result = await db.execute(query)
    all_depts = result.scalars().all()

    # Build lookup map
    dept_map = {}
    for dept in all_depts:
        dept_map[dept.feishu_dept_id] = {
            "id": dept.id,
            "feishu_dept_id": dept.feishu_dept_id,
            "name": dept.name,
            "order": dept.order,
            "is_active": dept.is_active,
            "parent_id": dept.parent_id,
            "children": [],
            "employee_count": 0,
            "created_at": dept.created_at,
            "updated_at": dept.updated_at,
        }

    # Build tree structure
    root_depts = []
    for dept_data in dept_map.values():
        parent_id = dept_data["parent_id"]
        if parent_id and parent_id in dept_map:
            dept_map[parent_id]["children"].append(dept_data)
        else:
            root_depts.append(dept_data)

    # Sort children by order
    for dept_data in dept_map.values():
        dept_data["children"].sort(key=lambda x: x["order"])

    # Sort root departments by order
    root_depts.sort(key=lambda x: x["order"])

    logger.info("department_tree_built", total_count=len(all_depts), root_count=len(root_depts))

    return DepartmentTreeResponse(
        departments=root_depts,
        total_count=len(all_depts),
    )


@router.get("/departments/{dept_id}/employees", response_model=List[EmployeeResponse])
async def get_department_employees(
    dept_id: str,
    include_sub_depts: bool = Query(
        default=True,
        description="Include employees from sub-departments",
    ),
    db: AsyncSession = Depends(get_db),
) -> List[EmployeeResponse]:
    """Get employees in a department.

    Args:
        dept_id: Feishu department ID
        include_sub_depts: Whether to include sub-department employees
        db: Database session

    Returns:
        List of employees
    """
    logger.info(
        "getting_department_employees",
        dept_id=dept_id,
        include_sub_depts=include_sub_depts,
    )

    # Get department IDs to query
    dept_ids = [dept_id]

    if include_sub_depts:
        # Get all sub-department IDs
        sub_depts_result = await db.execute(
            select(Department).where(Department.parent_id == dept_id)
        )
        sub_depts = sub_depts_result.scalars().all()
        dept_ids.extend([d.feishu_dept_id for d in sub_depts])

    # Query employees in these departments
    # Use string-based LIKE query for JSON field compatibility
    try:
        # Build a filter condition for any of the dept_ids
        conditions = [Employee.department_ids.cast(str).like(f'%{did}%') for did in dept_ids]
        from sqlalchemy import or_
        query = select(Employee).where(
            or_(*conditions),
            Employee.is_active == True,
        )
        result = await db.execute(query)
        employees = result.scalars().all()
    except Exception as e:
        logger.warning("employee_query_failed", error=str(e))
        # Fallback: fetch all and filter in Python
        all_emps_result = await db.execute(select(Employee).where(Employee.is_active == True))
        all_emps = all_emps_result.scalars().all()
        employees = [e for e in all_emps if any(did in (e.department_ids or []) for did in dept_ids)]

    # Build response with department names
    response_employees = []
    for emp in employees:
        # Get department names
        dept_names = []
        for emp_dept_id in emp.department_ids or []:
            dept_result = await db.execute(
                select(Department.name).where(Department.feishu_dept_id == emp_dept_id)
            )
            name = dept_result.scalar()
            if name:
                dept_names.append(name)

        response_employees.append(
            EmployeeResponse(
                id=emp.id,
                feishu_user_id=emp.feishu_user_id,
                name=emp.name,
                job_title=emp.job_title,
                is_active=emp.is_active,
                email=emp.email,
                mobile=emp.mobile,
                employee_no=emp.employee_no,
                avatar_url=emp.avatar_url,
                department_names=dept_names,
                role_type=emp.role_type,
                join_date=emp.join_date,
                is_admin=emp.is_admin,
                created_at=emp.created_at,
                updated_at=emp.updated_at,
            )
        )

    logger.info("department_employees_fetched", count=len(response_employees))
    return response_employees


@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(
    search: Optional[str] = Query(None, description="Search by name or email"),
    dept_id: Optional[str] = Query(None, description="Filter by department ID"),
    role_type: Optional[str] = Query(None, description="Filter by role type"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> EmployeeListResponse:
    """List employees with filtering and pagination.

    Args:
        search: Search term for name or email
        dept_id: Filter by department ID
        role_type: Filter by role type
        is_active: Filter by active status
        page: Page number (1-based)
        page_size: Items per page
        db: Database session

    Returns:
        Paginated employee list
    """
    logger.info(
        "listing_employees",
        search=search,
        dept_id=dept_id,
        role_type=role_type,
        page=page,
        page_size=page_size,
    )

    # Build base query
    base_query = select(Employee)
    count_query = select(func.count(Employee.id))

    # Apply filters
    filters = []
    if search:
        search_filter = (
            Employee.name.ilike(f"%{search}%") |
            Employee.email.ilike(f"%{search}%")
        )
        filters.append(search_filter)

    if dept_id:
        # Use LIKE query for JSON field compatibility instead of contains()
        filters.append(Employee.department_ids.cast(str).like(f'%{dept_id}%'))

    if role_type:
        filters.append(Employee.role_type == role_type)

    if is_active is not None:
        filters.append(Employee.is_active == is_active)

    # Apply filters to both queries
    for f in filters:
        base_query = base_query.where(f)
        count_query = count_query.where(f)

    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    base_query = base_query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(base_query)
    employees = result.scalars().all()

    # Build response
    response_employees = []
    for emp in employees:
        dept_names = []
        for emp_dept_id in emp.department_ids or []:
            dept_result = await db.execute(
                select(Department.name).where(Department.feishu_dept_id == emp_dept_id)
            )
            name = dept_result.scalar()
            if name:
                dept_names.append(name)

        response_employees.append(
            EmployeeResponse(
                id=emp.id,
                feishu_user_id=emp.feishu_user_id,
                name=emp.name,
                job_title=emp.job_title,
                is_active=emp.is_active,
                email=emp.email,
                mobile=emp.mobile,
                employee_no=emp.employee_no,
                avatar_url=emp.avatar_url,
                department_names=dept_names,
                role_type=emp.role_type,
                join_date=emp.join_date,
                is_admin=emp.is_admin,
                created_at=emp.created_at,
                updated_at=emp.updated_at,
            )
        )

    logger.info("employees_listed", count=len(response_employees), total=total)

    return EmployeeListResponse(
        items=response_employees,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/employees/{employee_id}", response_model=EmployeeDetailResponse)
async def get_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
) -> EmployeeDetailResponse:
    """Get detailed employee information.

    Args:
        employee_id: Internal employee ID
        db: Database session

    Returns:
        Employee details

    Raises:
        HTTPException: If employee not found
    """
    logger.info("getting_employee", employee_id=employee_id)

    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()

    if not emp:
        logger.warning("employee_not_found", employee_id=employee_id)
        raise HTTPException(status_code=404, detail="Employee not found")

    # Get department names
    dept_names = []
    for emp_dept_id in emp.department_ids or []:
        dept_result = await db.execute(
            select(Department.name).where(Department.feishu_dept_id == emp_dept_id)
        )
        name = dept_result.scalar()
        if name:
            dept_names.append(name)

    return EmployeeDetailResponse(
        id=emp.id,
        feishu_user_id=emp.feishu_user_id,
        name=emp.name,
        job_title=emp.job_title,
        is_active=emp.is_active,
        email=emp.email,
        mobile=emp.mobile,
        employee_no=emp.employee_no,
        avatar_url=emp.avatar_url,
        department_ids=emp.department_ids,
        department_names=dept_names,
        role_type=emp.role_type,
        join_date=emp.join_date,
        is_admin=emp.is_admin,
        created_at=emp.created_at,
        updated_at=emp.updated_at,
    )
