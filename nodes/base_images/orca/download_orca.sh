#!/usr/bin/env bash
# =============================================================================
# download_orca.sh — 引导用户获取 ORCA 6.1 并放置到正确路径
#
# ORCA 是学术免费软件，但 EULA 禁止再分发。本脚本：
#   1. 呈现学术用途声明，要求用户明确同意
#   2. 检测当前系统架构并推荐合适的 ORCA 版本
#   3. 引导用户从官方论坛获取 tarball
#   4. 将 tarball 放置到本目录（nodes/base_images/orca/）供后续构建使用
#
# 用法（从项目根目录运行）：
#   bash nodes/base_images/orca/download_orca.sh
#   bash nodes/base_images/orca/download_orca.sh --build      # 下载完成后自动触发镜像构建
#   bash nodes/base_images/orca/download_orca.sh --version 6.1.0  # 指定版本（默认 6.1.0）
# =============================================================================
set -euo pipefail

# ── 颜色与格式 ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'
DIM='\033[2m'; NC='\033[0m'

_info()    { echo -e "  ${BLUE}ℹ  $*${NC}"; }
_ok()      { echo -e "  ${GREEN}✔  $*${NC}"; }
_warn()    { echo -e "  ${YELLOW}⚠  $*${NC}"; }
_error()   { echo -e "\n  ${RED}✘  $*${NC}\n" >&2; exit 1; }
_section() { echo -e "\n${BOLD}${CYAN}── $* ${NC}"; }
_prompt()  { echo -e -n "  ${BOLD}$*${NC} "; }
_dim()     { echo -e "  ${DIM}$*${NC}"; }
_blank()   { echo; }

# ── 路径计算 ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ORCA_BUILD_DIR="${SCRIPT_DIR}"

# ── 默认参数 ────────────────────────────────────────────────────────────────
ORCA_VERSION="6.1.0"
AUTO_BUILD=false

for arg in "$@"; do
    case "$arg" in
        --build)      AUTO_BUILD=true ;;
        --version)    shift; ORCA_VERSION="$1" ;;
        --version=*)  ORCA_VERSION="${arg#*=}" ;;
        -h|--help)
            echo "用法: bash nodes/base_images/orca/download_orca.sh [--build] [--version X.Y.Z]"
            exit 0 ;;
        *) _warn "未知参数: $arg（忽略）" ;;
    esac
done

VER_UNDERSCORED="${ORCA_VERSION//./_}"
FORUM_URL="https://orcaforum.kofo.mpg.de"
DOWNLOAD_SECTION_URL="https://orcaforum.kofo.mpg.de/app.php/dlext/"

# ── tarball 文件名模式与示例（按 arch 变体集中管理）────────────────────────
# ORCA 6.1 实际命名规律（以 x86-64 为例）：
#   通用  : orca_6_1_0_linux_x86-64_shared_openmpi418.tar.xz
#   AVX2  : orca_6_1_0_linux_x86-64_shared_openmpi418_avx2.tar.xz
#            （注意：avx2 在 openmpi 版本号之后，而非之前）
_set_tarball_meta() {
    case "$ARCH_VARIANT" in
        x86-64_avx2)
            # avx2 可能出现在 openmpi 版本号前（旧格式）或后（6.1 实际格式），用宽 glob
            TARBALL_PATTERN="orca_${VER_UNDERSCORED}_linux_x86-64*avx2*.tar.*"
            TARBALL_EXAMPLE="orca_${VER_UNDERSCORED}_linux_x86-64_shared_openmpi418_avx2.tar.xz"
            ;;
        x86-64)
            TARBALL_PATTERN="orca_${VER_UNDERSCORED}_linux_x86-64_shared_openmpi*.tar.*"
            TARBALL_EXAMPLE="orca_${VER_UNDERSCORED}_linux_x86-64_shared_openmpi418.tar.xz"
            ;;
        arm64)
            TARBALL_PATTERN="orca_${VER_UNDERSCORED}_linux_arm64*.tar.*"
            TARBALL_EXAMPLE="orca_${VER_UNDERSCORED}_linux_arm64_shared_openmpi418.tar.xz"
            ;;
        riscv64)
            TARBALL_PATTERN="orca_${VER_UNDERSCORED}_linux_riscv64*.tar.*"
            TARBALL_EXAMPLE="orca_${VER_UNDERSCORED}_linux_riscv64_shared_openmpi418.tar.xz"
            ;;
        *)
            TARBALL_PATTERN="orca_${VER_UNDERSCORED}_linux_${ARCH_VARIANT}*.tar.*"
            TARBALL_EXAMPLE="orca_${VER_UNDERSCORED}_linux_${ARCH_VARIANT}_shared_openmpi418.tar.xz"
            ;;
    esac
}

# ── 系统架构检测（在 banner 前静默完成）────────────────────────────────────
_detect_arch() {
    local machine
    machine="$(uname -m)"

    case "$machine" in
        x86_64)
            # 检查 AVX2 支持：Linux 读 /proc/cpuinfo，macOS 用 sysctl
            local has_avx2=false
            if [[ -f /proc/cpuinfo ]] && grep -q avx2 /proc/cpuinfo 2>/dev/null; then
                has_avx2=true
            elif command -v sysctl &>/dev/null \
                 && sysctl -n machdep.cpu.leaf7_features 2>/dev/null | grep -qi avx2; then
                has_avx2=true
            fi

            if [[ "$has_avx2" == "true" ]]; then
                ARCH_LABEL="x86-64 (AVX2)"
                ARCH_VARIANT="x86-64_avx2"       # ORCA 文件名中的 arch 段
                ARCH_RECOMMEND="推荐 ✔"
                ARCH_NOTE="您的 CPU 支持 AVX2 指令集，AVX2 版本运算速度更快，强烈推荐。"
                ARCH_FALLBACK="若 AVX2 版本不可用，可退而选择通用 x86-64 版本。"
            else
                ARCH_LABEL="x86-64 (通用)"
                ARCH_VARIANT="x86-64"
                ARCH_RECOMMEND="推荐 ✔"
                ARCH_NOTE="您的 CPU 不支持 AVX2 指令集，请选择通用 x86-64 版本。"
                ARCH_FALLBACK=""
            fi
            ;;
        aarch64|arm64)
            ARCH_LABEL="ARM64 / AArch64"
            ARCH_VARIANT="arm64"
            ARCH_RECOMMEND="推荐 ✔"
            ARCH_NOTE="检测到 ARM64 架构（如 Apple M 系列、AWS Graviton、树莓派 4 等）。"
            ARCH_FALLBACK=""
            ;;
        riscv64)
            ARCH_LABEL="RISC-V 64"
            ARCH_VARIANT="riscv64"
            ARCH_RECOMMEND="推荐 ✔"
            ARCH_NOTE="检测到 RISC-V 64 架构。请注意 ORCA 对该平台的支持可能处于实验阶段。"
            ARCH_FALLBACK=""
            ;;
        *)
            ARCH_LABEL="未知（${machine}）"
            ARCH_VARIANT="x86-64"
            ARCH_RECOMMEND="猜测"
            ARCH_NOTE="无法识别当前架构，默认推荐通用 x86-64 版本，请根据实际情况调整。"
            ARCH_FALLBACK=""
            ;;
    esac

    # 根据架构生成 tarball 文件名的 glob 模式和示例
    _set_tarball_meta
}

_detect_arch

# ═══════════════════════════════════════════════════════════════════════════
#  BANNER
# ═══════════════════════════════════════════════════════════════════════════
clear
echo
echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║         MiQroForge 2.0 — ORCA ${ORCA_VERSION} 下载向导                     ║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1: 学术用途声明（用户必须明确同意）
# ═══════════════════════════════════════════════════════════════════════════
_section "STEP 1  学术用途声明与许可协议确认"
_blank

echo -e "  ORCA 是由 Frank Neese 教授（马克斯-普朗克研究所）开发的量子化学软件。"
echo -e "  官方网站：${CYAN}https://www.faccts.de/orca/${NC}"
_blank
echo -e "  ${BOLD}许可证关键条款摘要（须全文遵守 ORCA EULA）：${NC}"
_blank
echo -e "  ${GREEN}✔  允许${NC}  非商业学术研究与教育目的的免费使用"
echo -e "  ${GREEN}✔  允许${NC}  在本机构内部计算集群上部署和使用"
echo -e "  ${RED}✘  禁止${NC}  将 ORCA 二进制文件上传至任何公开镜像仓库或存储服务"
echo -e "  ${RED}✘  禁止${NC}  将 ORCA 转让、分发或共享给任何第三方"
echo -e "  ${RED}✘  禁止${NC}  任何商业用途（需向 FACCTs GmbH 购买商业许可）"
echo -e "  ${RED}✘  禁止${NC}  将包含 ORCA 的 Docker 镜像推送到公开容器仓库"
_blank
_dim   "  完整 EULA 可在下载后查阅，或访问：https://www.faccts.de/docs/orca/6.1/manual/"
_blank

echo -e "  ${BOLD}${YELLOW}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${BOLD}${YELLOW}║                    ⚠  学术用途声明                              ║${NC}"
echo -e "  ${BOLD}${YELLOW}╠══════════════════════════════════════════════════════════════════╣${NC}"
echo -e "  ${BOLD}${YELLOW}║                                                                  ║${NC}"
echo -e "  ${BOLD}${YELLOW}║  我声明：                                                        ║${NC}"
echo -e "  ${BOLD}${YELLOW}║  1. 我已阅读并同意遵守 ORCA 最终用户许可协议 (EULA) 的全部条款  ║${NC}"
echo -e "  ${BOLD}${YELLOW}║  2. 我仅将 ORCA 用于非商业学术研究或教育目的                    ║${NC}"
echo -e "  ${BOLD}${YELLOW}║  3. 我不会将 ORCA 二进制文件或包含 ORCA 的镜像公开分发          ║${NC}"
echo -e "  ${BOLD}${YELLOW}║  4. 我已在 ORCA 官方论坛注册个人账号，并使用个人账号下载        ║${NC}"
echo -e "  ${BOLD}${YELLOW}║                                                                  ║${NC}"
echo -e "  ${BOLD}${YELLOW}╚══════════════════════════════════════════════════════════════════╝${NC}"
_blank

_prompt "请输入 AGREE 确认以上声明（其他任何输入将退出）："
read -r user_confirm

if [[ "$user_confirm" != "AGREE" ]]; then
    _blank
    _warn "未确认，退出。如需继续，请输入 AGREE。"
    _blank
    exit 0
fi

_ok "声明已确认，继续下一步。"

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 2: 系统架构检测与版本推荐
# ═══════════════════════════════════════════════════════════════════════════
_section "STEP 2  系统架构检测与版本推荐"
_blank

echo -e "  ORCA ${ORCA_VERSION} 提供以下平台版本，请根据您的集群选择正确的包："
_blank

# 显示所有可用版本，高亮推荐项
_print_variant() {
    local variant="$1" label="$2" note="$3" is_recommended="$4"
    if [[ "$is_recommended" == "yes" ]]; then
        echo -e "  ${GREEN}${BOLD}▶  ${label}${NC}  ${GREEN}← ${ARCH_RECOMMEND}（本机）${NC}"
        echo -e "     ${DIM}${note}${NC}"
    else
        echo -e "     ${DIM}${label}${NC}"
    fi
}

_print_variant "x86-64"      "x86-64        — 通用 x86-64，兼容性最广"      "" \
    "$( [[ "$ARCH_VARIANT" == "x86-64" ]] && echo yes || echo no )"
_print_variant "x86-64_avx2" "x86-64 (AVX2) — 需要 AVX2 指令集，性能更优"  "" \
    "$( [[ "$ARCH_VARIANT" == "x86-64_avx2" ]] && echo yes || echo no )"
_print_variant "arm64"       "ARM64         — Apple M 系列 / AWS Graviton"   "" \
    "$( [[ "$ARCH_VARIANT" == "arm64" ]] && echo yes || echo no )"
_print_variant "riscv64"     "RISC-V 64     — 实验性支持"                     "" \
    "$( [[ "$ARCH_VARIANT" == "riscv64" ]] && echo yes || echo no )"

_blank
_info "检测结果：当前系统架构为 ${BOLD}${ARCH_LABEL}${NC}"
_info "${ARCH_NOTE}"
[[ -n "$ARCH_FALLBACK" ]] && _warn "$ARCH_FALLBACK"
_blank
_info "推荐下载的文件名示例："
echo -e "     ${CYAN}${TARBALL_EXAMPLE}${NC}"
_blank
_warn "注意：上述推荐基于本机架构。若您为远程集群构建镜像，请根据集群实际架构选择。"
_blank
_prompt "推荐版本是否正确？(Y/n，输入 n 可手动指定):"
read -r arch_confirm

if [[ "$arch_confirm" =~ ^[Nn]$ ]]; then
    _blank
    echo -e "  请选择目标架构："
    echo -e "  ${BOLD}[1]${NC} x86-64        （通用，兼容性最广）"
    echo -e "  ${BOLD}[2]${NC} x86-64 (AVX2) （需 AVX2，性能更优）"
    echo -e "  ${BOLD}[3]${NC} ARM64"
    echo -e "  ${BOLD}[4]${NC} RISC-V 64"
    _blank
    _prompt "请选择 (1-4):"
    read -r arch_choice
    case "$arch_choice" in
        1) ARCH_VARIANT="x86-64";       ARCH_LABEL="x86-64 (通用)" ;;
        2) ARCH_VARIANT="x86-64_avx2";  ARCH_LABEL="x86-64 (AVX2)" ;;
        3) ARCH_VARIANT="arm64";         ARCH_LABEL="ARM64" ;;
        4) ARCH_VARIANT="riscv64";       ARCH_LABEL="RISC-V 64" ;;
        *) _warn "无效选择，保留自动检测结果：${ARCH_LABEL}" ;;
    esac
    # 重新生成模式和示例
    _set_tarball_meta
fi

_ok "已选择架构：${ARCH_LABEL}"
_info "将搜索文件名模式：${TARBALL_PATTERN}"

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 3: 检查是否已有 tarball
# ═══════════════════════════════════════════════════════════════════════════
_section "STEP 3  检查本地文件"

EXISTING_TARBALL=""
for f in "${ORCA_BUILD_DIR}"/${TARBALL_PATTERN}; do
    [[ -f "$f" ]] && EXISTING_TARBALL="$f" && break
done

# 也扫描当前目录和常用下载目录
for search_dir in "$(pwd)" "${HOME}/Downloads" "${HOME}/桌面" "${HOME}/Desktop"; do
    [[ -d "$search_dir" ]] || continue
    for f in "${search_dir}"/${TARBALL_PATTERN}; do
        [[ -f "$f" ]] && EXISTING_TARBALL="$f" && break 2
    done
done

if [[ -n "$EXISTING_TARBALL" ]]; then
    _ok "发现已有 ORCA 文件：$(basename "$EXISTING_TARBALL")"
    _info "路径：${EXISTING_TARBALL}"
    _blank
    _prompt "是否使用此文件？(y/N):"
    read -r use_existing
    if [[ "$use_existing" =~ ^[Yy]$ ]]; then
        DEST="${ORCA_BUILD_DIR}/$(basename "$EXISTING_TARBALL")"
        if [[ "$EXISTING_TARBALL" != "$DEST" ]]; then
            _info "复制文件到构建目录..."
            cp "$EXISTING_TARBALL" "$DEST"
        fi
        _ok "文件已就位：${DEST}"
        PLACED_TARBALL="$DEST"
        SKIP_DOWNLOAD=true
    else
        SKIP_DOWNLOAD=false
    fi
else
    _info "未在常用路径发现匹配的 ORCA ${ORCA_VERSION} (${ARCH_LABEL}) tarball，将引导您获取。"
    SKIP_DOWNLOAD=false
fi

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 4: 下载引导（如果没有现成文件）
# ═══════════════════════════════════════════════════════════════════════════
if [[ "${SKIP_DOWNLOAD:-false}" != "true" ]]; then

    _section "STEP 4  从 ORCA 官方论坛获取 tarball"
    _blank
    _info "ORCA ${ORCA_VERSION} 需要从官方论坛下载，请按以下步骤操作："
    _blank
    echo -e "  ${BOLD}1.${NC} 在浏览器中打开 ORCA 官方论坛并登录您的账号："
    echo -e "     ${CYAN}${FORUM_URL}${NC}"
    _blank
    echo -e "  ${BOLD}2.${NC} 进入下载页面（Downloads → ORCA ${ORCA_VERSION}）："
    echo -e "     ${CYAN}${DOWNLOAD_SECTION_URL}${NC}"
    _blank
    echo -e "  ${BOLD}3.${NC} 根据您的架构选择对应包："
    echo -e "     目标架构：${GREEN}${BOLD}${ARCH_LABEL}${NC}"
    echo -e "     文件名示例：${CYAN}${TARBALL_EXAMPLE}${NC}"
    [[ -n "$ARCH_FALLBACK" ]] && echo -e "     ${YELLOW}备选：${ARCH_FALLBACK}${NC}"
    _blank

    # 尝试在终端打开浏览器（适配多种环境）
    if command -v xdg-open &>/dev/null; then
        _prompt "是否立即用浏览器打开下载页面？(Y/n):"
        read -r open_browser
        if [[ ! "$open_browser" =~ ^[Nn]$ ]]; then
            xdg-open "${DOWNLOAD_SECTION_URL}" 2>/dev/null &
            _ok "已在浏览器中打开下载页面"
        fi
    elif command -v open &>/dev/null; then
        open "${DOWNLOAD_SECTION_URL}" 2>/dev/null &
        _ok "已在浏览器中打开下载页面"
    else
        _warn "无法自动打开浏览器，请手动访问上方链接"
    fi

    _blank
    echo -e "  ${BOLD}获取文件的两种方式，请选择：${NC}"
    _blank
    echo -e "  ${BOLD}[A]${NC} 手动下载  — 用浏览器下载完毕后，告诉我文件路径"
    echo -e "  ${BOLD}[B]${NC} URL 粘贴  — 从浏览器复制下载链接，由本脚本 wget 下载"
    _blank
    _prompt "请选择 (A/B) [默认: A]:"
    read -r dl_method
    dl_method="${dl_method:-A}"

    case "${dl_method^^}" in

        # ── 方式 A：用户手动下载，输入文件路径 ───────────────────────────
        A)
            _blank
            _info "请在浏览器中完成下载，然后回到此终端。"
            _blank

            while true; do
                _prompt "请输入下载完成的 tarball 完整路径（或直接拖拽文件到终端）:"
                read -r user_path
                # 去掉可能的转义空格和引号
                user_path="${user_path//\\ / }"
                user_path="${user_path//\'/}"
                user_path="${user_path//\"/}"
                # 展开 ~
                user_path="${user_path/#\~/$HOME}"

                if [[ -f "$user_path" ]]; then
                    _ok "找到文件：$(basename "$user_path")"
                    _info "文件大小：$(du -sh "$user_path" | cut -f1)"
                    break
                else
                    _warn "文件不存在：${user_path}"
                    _prompt "重新输入？(Y/n):"
                    read -r retry
                    [[ "$retry" =~ ^[Nn]$ ]] && _error "放弃获取文件，退出。"
                fi
            done

            DEST="${ORCA_BUILD_DIR}/$(basename "$user_path")"
            if [[ "$user_path" != "$DEST" ]]; then
                _info "复制文件到构建目录..."
                cp "$user_path" "$DEST"
            fi
            PLACED_TARBALL="$DEST"
            _ok "文件已就位：${PLACED_TARBALL}"
            ;;

        # ── 方式 B：用户粘贴 URL，wget 下载 ──────────────────────────────
        B)
            _blank
            _info "请在浏览器登录论坛后，右键点击下载链接 → 复制链接地址。"
            _warn "注意：该链接通常包含您的会话 token，请勿泄露给他人。"
            _blank
            _prompt "请粘贴下载 URL:"
            read -r dl_url

            if [[ -z "$dl_url" ]]; then
                _error "未输入 URL，退出。"
            fi

            # 尝试从 URL 推断文件名
            url_filename="$(basename "${dl_url%%\?*}")"
            if [[ "$url_filename" != *.tar.* ]]; then
                _warn "无法从 URL 自动推断文件名。"
                _prompt "请输入保存的文件名（例如 ${TARBALL_EXAMPLE}）:"
                read -r url_filename
            fi

            DEST="${ORCA_BUILD_DIR}/${url_filename}"

            _info "开始下载：${url_filename}"
            _info "目标路径：${DEST}"
            _blank

            # 检查 wget / curl 可用性
            if command -v wget &>/dev/null; then
                wget \
                    --show-progress \
                    --retry-connrefused \
                    --tries=3 \
                    --timeout=30 \
                    -O "$DEST" \
                    "$dl_url" \
                || _error "wget 下载失败，请检查链接是否有效（链接可能已过期，需重新从论坛复制）"
            elif command -v curl &>/dev/null; then
                curl \
                    --location \
                    --retry 3 \
                    --retry-delay 5 \
                    --progress-bar \
                    -o "$DEST" \
                    "$dl_url" \
                || _error "curl 下载失败，请检查链接是否有效"
            else
                _error "未找到 wget 或 curl，请手动安装后重试：sudo apt install wget"
            fi

            PLACED_TARBALL="$DEST"
            _ok "下载完成：$(basename "$PLACED_TARBALL")"
            ;;

        *)
            _error "无效选择。请重新运行脚本并选择 A 或 B。"
            ;;
    esac
fi

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 5: 验证 tarball
# ═══════════════════════════════════════════════════════════════════════════
_section "STEP 5  验证文件完整性"

if [[ -z "${PLACED_TARBALL:-}" ]] || [[ ! -f "$PLACED_TARBALL" ]]; then
    _error "文件路径无效，请重新运行脚本。"
fi

FILE_SIZE_MB=$(du -sm "$PLACED_TARBALL" | cut -f1)
_info "文件大小：${FILE_SIZE_MB} MiB"

# ORCA 完整包通常大于 400 MiB
if (( FILE_SIZE_MB < 100 )); then
    _warn "文件过小（${FILE_SIZE_MB} MiB），ORCA 完整包通常 > 400 MiB"
    _warn "可能下载不完整或文件有误，建议重新下载。"
    _blank
    _prompt "仍然继续？(y/N):"
    read -r force_continue
    [[ "$force_continue" =~ ^[Yy]$ ]] || exit 1
fi

# 验证 tar 归档完整性（仅检查结构，不解压）
_info "校验 tar 归档结构..."
if tar tf "$PLACED_TARBALL" &>/dev/null; then
    _ok "tar 归档结构完整"
else
    _error "tar 校验失败，文件可能损坏。请重新下载。"
fi

# 简单检查包内是否含 orca 可执行文件
if tar tf "$PLACED_TARBALL" 2>/dev/null | grep -qE '(^|/)orca$'; then
    _ok "包内找到 orca 可执行文件"
else
    _warn "未在 tarball 中明确找到 orca 可执行文件（可能在子目录，构建时会自动处理）"
fi

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 6: 显示摘要
# ═══════════════════════════════════════════════════════════════════════════
_section "STEP 6  摘要"
_blank
_ok "ORCA ${ORCA_VERSION} tarball 已就绪："
echo
echo -e "    ${BOLD}文件：${NC}$(basename "$PLACED_TARBALL")"
echo -e "    ${BOLD}架构：${NC}${ARCH_LABEL}"
echo -e "    ${BOLD}位置：${NC}${PLACED_TARBALL}"
echo -e "    ${BOLD}大小：${NC}${FILE_SIZE_MB} MiB"
_blank

# ── 下一步提示 ────────────────────────────────────────────────────────────
BUILD_SCRIPT="${PROJECT_ROOT}/nodes/base_images/orca/build.sh"
if [[ "$AUTO_BUILD" == "true" ]]; then
    _section "自动触发镜像构建"
    _blank
    if [[ -f "$BUILD_SCRIPT" ]]; then
        bash "$BUILD_SCRIPT"
    else
        _warn "未找到 build.sh，请手动运行："
        echo "    bash nodes/base_images/orca/build.sh"
    fi
else
    echo -e "  ${BOLD}下一步：${NC}构建 Docker 镜像"
    _blank
    echo -e "      bash nodes/base_images/orca/build.sh"
    _blank
    echo -e "  ${BOLD}⚠  提醒：${NC}请勿将包含 ORCA 的镜像推送到任何公开仓库（Docker Hub 等）"
fi

_blank
echo -e "${GREEN}${BOLD}  ══ 完成 ══${NC}"
_blank
