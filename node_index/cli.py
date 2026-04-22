"""节点索引 CLI。

用法::

    python -m node_index.cli reindex           # 重新扫描生成 node_index.yaml
    python -m node_index.cli list              # 列出所有节点
    python -m node_index.cli search <query>    # 搜索节点
    python -m node_index.cli info <name>       # 显示节点详情
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── 颜色 ──
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

# 端口类别颜色
PORT_COLORS = {
    "physical_quantity": "\033[0;33m",       # 橙色 (yellow)
    "software_data_package": "\033[0;34m",   # 蓝色
    "logic_value": "\033[0;32m",             # 绿色
    "report_object": "\033[0;35m",           # 紫色
}


def _detect_project_root() -> Path:
    """探测项目根目录。"""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "CLAUDE.md").exists() or (parent / "nodes" / "schemas").exists():
            return parent
    return cwd


def _load_include_test_setting(project_root: Path) -> bool:
    """从 userdata/settings.yaml 读取 index.include_test_nodes 配置。"""
    settings_path = project_root / "userdata" / "settings.yaml"
    if not settings_path.exists():
        return False
    try:
        import yaml
        with settings_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("index", {}).get("include_test_nodes", False)
    except Exception:
        return False


def cmd_reindex() -> int:
    """重新扫描生成 node_index.yaml。"""
    from .scanner import scan_nodes, write_index

    project_root = _detect_project_root()
    print(f"\n{BLUE}{BOLD}══ MF Node Index — Reindex ══{NC}\n")
    print(f"  {BLUE}i Scanning nodes/ directory...{NC}")

    include_test = _load_include_test_setting(project_root)
    index = scan_nodes(project_root, include_test_nodes=include_test)
    output = write_index(index, project_root)

    print(f"  {GREEN}✔ Indexed {index.total_nodes} nodes → {output}{NC}")

    for entry in index.entries:
        n_in = len(entry.stream_inputs)
        n_out = len(entry.stream_outputs)
        print(
            f"  {DIM}  • {entry.name} v{entry.version} "
            f"({entry.node_type}/{entry.category}) "
            f"[{n_in} in / {n_out} out]{NC}"
        )
    print()
    return 0


def cmd_list(include_deprecated: bool = False) -> int:
    """列出所有索引中的节点。"""
    from .scanner import load_index

    project_root = _detect_project_root()

    try:
        index = load_index(project_root)
    except FileNotFoundError as e:
        print(f"  {RED}✘ {e}{NC}", file=sys.stderr)
        return 1

    entries_all = index.entries
    if not include_deprecated:
        entries_all = [e for e in entries_all if not e.deprecated]

    dep_count = sum(1 for e in index.entries if e.deprecated)
    header_count = f"{len(entries_all)} nodes"
    if dep_count and not include_deprecated:
        header_count += f" ({dep_count} deprecated hidden)"

    print(f"\n{BLUE}{BOLD}══ MF Node Catalog ({header_count}) ══{NC}\n")

    # 按 category 分组
    by_cat: dict[str, list] = {}
    for entry in entries_all:
        by_cat.setdefault(entry.category, []).append(entry)

    for cat, entries in sorted(by_cat.items()):
        print(f"  {BOLD}{cat.upper()}{NC}")
        for entry in entries:
            n_in = len(entry.stream_inputs)
            n_out = len(entry.stream_outputs)
            n_param = len(entry.onboard_inputs)
            type_badge = f"{CYAN}compute{NC}" if entry.node_type == "compute" else f"{GREEN}light{NC}"
            dep_badge = f"  {RED}[deprecated]{NC}" if entry.deprecated else ""
            print(
                f"    {BOLD}{entry.name}{NC} v{entry.version}"
                f"  [{type_badge}]"
                f"  {n_in}→{n_out} ports"
                f"  {n_param} params"
                f"{dep_badge}"
            )
            if entry.description:
                desc = entry.description[:80]
                if len(entry.description) > 80:
                    desc += "..."
                print(f"      {DIM}{desc}{NC}")
        print()

    return 0


def cmd_search(query: str, include_deprecated: bool = False) -> int:
    """搜索节点。"""
    from .scanner import load_index
    from .search import search_nodes

    project_root = _detect_project_root()

    try:
        index = load_index(project_root)
    except FileNotFoundError as e:
        print(f"  {RED}✘ {e}{NC}", file=sys.stderr)
        return 1

    results = search_nodes(index, query)

    if not include_deprecated:
        results = [r for r in results if not r.deprecated]

    print(f"\n{BLUE}{BOLD}══ Search: \"{query}\" — {len(results)} results ══{NC}\n")

    if not results:
        print(f"  {YELLOW}⚠ No nodes matched your query.{NC}")
        print(f"  {DIM}  Try broader terms or run 'mf2 nodes list' to see all nodes.{NC}")
        print()
        return 0

    for entry in results:
        n_in = len(entry.stream_inputs)
        n_out = len(entry.stream_outputs)
        type_badge = f"{CYAN}compute{NC}" if entry.node_type == "compute" else f"{GREEN}light{NC}"
        print(
            f"  {BOLD}{entry.name}{NC} v{entry.version}"
            f"  [{type_badge}]"
            f"  {entry.category}"
        )
        if entry.description:
            desc = entry.description[:100]
            if len(entry.description) > 100:
                desc += "..."
            print(f"    {DIM}{desc}{NC}")

    print()
    return 0


def cmd_info(name: str) -> int:
    """显示单个节点的完整信息。"""
    from .scanner import load_index

    project_root = _detect_project_root()

    try:
        index = load_index(project_root)
    except FileNotFoundError as e:
        print(f"  {RED}✘ {e}{NC}", file=sys.stderr)
        return 1

    # 查找节点
    entry = None
    for e in index.entries:
        if e.name == name:
            entry = e
            break

    if entry is None:
        print(f"  {RED}✘ Node '{name}' not found in index.{NC}", file=sys.stderr)
        print(f"  {DIM}  Available nodes:{NC}")
        for e in index.entries:
            print(f"  {DIM}    • {e.name}{NC}")
        return 1

    print(f"\n{BLUE}{BOLD}══ Node: {entry.display_name} ══{NC}\n")

    # 基本信息
    type_badge = f"{CYAN}compute{NC}" if entry.node_type == "compute" else f"{GREEN}lightweight{NC}"
    print(f"  {BOLD}Name:{NC}        {entry.name}")
    print(f"  {BOLD}Version:{NC}     {entry.version}")
    print(f"  {BOLD}Type:{NC}        {type_badge}")
    print(f"  {BOLD}Category:{NC}    {entry.category}")
    if entry.deprecated:
        print(f"  {BOLD}Status:{NC}      {RED}DEPRECATED{NC}")
    if entry.base_image_ref:
        print(f"  {BOLD}Base Image:{NC}  {entry.base_image_ref}")
    print(f"  {BOLD}Spec Path:{NC}   {entry.nodespec_path}")
    print()

    if entry.description:
        print(f"  {BOLD}Description:{NC}")
        print(f"    {entry.description}")
        print()

    # 标签
    if entry.software or entry.methods or entry.domains or entry.capabilities or entry.keywords:
        print(f"  {BOLD}Tags:{NC}")
        if entry.software:
            print(f"    Software:     {entry.software}")
        if entry.methods:
            print(f"    Methods:      {', '.join(entry.methods)}")
        if entry.domains:
            print(f"    Domains:      {', '.join(entry.domains)}")
        if entry.capabilities:
            print(f"    Capabilities: {', '.join(entry.capabilities)}")
        if entry.keywords:
            print(f"    Keywords:     {', '.join(entry.keywords)}")
        print()

    # Stream 输入
    if entry.stream_inputs:
        print(f"  {BOLD}Stream Inputs ({len(entry.stream_inputs)}):{NC}")
        for port in entry.stream_inputs:
            color = PORT_COLORS.get(port.category, NC)
            print(f"    {color}●{NC} {port.name}  {DIM}[{port.category}] {port.detail}{NC}")
        print()

    # Stream 输出
    if entry.stream_outputs:
        print(f"  {BOLD}Stream Outputs ({len(entry.stream_outputs)}):{NC}")
        for port in entry.stream_outputs:
            color = PORT_COLORS.get(port.category, NC)
            print(f"    {color}●{NC} {port.name}  {DIM}[{port.category}] {port.detail}{NC}")
        print()

    # On-Board
    if entry.onboard_inputs or entry.onboard_outputs:
        print(f"  {BOLD}On-Board:{NC}")
        print(f"    Inputs:  {len(entry.onboard_inputs)} parameters")
        print(f"    Outputs: {len(entry.onboard_outputs)} results")
        print()

    return 0


def main() -> None:
    """CLI 入口点。"""
    if len(sys.argv) < 2:
        print(f"""
{BLUE}{BOLD}mf2 node-index — MiQroForge 2.0 Node Index CLI{NC}

{BOLD}Usage:{NC}
  python -m node_index.cli reindex          重新扫描生成 node_index.yaml
  python -m node_index.cli list [-d]        列出所有节点
  python -m node_index.cli search <query> [-d]  搜索节点
  python -m node_index.cli info <name>      显示节点详情

{BOLD}Options:{NC}
  -d, --include-deprecated    包含已废弃的节点
""")
        sys.exit(0)

    # 解析全局 flag
    include_deprecated = "-d" in sys.argv or "--include-deprecated" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("-d", "--include-deprecated")]

    cmd = args[0] if args else ""

    if cmd == "reindex":
        sys.exit(cmd_reindex())
    elif cmd == "list":
        sys.exit(cmd_list(include_deprecated=include_deprecated))
    elif cmd == "search":
        if len(args) < 2:
            print(f"  {RED}✘ 用法: python -m node_index.cli search <query>{NC}")
            sys.exit(1)
        query = " ".join(args[1:])
        sys.exit(cmd_search(query, include_deprecated=include_deprecated))
    elif cmd == "info":
        if len(args) < 2:
            print(f"  {RED}✘ 用法: python -m node_index.cli info <name>{NC}")
            sys.exit(1)
        sys.exit(cmd_info(args[1]))
    else:
        print(f"  {RED}✘ 未知命令: {cmd}{NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
