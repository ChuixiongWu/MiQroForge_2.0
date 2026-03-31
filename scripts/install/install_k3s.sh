#!/usr/bin/env bash
# =============================================================================
# MiQroForge 2.0 — Install k3s (轻量级本地 Kubernetes，仅用于开发/测试)
#
# ⚠ 生产环境请使用正式 K8s 集群，配置好 kubeconfig 后无需运行此脚本。
#
# 安装后：
#   - kubeconfig 写入 /etc/rancher/k3s/k3s.yaml
#   - 本脚本将其复制到 ~/.kube/config 以便 kubectl 直接使用
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "  ${BLUE}ℹ $1${NC}"; }
success() { echo -e "  ${GREEN}✔ $1${NC}"; }
warn()    { echo -e "  ${YELLOW}⚠ $1${NC}"; }
error()   { echo -e "  ${RED}✘ $1${NC}" >&2; exit 1; }

# 若集群已可达则跳过
if kubectl cluster-info &>/dev/null 2>&1; then
    success "Kubernetes 集群已可达，跳过 k3s 安装。"
    exit 0
fi

warn "此脚本将在本机安装 k3s 单节点集群（开发用途）。"
echo -e "  生产环境请 ${BOLD}跳过此步骤${NC}，直接配置 kubeconfig 指向正式集群。"

info "下载并安装 k3s（优先使用国内镜像源）..."
if curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh \
    | INSTALL_K3S_MIRROR=cn sh - ; then
    info "已通过国内镜像源安装。"
else
    warn "国内镜像源失败，尝试官方源..."
    curl -sfL https://get.k3s.io | sh -
fi

# 等待节点就绪（最多 60 秒）
info "等待 k3s 节点就绪..."
for i in $(seq 1 12); do
    if sudo k3s kubectl get node &>/dev/null 2>&1; then
        break
    fi
    sleep 5
    echo -n "."
done
echo

# 配置 kubeconfig
KUBECONFIG_SRC="/etc/rancher/k3s/k3s.yaml"
KUBECONFIG_DST="${HOME}/.kube/config"

if [[ -f "${KUBECONFIG_SRC}" ]]; then
    mkdir -p "${HOME}/.kube"
    # 备份已有 config
    if [[ -f "${KUBECONFIG_DST}" ]]; then
        cp "${KUBECONFIG_DST}" "${KUBECONFIG_DST}.bak.$(date +%Y%m%d%H%M%S)"
        warn "已备份原有 kubeconfig 到 ${KUBECONFIG_DST}.bak.*"
    fi
    sudo cp "${KUBECONFIG_SRC}" "${KUBECONFIG_DST}"
    sudo chown "${USER}:${USER}" "${KUBECONFIG_DST}"
    chmod 600 "${KUBECONFIG_DST}"
    success "kubeconfig 已写入 ${KUBECONFIG_DST}"
else
    warn "未找到 k3s kubeconfig，请手动配置：sudo cat ${KUBECONFIG_SRC} > ${KUBECONFIG_DST}"
fi

success "k3s 安装完成。"
kubectl get nodes
