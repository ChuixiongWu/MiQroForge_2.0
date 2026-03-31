#!/usr/bin/env bash
# =============================================================================
# MiQroForge 2.0 — Install Python Phase 1 Dependencies
#
# 安装策略（按优先级）：
#   1. 若存在 venv (.venv/)，在其中安装
#   2. 若存在 uv，使用 uv pip install
#   3. 否则使用 pip install --user
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REQUIREMENTS="${PROJECT_ROOT}/requirements/phase1.txt"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "  ${BLUE}ℹ $1${NC}"; }
success() { echo -e "  ${GREEN}✔ $1${NC}"; }
warn()    { echo -e "  ${YELLOW}⚠ $1${NC}"; }
error()   { echo -e "  ${RED}✘ $1${NC}" >&2; exit 1; }

# ── 检查 Python 版本 ──────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    error "未找到 python3。请先安装 Python >= 3.10。"
fi

PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")

if [[ "$PY_MAJOR" -lt 3 || ("$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10) ]]; then
    error "Python ${PY_VER} 不满足要求（需要 >= 3.10）。"
fi
info "Python ${PY_VER} 已满足要求。"

# ── 检查 requirements 文件 ────────────────────────────────────────────────────
if [[ ! -f "${REQUIREMENTS}" ]]; then
    error "找不到 ${REQUIREMENTS}，请确保项目文件完整。"
fi

# ── 选择安装方式 ──────────────────────────────────────────────────────────────
VENV_DIR="${PROJECT_ROOT}/.venv"

if [[ -d "${VENV_DIR}" ]]; then
    info "检测到 .venv/，在虚拟环境中安装..."
    PIP="${VENV_DIR}/bin/pip"
    PYTHON="${VENV_DIR}/bin/python"

elif command -v uv &>/dev/null; then
    info "检测到 uv，创建虚拟环境并安装..."
    uv venv "${VENV_DIR}" --python python3
    PIP="${VENV_DIR}/bin/pip"
    PYTHON="${VENV_DIR}/bin/python"

else
    warn "未检测到 .venv/ 或 uv，建议先创建虚拟环境："
    warn "  python3 -m venv .venv && source .venv/bin/activate"
    warn "将使用 pip install --user 继续安装..."
    PIP="pip3"
    PYTHON="python3"
fi

# ── 升级 pip ──────────────────────────────────────────────────────────────────
info "升级 pip..."
"${PYTHON}" -m pip install --upgrade pip -q

# ── 安装依赖 ──────────────────────────────────────────────────────────────────
info "安装 requirements/phase1.txt..."
"${PIP}" install -r "${REQUIREMENTS}" -q

# ── 验证关键包 ────────────────────────────────────────────────────────────────
info "验证安装..."
"${PYTHON}" -c "
import importlib.metadata, pydantic, yaml, dotenv, pytest
assert int(pydantic.VERSION.split('.')[0]) >= 2, 'pydantic < v2'
print('  pydantic   ', pydantic.VERSION)
print('  pyyaml     ', yaml.__version__)
print('  python-dotenv', importlib.metadata.version('python-dotenv'))
print('  pytest     ', importlib.metadata.version('pytest'))
"

success "Python Phase 1 依赖安装完成。"

if [[ -d "${VENV_DIR}" && "${PIP}" == "${VENV_DIR}/bin/pip" ]]; then
    echo
    info "激活虚拟环境：source .venv/bin/activate"
fi
