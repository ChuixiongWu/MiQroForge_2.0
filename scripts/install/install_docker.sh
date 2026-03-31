#!/usr/bin/env bash
# =============================================================================
# MiQroForge 2.0 — Install Docker
# 支持：Ubuntu/Debian, CentOS/RHEL/Rocky, Arch Linux
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "  ${BLUE}ℹ $1${NC}"; }
success() { echo -e "  ${GREEN}✔ $1${NC}"; }
error()   { echo -e "  ${RED}✘ $1${NC}" >&2; exit 1; }

if command -v docker &>/dev/null; then
    success "Docker 已安装 ($(docker --version | grep -oP '[\d.]+' | head -1))，跳过。"
    exit 0
fi

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "${ID}"
    else
        uname -s | tr '[:upper:]' '[:lower:]'
    fi
}

OS=$(detect_os)
info "检测到操作系统：${OS}"

case "${OS}" in
    ubuntu|debian)
        info "使用 apt 安装 Docker..."
        sudo apt-get update -qq
        sudo apt-get install -y ca-certificates curl gnupg lsb-release

        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/${OS}/gpg \
            | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg

        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/${OS} $(lsb_release -cs) stable" \
            | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        sudo apt-get update -qq
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
            docker-buildx-plugin docker-compose-plugin
        ;;

    centos|rhel|rocky|almalinux|fedora)
        info "使用 dnf/yum 安装 Docker..."
        sudo dnf -y install dnf-plugins-core 2>/dev/null \
            || sudo yum -y install yum-utils
        sudo dnf config-manager --add-repo \
            https://download.docker.com/linux/centos/docker-ce.repo 2>/dev/null \
            || sudo yum-config-manager --add-repo \
            https://download.docker.com/linux/centos/docker-ce.repo
        sudo dnf -y install docker-ce docker-ce-cli containerd.io \
            docker-buildx-plugin docker-compose-plugin 2>/dev/null \
            || sudo yum -y install docker-ce docker-ce-cli containerd.io
        ;;

    arch|manjaro)
        info "使用 pacman 安装 Docker..."
        sudo pacman -Sy --noconfirm docker
        ;;

    darwin)
        error "macOS 请从 https://docs.docker.com/desktop/mac/ 下载 Docker Desktop 手动安装。"
        ;;

    *)
        error "不支持的操作系统: ${OS}。请参考 https://docs.docker.com/engine/install/ 手动安装。"
        ;;
esac

# 启动并设置开机自启
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker "${USER}" || true
success "Docker 安装完成。请重新登录或运行 'newgrp docker' 以使用非 root 权限。"
docker --version
