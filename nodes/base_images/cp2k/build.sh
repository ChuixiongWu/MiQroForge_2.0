#!/usr/bin/env bash
# =============================================================================
# build.sh — 构建 CP2K Docker 镜像（基于官方镜像）
#
# 用法：
#   bash nodes/base_images/cp2k/build.sh
#
# 环境变量：
#   IMAGE_REGISTRY  自定义 registry 前缀（默认 harbor.era.local）
#   REGISTRY_PROJECT  自定义项目名（默认 miqroforge2.0）
#
# 前置条件：
#   docker login harbor.era.local
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LOCAL_NAME="cp2k"
LOCAL_TAG="2025.2"
REGISTRY_PREFIX="${IMAGE_REGISTRY:-harbor.era.local}/${REGISTRY_PROJECT:-miqroforge2.0}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

_info()  { echo -e "  ${BLUE}ℹ  $*${NC}"; }
_ok()    { echo -e "  ${GREEN}✔  $*${NC}"; }
_warn()  { echo -e "  ${YELLOW}⚠  $*${NC}"; }
_error() { echo -e "\n  ${RED}✘  $*${NC}\n" >&2; exit 1; }

# 自动检测 sudo
DOCKER="docker"
if ! docker info &>/dev/null 2>&1; then
    DOCKER="sudo docker"
    $DOCKER info &>/dev/null || _error "Docker 不可用"
fi

echo
echo -e "${BLUE}${BOLD}══ Build CP2K Docker Image ══${NC}"
echo

# ── 1. 构建镜像 ───────────────────────────────────────────────────────────────
_info "构建本地镜像：${LOCAL_NAME}:${LOCAL_TAG}"
echo

$DOCKER build \
    --tag "${LOCAL_NAME}:${LOCAL_TAG}" \
    --no-cache \
    "${SCRIPT_DIR}"

echo
_ok "构建完成：${LOCAL_NAME}:${LOCAL_TAG}"

# ── 2. 验证 ──────────────────────────────────────────────────────────────────
_info "验证 CP2K..."
if $DOCKER run --rm "${LOCAL_NAME}:${LOCAL_TAG}" cp2k.psmp --version 2>&1 | head -3; then
    _ok "CP2K 验证通过"
else
    _warn "未能确认 CP2K 可用，请手动检查"
fi

# ── 3. 推送到 Harbor ─────────────────────────────────────────────────────────
REMOTE_IMAGE="${REGISTRY_PREFIX}/${LOCAL_NAME}:${LOCAL_TAG}"

_info "推送到 ${REMOTE_IMAGE}..."
$DOCKER tag "${LOCAL_NAME}:${LOCAL_TAG}" "${REMOTE_IMAGE}"
$DOCKER push "${REMOTE_IMAGE}"
_ok "推送完成"

echo
_ok "完成！"
echo "  本地镜像：${LOCAL_NAME}:${LOCAL_TAG}"
echo "  Harbor 镜像：${REMOTE_IMAGE}"
echo
