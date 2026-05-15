#!/usr/bin/env python3
"""MiQroForge 2.0 单用户 → 多用户数据迁移脚本。

非破坏性迁移：使用 mv（而非 rm），可手动回滚。

迁移逻辑：
  userdata/models.yaml              → userdata/shared/models.yaml
  userdata/node_gen_memory/         → userdata/shared/node_gen_memory/
  userdata/vectorstore/             → userdata/shared/vectorstore/
  userdata/projects/                → userdata/users/{admin}/projects/
  userdata/workspace/               → userdata/users/{admin}/workspace/
  userdata/nodes/                   → userdata/users/{admin}/nodes/
  userdata/settings.yaml            → userdata/users/{admin}/settings.yaml
  userdata/node_preferences.yaml    → userdata/users/{admin}/node_preferences.yaml
  userdata/agent_sessions/          → userdata/users/{admin}/agent_sessions/
  userdata/pip_history.jsonl        → userdata/users/{admin}/pip_history.jsonl

用法：
    python scripts/migrate_to_multiuser.py [--admin-username NAME] [--dry-run]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))


DRY_RUN = False
MOVED: list[tuple[str, str]] = []


def _mv(src: Path, dst: Path) -> None:
    """移动文件或目录，dry-run 模式下只打印。"""
    global MOVED
    if not src.exists():
        print(f"  [SKIP] 源不存在: {src}")
        return
    if DRY_RUN:
        print(f"  [DRY-RUN] {src} → {dst}")
        MOVED.append((str(src), str(dst)))
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    MOVED.append((str(src), str(dst)))
    print(f"  [OK] {src} → {dst}")


def main() -> None:
    global DRY_RUN

    parser = argparse.ArgumentParser(
        description="MiQroForge 2.0 单用户 → 多用户数据迁移",
    )
    parser.add_argument("--admin-username", default="admin",
                        help="管理员用户名（接收旧数据），默认: admin")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅显示迁移计划，不实际执行")
    args = parser.parse_args()

    DRY_RUN = args.dry_run
    admin_user = args.admin_username

    from api.config import get_settings
    settings = get_settings()
    data_root = settings.data_root
    users_root = settings.users_root
    shared_root = settings.shared_root

    print("=" * 60)
    print("MiQroForge 2.0 多用户数据迁移")
    print("=" * 60)
    print(f"  data_root:    {data_root}")
    print(f"  admin user:   {admin_user}")
    print(f"  mode:         {'DRY RUN (不实际操作)' if DRY_RUN else 'LIVE (实际移动文件)'}")
    print()

    # 检查是否已迁移
    if shared_root.exists() and list(shared_root.iterdir()):
        print("[WARN] userdata/shared/ 已存在且非空——可能已迁移过。")
        ans = input("继续执行? [y/N] ")
        if ans.lower() != "y":
            print("已取消。")
            return

    # ═══ Step 1: 共享数据 ═══
    print("─ 共享数据 ─")
    _mv(data_root / "models.yaml", shared_root / "models.yaml")
    _mv(data_root / "node_gen_memory", shared_root / "node_gen_memory")
    _mv(data_root / "vectorstore", shared_root / "vectorstore")

    # ═══ Step 2: 私有数据（迁移到 admin 用户下）═══
    print("\n─ 私有数据 (→ users/{}) ─".format(admin_user))
    admin_dir = users_root / admin_user
    admin_dir.mkdir(parents=True, exist_ok=True)

    _mv(data_root / "projects", admin_dir / "projects")
    _mv(data_root / "workspace", admin_dir / "workspace")
    _mv(data_root / "nodes", admin_dir / "nodes")
    _mv(data_root / "settings.yaml", admin_dir / "settings.yaml")
    _mv(data_root / "node_preferences.yaml", admin_dir / "node_preferences.yaml")
    _mv(data_root / "agent_sessions", admin_dir / "agent_sessions")
    _mv(data_root / "pip_history.jsonl", admin_dir / "pip_history.jsonl")
    # 可能存在的临时文件目录
    _mv(data_root / "tmp", admin_dir / "tmp")

    # ═══ Step 3: 创建管理员账户 ═══
    print("\n─ 认证数据 ─")
    from api.auth import create_user_yaml, hash_password, init_auth, user_exists
    init_auth(settings.auth_dir)

    if not user_exists(admin_user, settings.auth_dir):
        import getpass
        print(f"\n为管理员 '{admin_user}' 设置密码：")
        pw = getpass.getpass("密码: ")
        pw2 = getpass.getpass("确认密码: ")
        if pw != pw2:
            print("错误：两次输入的密码不一致。")
            sys.exit(1)
        if len(pw) < 4:
            print("错误：密码至少 4 个字符。")
            sys.exit(1)
        pwh = hash_password(pw)
        if not DRY_RUN:
            create_user_yaml(admin_user, pwh, "admin", admin_user, settings.auth_dir)
            print(f"  [OK] 管理员账户 '{admin_user}' 创建成功")
        else:
            print(f"  [DRY-RUN] 将创建管理员账户 '{admin_user}'")
    else:
        print(f"  [SKIP] 用户 '{admin_user}' 已存在，不覆盖")

    # ═══ 总结 ═══
    print("\n" + "=" * 60)
    if DRY_RUN:
        print("DRY RUN 完成。以上操作未实际执行。")
        print(f"共 {len(MOVED)} 项将被迁移。")
        print("\n运行以下命令执行实际迁移：")
        print(f"  python scripts/migrate_to_multiuser.py --admin-username {admin_user}")
    else:
        print("迁移完成!")
        print(f"共 {len(MOVED)} 项已迁移。")
        print()
        print("后续步骤：")
        print(f"  1. 登录: POST /api/v1/auth/login (username={admin_user})")
        print(f"  2. 创建其他用户: python scripts/create_user.py <username>")
        print(f"  3. 可选：清理旧 userdata/ 顶层空目录")

    # 回滚命令
    print()
    print("回滚命令（如有需要）：")
    for src, dst in reversed(MOVED):
        print(f"  mv '{dst}' '{src}'")


if __name__ == "__main__":
    main()
