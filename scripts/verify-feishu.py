#!/usr/bin/env python3
"""飞书配置验证脚本.

验证飞书 AppID 和 AppSecret 配置是否正确，
并测试与飞书 API 的连接。
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import structlog

logger = structlog.get_logger()


def check_environment():
    """检查环境变量配置."""
    from src.config.settings import settings

    print("=" * 60)
    print("飞书配置验证")
    print("=" * 60)
    print()

    # 检查 App ID
    app_id = settings.feishu.app_id
    if not app_id or app_id == "cli_test_app_id":
        print("❌ FEISHU_APP_ID 未配置")
        print("   请在 .env 文件中设置 FEISHU_APP_ID")
        print("   格式: cli_xxxxxxxxxxxxxxxx")
        return False
    else:
        print(f"✅ FEISHU_APP_ID: {app_id}")

    # 检查 App Secret
    app_secret = settings.feishu.app_secret
    if not app_secret or app_secret == "test_secret_key":
        print("❌ FEISHU_APP_SECRET 未配置")
        print("   请在 .env 文件中设置 FEISHU_APP_SECRET")
        return False
    else:
        masked_secret = app_secret[:4] + "****" + app_secret[-4:]
        print(f"✅ FEISHU_APP_SECRET: {masked_secret}")

    # 检查 Base URL
    print(f"✅ FEISHU_BASE_URL: {settings.feishu.base_url}")

    print()
    return True


async def test_connection():
    """测试飞书 API 连接."""
    from src.services.feishu.client import FeishuClient

    print("=" * 60)
    print("测试飞书 API 连接")
    print("=" * 60)
    print()

    try:
        async with FeishuClient() as client:
            # 测试获取 Token
            print("1. 获取访问令牌...")
            token = await client._get_access_token()
            print(f"   ✅ 成功 (Token: {token[:20]}...)")

            # 测试获取部门列表
            print("\n2. 获取部门列表...")
            departments = await client.list_departments(page_size=5)
            print(f"   ✅ 成功 (获取 {len(departments)} 个部门)")

            if departments:
                print("\n   部门示例:")
                for dept in departments[:3]:
                    print(f"   - {dept.name} (ID: {dept.department_id})")

            # 测试获取用户列表
            print("\n3. 获取用户列表...")
            users = await client.list_users(page_size=5)
            print(f"   ✅ 成功 (获取 {len(users)} 个用户)")

            if users:
                print("\n   用户示例:")
                for user in users[:3]:
                    print(f"   - {user.name} (ID: {user.user_id})")

            print()
            return True

    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        print()

        # 提供故障排除建议
        error_msg = str(e).lower()
        if "tenant_access_token invalid" in error_msg:
            print("故障排除:")
            print("  1. 检查 FEISHU_APP_ID 和 FEISHU_APP_SECRET 是否正确")
            print("  2. 确认应用已在飞书开放平台创建")
            print("  3. 检查 App Secret 是否已重置（重置后需更新配置）")
        elif "permission" in error_msg or "denied" in error_msg:
            print("故障排除:")
            print("  1. 确认已在飞书开放平台申请权限")
            print("  2. 检查权限是否已审批通过")
            print("  3. 确认应用可见范围包含目标部门")
        elif "cannot connect" in error_msg:
            print("故障排除:")
            print("  1. 检查网络连接")
            print("  2. 确认可以访问 open.feishu.cn")
            print("  3. 检查防火墙设置")

        return False


def print_next_steps():
    """打印下一步操作."""
    print("=" * 60)
    print("下一步")
    print("=" * 60)
    print()
    print("1. 启动服务:")
    print("   docker-compose up -d")
    print()
    print("2. 触发同步:")
    print("   curl -X POST http://localhost:8000/api/v1/sync/full")
    print()
    print("3. 查看 API 文档:")
    print("   http://localhost:8000/api/docs")
    print()


async def main():
    """主函数."""
    # 检查环境变量
    if not check_environment():
        print()
        print("配置检查失败，请按上述提示修改 .env 文件")
        sys.exit(1)

    # 测试连接
    if not await test_connection():
        print()
        print("连接测试失败，请根据错误信息排查")
        sys.exit(1)

    # 成功
    print()
    print("=" * 60)
    print("✅ 飞书配置验证通过！")
    print("=" * 60)
    print()

    print_next_steps()


if __name__ == "__main__":
    asyncio.run(main())
