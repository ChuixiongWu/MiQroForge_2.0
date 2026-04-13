#!/usr/bin/env bash
# =============================================================================
# build.sh — 构建并推送临时节点基础镜像 ephemeral-py
#
# 用法：
#   bash nodes/base_images/ephemeral-py/build.sh
#
# 默认推送到 harbor.era.local，可通过 IMAGE_REGISTRY 环境变量覆盖。
# 设置 PUSH=0 只构建不推送。
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE_NAME="${IMAGE_REGISTRY:-harbor.era.local}/library/mf-ephemeral-py"
IMAGE_TAG="3.11"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
PUSH="${PUSH:-1}"

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'

_info() { echo -e "  ${BLUE}ℹ  $*${NC}"; }
_ok()   { echo -e "  ${GREEN}✔  $*${NC}"; }

# 自动检测 sudo
DOCKER="docker"
if ! docker info &>/dev/null 2>&1; then
    DOCKER="sudo docker"
    $DOCKER info &>/dev/null || { echo -e "${RED}Docker 不可用${NC}" >&2; exit 1; }
fi

echo
echo -e "${BLUE}${BOLD}══ Build ephemeral-py Docker Image ══${NC}"
echo

_info "构建镜像：${FULL_IMAGE}"
echo

$DOCKER build \
    --tag "${FULL_IMAGE}" \
    --no-cache \
    "${SCRIPT_DIR}"

echo
_ok "构建完成：${FULL_IMAGE}"

$DOCKER tag "${FULL_IMAGE}" "${IMAGE_NAME}:latest"
_ok "已添加 latest 标签"

_info "验证 Python + numpy + matplotlib..."
$DOCKER run --rm "${FULL_IMAGE}" python -c \
    "import numpy; import matplotlib; import scipy; import pandas; print('All OK')"

if [[ "$PUSH" == "1" ]]; then
    echo
    _info "推送到 ${IMAGE_NAME}..."
    $DOCKER push "${FULL_IMAGE}"
    $DOCKER push "${IMAGE_NAME}:latest"
    _ok "推送完成"
fi

echo
_ok "完成！临时节点将自动使用此镜像。"
echo
