#!/usr/bin/env bash
# =============================================================================
# MiQroForge 2.0 — Install kubectl
# 安装最新稳定版 kubectl（Linux/macOS）
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "  ${BLUE}ℹ $1${NC}"; }
success() { echo -e "  ${GREEN}✔ $1${NC}"; }
error()   { echo -e "  ${RED}✘ $1${NC}" >&2; exit 1; }

if command -v kubectl &>/dev/null; then
    success "kubectl 已安装，跳过。"
    exit 0
fi

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case "${ARCH}" in
    x86_64)  ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) error "不支持的架构: ${ARCH}" ;;
esac

info "获取最新稳定版本号..."
KUBECTL_VERSION=$(curl -fsSL https://dl.k8s.io/release/stable.txt)
info "下载 kubectl ${KUBECTL_VERSION} (${OS}/${ARCH})..."

DOWNLOAD_URL="https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/${OS}/${ARCH}/kubectl"
curl -fsSLo /tmp/kubectl "${DOWNLOAD_URL}"

# 校验（可选，下载 checksum 文件验证）
curl -fsSLo /tmp/kubectl.sha256 "${DOWNLOAD_URL}.sha256"
echo "$(cat /tmp/kubectl.sha256)  /tmp/kubectl" | sha256sum --check --quiet \
    || error "kubectl 校验失败，下载可能已损坏。"

chmod +x /tmp/kubectl
sudo mv /tmp/kubectl /usr/local/bin/kubectl
rm -f /tmp/kubectl.sha256

success "kubectl 安装完成：$(kubectl version --client --short 2>/dev/null || kubectl version --client)"
