#!/usr/bin/env bash
# =============================================================================
# MiQroForge 2.0 — Phase 1 Setup
# 职责：仅安装 Python 开发依赖。
#
# 基础设施（Docker / Kubernetes / Argo）需要 root 权限，由独立脚本处理：
#   sudo bash scripts/setup_infra.sh
#
# 用法：
#   bash scripts/setup_phase1.sh          # 交互模式
#   bash scripts/setup_phase1.sh --yes    # 自动安装所有缺失 Python 依赖
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}/install"
AUTO_YES=false

for arg in "$@"; do
    [[ "$arg" == "--yes" ]] && AUTO_YES=true
done

# ── 颜色 ──────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

section() { echo -e "\n${BLUE}${BOLD}── $1 ──${NC}"; }
success() { echo -e "  ${GREEN}✔ $1${NC}"; }
info()    { echo -e "  ${BLUE}ℹ $1${NC}"; }
warn()    { echo -e "  ${YELLOW}⚠ $1${NC}"; }

ask_install() {
    local component="$1"
    if $AUTO_YES; then return 0; fi
    echo -en "  ${YELLOW}?${NC} 是否安装 ${BOLD}${component}${NC}？[y/N] "
    read -r ans
    [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]]
}

# ── 检测环境 ──────────────────────────────────────────────────────────────────
declare -A MF_MISSING
source "${SCRIPT_DIR}/check_env.sh"
run_checks || true

if [[ ${#MF_MISSING[@]} -eq 0 ]]; then
    success "环境已完备，无需安装任何组件。"
    exit 0
fi

# ── 基础设施缺失：提示并引导，不在此处理 ─────────────────────────────────────
INFRA_MISSING=false
for key in "docker" "docker-daemon" "kubectl" "k8s-cluster" "argo-cli" "argo-server"; do
    [[ -v MF_MISSING["$key"] ]] && INFRA_MISSING=true && break
done

if $INFRA_MISSING; then
    section "基础设施未就绪"
    warn "以下组件需要 root 权限安装，不在本脚本处理范围内："
    for key in "docker" "docker-daemon" "kubectl" "k8s-cluster" "argo-cli" "argo-server"; do
        [[ -v MF_MISSING["$key"] ]] && echo -e "    ${RED}•${NC} ${MF_MISSING[$key]}"
    done
    echo
    echo -e "  请运行基础设施安装脚本（需要 sudo）："
    echo -e "  ${BOLD}  sudo bash scripts/setup_infra.sh${NC}"
    echo
    echo -e "  安装完成后再次运行本脚本。"
    echo -e "  详细说明见 ${BOLD}README.md${NC} → 快速开始"
fi

# ── Python 依赖 ───────────────────────────────────────────────────────────────
PYTHON_MISSING=false
for key in "python" "pydantic" "pytest" "pyyaml" "python-dotenv"; do
    [[ -v MF_MISSING["$key"] ]] && PYTHON_MISSING=true && break
done

if $PYTHON_MISSING; then
    section "Python 依赖"
    if ask_install "Python Phase 1 依赖（pydantic v2, pytest, pyyaml, python-dotenv）"; then
        bash "${INSTALL_DIR}/install_python_deps.sh"
    else
        info "跳过 Python 依赖安装。"
    fi
fi

# ── 重新检测 ──────────────────────────────────────────────────────────────────
echo
echo -e "${BOLD}重新检测环境...${NC}"
unset MF_MISSING
declare -A MF_MISSING
source "${SCRIPT_DIR}/check_env.sh"
run_checks || true

# 基础设施问题不影响 Python 开发环境的就绪判断
PYTHON_STILL_MISSING=false
for key in "python" "pydantic" "pytest" "pyyaml" "python-dotenv"; do
    [[ -v MF_MISSING["$key"] ]] && PYTHON_STILL_MISSING=true && break
done

if ! $PYTHON_STILL_MISSING; then
    echo
    success "Python 开发环境就绪，可以开始 Phase 1 开发！"
    if $INFRA_MISSING; then
        warn "基础设施仍需配置，提交工作流前请先运行: sudo bash scripts/setup_infra.sh"
    fi
else
    echo
    warn "Python 依赖仍有缺失，请参考上方报告处理。"
    exit 1
fi
