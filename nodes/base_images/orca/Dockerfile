# =============================================================================
# ORCA 6.1 Docker Image — BYOB (Bring Your Own Binary)，多阶段构建
#
# ORCA 为学术免费软件，但不可再分发。用户需要：
#   1. 在 https://orcaforum.kofo.mpg.de/ 注册并下载 ORCA 6.1
#   2. 将 tarball 放到本目录，文件名示例：
#        orca_6_1_0_linux_x86-64_shared_openmpi418_avx2.tar.xz  （AVX2 版）
#        orca_6_1_0_linux_x86-64_shared_openmpi418.tar.xz       （通用版）
#   3. 运行 nodes/base_images/orca/build.sh 构建镜像
#
# 构建命令（由 build_orca_image.sh 自动调用）：
#   docker build -t harbor.era.local/library/orca:6.1 \
#     --build-arg ORCA_TARBALL=orca_6_1_0_linux_x86-64_shared_openmpi418_avx2.tar.xz \
#     nodes/base_images/orca/
# =============================================================================

ARG ORCA_TARBALL=orca_6_1_0_linux_x86-64_shared_openmpi418_avx2.tar.xz

# ═════════════════════════════════════════════════════════════════════════════
# Stage 1: builder — 仅用于解压 tarball，不进入最终镜像
# 这样 tarball 本身（0.5GB）不会作为层留在最终镜像里
# ═════════════════════════════════════════════════════════════════════════════
FROM ubuntu:22.04 AS builder

ARG ORCA_TARBALL

RUN apt-get update \
    && apt-get install -y --no-install-recommends xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY ${ORCA_TARBALL} /tmp/orca.tar.xz
RUN mkdir -p /opt/orca \
    && tar xf /tmp/orca.tar.xz -C /opt/orca --strip-components=1 \
    && chmod +x /opt/orca/orca*

# ═════════════════════════════════════════════════════════════════════════════
# Stage 2: runtime — 仅包含运行时依赖，体积最小
# ═════════════════════════════════════════════════════════════════════════════
FROM ubuntu:22.04

# ── 运行时依赖（不含编译器/开发头文件）────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenMPI 运行时（shared_openmpi 版 ORCA 需要）
    libopenmpi3 \
    openmpi-bin \
    # 数学库运行时
    liblapack3 \
    libblas3 \
    # Python 后处理（orca-thermo-extractor 用）
    python3 \
    python3-pip \
    # 其他工具
    bc \
    && rm -rf /var/lib/apt/lists/*

# ── 从 builder 拷贝已解压的 ORCA（不带 tarball 层）────────────────────────
COPY --from=builder /opt/orca /opt/orca

# ── 环境变量 ──────────────────────────────────────────────────────────────────
ENV PATH="/opt/orca:${PATH}"
ENV LD_LIBRARY_PATH="/opt/orca"

# ── Python 后处理依赖 ──────────────────────────────────────────────────────
RUN pip3 install --no-cache-dir numpy

# ── MiQroForge 工作目录约定 ────────────────────────────────────────────────
RUN mkdir -p /mf/profile /mf/input /mf/output /mf/workdir

WORKDIR /mf/workdir

# ── 验证安装 ──────────────────────────────────────────────────────────────────
# ORCA 不支持 --version，无参数运行会输出启动信息后报缺少输入文件，属正常现象
RUN /opt/orca/orca 2>&1 | grep -q "Starting time" \
    && echo "[OK] ORCA binary verified" \
    || echo "[WARN] Could not verify ORCA binary, check tarball"

LABEL maintainer="MiQroForge Team" \
      software="orca" \
      version="6.1" \
      description="ORCA 6.1 quantum chemistry + OpenMPI 4.1.8"
