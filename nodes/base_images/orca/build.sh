#!/usr/bin/env bash
# =============================================================================
# build.sh — 构建 ORCA 6.1 Docker 镜像（本地使用）
#
# 用法：
#   bash nodes/base_images/orca/build.sh
#
# 前置条件：
#   将 ORCA 6.1 tarball 放到本目录（通过下载引导获取）
#   文件名示例：orca_6_1_0_linux_x86-64_shared_openmpi418_avx2.tar.xz
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE_NAME="harbor.era.local/library/orca"
IMAGE_TAG="6.1"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

_info()  { echo -e "  ${BLUE}ℹ  $*${NC}"; }
_ok()    { echo -e "  ${GREEN}✔  $*${NC}"; }
_warn()  { echo -e "  ${YELLOW}⚠  $*${NC}"; }
_error() { echo -e "\n  ${RED}✘  $*${NC}\n" >&2; exit 1; }

echo
echo -e "${BLUE}${BOLD}══ Build ORCA 6.1 Docker Image ══${NC}"
echo

# ── 1. 检测 tarball ───────────────────────────────────────────────────────────
TARBALL=""
for f in "${SCRIPT_DIR}"/*.tar.xz "${SCRIPT_DIR}"/*.tar.gz; do
    [[ -f "$f" ]] && TARBALL="$f" && break
done

if [[ -z "$TARBALL" ]]; then
    _error "未找到 ORCA tarball！
请先运行下载引导：
    bash nodes/base_images/orca/download_orca.sh"
fi

TARBALL_FILENAME="$(basename "$TARBALL")"
_ok "找到 tarball：${TARBALL_FILENAME}"

# ── 2. 确认 Docker 可用 ───────────────────────────────────────────────────────
command -v docker &>/dev/null || _error "Docker 未安装或未在 PATH 中"

DOCKER="docker"
if ! docker info &>/dev/null; then
    DOCKER_ERR=$(docker info 2>&1 || true)

    if echo "$DOCKER_ERR" | grep -qi "permission denied"; then
        _warn "当前用户无权访问 Docker socket，尝试 sudo docker..."
        sudo docker info &>/dev/null \
            && DOCKER="sudo docker" && _ok "将使用 sudo docker" \
            || _error "sudo docker info 也失败，请检查 Docker 安装。"
    else
        _warn "Docker daemon 未运行，正在尝试启动..."
        if command -v systemctl &>/dev/null \
           && systemctl list-units --type=service 2>/dev/null | grep -q docker; then
            sudo systemctl start docker && _info "已通过 systemctl 启动 Docker" || true
        elif command -v service &>/dev/null; then
            sudo service docker start && _info "已通过 service 启动 Docker" || true
        elif [[ "$(uname -s)" == "Darwin" ]]; then
            open -a Docker 2>/dev/null && _info "已唤醒 Docker Desktop..." || true
        else
            _error "无法自动启动 Docker，请手动运行：sudo systemctl start docker"
        fi

        waited=0
        until docker info &>/dev/null; do
            [[ $waited -ge 30 ]] && _error "等待 Docker daemon 超时（30s）"
            sleep 2; waited=$(( waited + 2 ))
            _info "等待 Docker daemon 就绪... (${waited}s)"
        done
        _ok "Docker daemon 已就绪"
    fi
fi

# ── 3. 构建镜像 ───────────────────────────────────────────────────────────────
_info "构建镜像：${FULL_IMAGE}"
echo

$DOCKER build \
    --tag "${FULL_IMAGE}" \
    --build-arg "ORCA_TARBALL=${TARBALL_FILENAME}" \
    --no-cache \
    "${SCRIPT_DIR}"

echo
_ok "构建完成：${FULL_IMAGE}"

$DOCKER tag "${FULL_IMAGE}" "${IMAGE_NAME}:latest"
_ok "已添加 latest 标签"

# ── 4. 验证 ──────────────────────────────────────────────────────────────────
_info "验证 ORCA 二进制..."
if $DOCKER run --rm "${FULL_IMAGE}" /opt/orca/orca 2>&1 | grep -q "Starting time"; then
    _ok "ORCA 二进制验证通过"
else
    _warn "未能确认 ORCA 可执行，请手动检查：$DOCKER run --rm ${FULL_IMAGE} /opt/orca/orca"
fi

echo
_ok "完成！可以开始运行工作流："
echo "    bash scripts/mf2.sh validate workflows/examples/orca-h2o-thermo-mf.yaml"
echo "    bash scripts/mf2.sh run     workflows/examples/orca-h2o-thermo-mf.yaml"
echo
