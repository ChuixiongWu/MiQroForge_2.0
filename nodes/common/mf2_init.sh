#!/usr/bin/env bash
# =============================================================================
# MiQroForge 2.0 — 节点运行时公共库  (nodes/common/mf2_init.sh)
#
# 编译器在构建 ConfigMap 时自动将本文件注入到每个节点的 profile 目录，
# 节点的 run.sh 在脚本顶部通过以下方式引入：
#
#   source /mf/profile/mf2_init.sh
#
# 提供：
#   标准目录变量  INPUT_DIR / OUTPUT_DIR / WORKDIR / PROFILE_DIR
#   mf_param()    读取 on-board 参数，文件不存在或为空时返回默认值
#   mf_banner()   打印节点启动横幅（节点名 + 描述 + UTC 时间戳）
#   mf_write_xyz() 将 XYZ 几何字符串写入 workdir/input.xyz，
#                  自动适配标准 XYZ 格式与纯原子行格式
# =============================================================================

# ── 标准目录 ──────────────────────────────────────────────────────────────────
INPUT_DIR="/mf/input"
OUTPUT_DIR="/mf/output"
WORKDIR="/mf/workdir"
PROFILE_DIR="/mf/profile"
WORKSPACE_DIR="/mf/workspace"

mkdir -p "$OUTPUT_DIR" "$WORKDIR"

# ── mf_param ──────────────────────────────────────────────────────────────────
# 读取 /mf/input/<name> 的内容（去除 Windows 换行符）。
# 文件不存在、无法读取或内容为空时返回 <default>。
#
# 用法：VALUE=$(mf_param <param-name> <default>)
#
# 示例：
#   METHOD=$(mf_param method B3LYP)
#   CHARGE=$(mf_param charge 0)
mf_param() {
    local name="$1"
    local default="${2:-}"
    if [[ -f "${INPUT_DIR}/${name}" ]]; then
        local val
        val=$(tr -d '\r' < "${INPUT_DIR}/${name}")
        echo "${val:-${default}}"
    else
        echo "${default}"
    fi
}

# ── mf_banner ─────────────────────────────────────────────────────────────────
# 打印节点启动横幅，包含节点 ID、任务描述、UTC 时间戳。
# 建议在读取参数之前调用，作为 run.sh 的第一个输出。
#
# 用法：mf_banner <node-id> [description]
#
# 示例：
#   mf_banner "orca-geo-opt" "DFT geometry optimization"
mf_banner() {
    local node_id="$1"
    local desc="${2:-}"
    local ts
    ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo "N/A")
    local line="================================================================"
    echo ""
    echo "  ${line}"
    echo "    MiQroForge 2.0 — Node Bootstrap"
    echo "  ${line}"
    printf "    Node : %s\n" "${node_id}"
    [[ -n "$desc" ]] && printf "    Task : %s\n" "${desc}"
    printf "    Time : %s\n" "${ts}"
    echo "  ${line}"
    echo ""
}

# ── mf_write_xyz ──────────────────────────────────────────────────────────────
# 将 XYZ 几何字符串写入 ${WORKDIR}/input.xyz。
# 自动识别并适配两种常见格式：
#
#   标准 XYZ：第 1 行为原子数（纯整数），第 2 行为注释，其余为坐标行
#   纯原子行：直接以元素符号开头，本函数自动统计原子数并补充文件头
#
# 用法：mf_write_xyz "$XYZ_GEOMETRY" [node-id]
#
# 示例：
#   XYZ_GEOMETRY=$(mf_param xyz_geometry "")
#   mf_write_xyz "$XYZ_GEOMETRY" "orca-single-point"
mf_write_xyz() {
    local xyz_content="$1"
    local node_id="${2:-node}"
    local first_line
    first_line=$(echo "${xyz_content}" | head -1 | tr -d '[:space:]')
    if echo "${first_line}" | grep -qE '^[0-9]+$'; then
        printf '%s\n' "${xyz_content}" > "${WORKDIR}/input.xyz"
        echo "[${node_id}] XYZ: standard format (${first_line} atoms)"
    else
        local n_atoms
        n_atoms=$(echo "${xyz_content}" | grep -cE '^\s*[A-Za-z]' || true)
        printf '%d\nGeometry input (MiQroForge)\n%s\n' \
            "${n_atoms}" "${xyz_content}" > "${WORKDIR}/input.xyz"
        echo "[${node_id}] XYZ: atom-only format, added header (${n_atoms} atoms)"
    fi
}

# ── 自动加载节点参数 ───────────────────────────────────────────────────────────
# 编译器为每个节点生成 mf_node_params.sh，内含所有 onboard_inputs 的变量赋值。
# 直接在 source mf2_init.sh 的同时完成参数加载，run.sh 无需手写任何 mf_param 调用。
# shellcheck source=/dev/null
[[ -f "${PROFILE_DIR}/mf_node_params.sh" ]] && source "${PROFILE_DIR}/mf_node_params.sh"
