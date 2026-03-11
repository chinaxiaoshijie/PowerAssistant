"""Test fixtures for Feishu client tests."""

import pytest


@pytest.fixture
def mock_token_response():
    """Mock successful token response."""
    return {
        "code": 0,
        "msg": "ok",
        "tenant_access_token": "test-token-12345",
        "expire": 7200,
    }


@pytest.fixture
def mock_token_response_expired():
    """Mock expired token response."""
    return {
        "code": 99991663,
        "msg": "tenant_access_token invalid",
    }


@pytest.fixture
def mock_departments_response():
    """Mock departments list response."""
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "items": [
                {
                    "department_id": "0",
                    "name": "公司总部",
                    "parent_department_id": "",
                    "department_path": "公司总部",
                    "order": 0,
                    "member_count": 50,
                    "status": 0,
                },
                {
                    "department_id": "d001",
                    "name": "研发中心",
                    "parent_department_id": "0",
                    "department_path": "公司总部/研发中心",
                    "order": 1,
                    "member_count": 30,
                    "status": 0,
                },
                {
                    "department_id": "d002",
                    "name": "交付中心",
                    "parent_department_id": "0",
                    "department_path": "公司总部/交付中心",
                    "order": 2,
                    "member_count": 20,
                    "status": 0,
                },
            ],
            "has_more": False,
            "page_token": None,
        },
    }


@pytest.fixture
def mock_departments_paginated_response():
    """Mock paginated departments response."""
    return [
        {
            "code": 0,
            "msg": "success",
            "data": {
                "items": [
                    {
                        "department_id": "d001",
                        "name": "研发中心",
                        "parent_department_id": "0",
                        "order": 1,
                    },
                ],
                "has_more": True,
                "page_token": "next_page_token_123",
            },
        },
        {
            "code": 0,
            "msg": "success",
            "data": {
                "items": [
                    {
                        "department_id": "d002",
                        "name": "交付中心",
                        "parent_department_id": "0",
                        "order": 2,
                    },
                ],
                "has_more": False,
                "page_token": None,
            },
        },
    ]


@pytest.fixture
def mock_users_response():
    """Mock users list response."""
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "items": [
                {
                    "user_id": "u001",
                    "union_id": "union001",
                    "open_id": "open001",
                    "name": "张三",
                    "en_name": "John Zhang",
                    "email": "zhangsan@example.com",
                    "mobile": "+8613800000001",
                    "job_title": "高级工程师",
                    "employee_no": "E001",
                    "department_ids": ["d001"],
                    "status": 1,
                },
                {
                    "user_id": "u002",
                    "union_id": "union002",
                    "open_id": "open002",
                    "name": "李四",
                    "en_name": "Li Si",
                    "email": "lisi@example.com",
                    "mobile": "+8613800000002",
                    "job_title": "产品经理",
                    "employee_no": "E002",
                    "department_ids": ["d001", "d002"],
                    "status": 1,
                },
            ],
            "has_more": False,
            "page_token": None,
        },
    }


@pytest.fixture
def mock_user_detail_response():
    """Mock user detail response."""
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "user_id": "u001",
            "union_id": "union001",
            "open_id": "open001",
            "name": "张三",
            "en_name": "John Zhang",
            "email": "zhangsan@example.com",
            "mobile": "+8613800000001",
            "job_title": "高级工程师",
            "employee_no": "E001",
            "department_ids": ["d001"],
            "status": 1,
            "is_tenant_manager": False,
        },
    }


@pytest.fixture
def mock_rate_limit_response():
    """Mock rate limit response."""
    return {
        "code": 99991401,
        "msg": "Request frequency limited",
    }


@pytest.fixture
def mock_auth_error_response():
    """Mock authentication error response."""
    return {
        "code": 99991663,
        "msg": "tenant_access_token invalid",
    }


@pytest.fixture
def mock_server_error_response():
    """Mock server error response."""
    return {
        "code": 99999999,
        "msg": "Internal server error",
    }
