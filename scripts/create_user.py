#!/usr/bin/env python3
"""创建 MiQroForge 2.0 用户账户。

用法：
    python scripts/create_user.py <username> [--admin] [--display-name NAME]

首次运行时，如果 userdata/auth/users.yaml 尚不存在，会自动创建。
密码通过交互式提示输入（不显示在终端上）。

示例：
    python scripts/create_user.py alice
    python scripts/create_user.py bob --admin --display-name "Bob"
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="创建 MiQroForge 2.0 用户账户",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/create_user.py alice
  python scripts/create_user.py bob --admin --display-name "Bob"
        """,
    )
    parser.add_argument("username", help="用户名（字母、数字、下划线、短横线）")
    parser.add_argument("--admin", action="store_true", help="设为管理员角色")
    parser.add_argument("--display-name", default="", help="显示名称")
    args = parser.parse_args()

    # 验证用户名格式
    import re
    if not re.match(r"^[a-zA-Z0-9_\-]+$", args.username):
        print("错误：用户名只能包含字母、数字、下划线和短横线。")
        sys.exit(1)

    # 密码输入
    password = getpass.getpass(f"请输入 {args.username} 的密码: ")
    if len(password) < 4:
        print("错误：密码至少 4 个字符。")
        sys.exit(1)
    confirm = getpass.getpass("确认密码: ")
    if password != confirm:
        print("错误：两次输入的密码不一致。")
        sys.exit(1)

    # 初始化 auth 模块
    from api.config import get_settings
    settings = get_settings()

    from api.auth import create_user_yaml, hash_password, init_auth, user_exists

    # 确保 auth 目录和密钥存在
    init_auth(settings.auth_dir)

    # 检查用户是否已存在
    if user_exists(args.username, settings.auth_dir):
        print(f"警告：用户 '{args.username}' 已存在，将更新密码。")

    role = "admin" if args.admin else "user"
    password_hash = hash_password(password)
    create_user_yaml(args.username, password_hash, role, args.display_name, settings.auth_dir)

    print(f"✓ 用户 '{args.username}' (角色: {role}) 创建成功。")


if __name__ == "__main__":
    main()
