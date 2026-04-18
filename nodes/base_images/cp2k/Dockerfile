# =============================================================================
# CP2K — MiQroForge 周期性 DFT 基础镜像
#
# 基于 cp2k/cp2k 官方 Docker 镜像，仅添加 MF 工作目录约定和环境变量。
#
# 构建：bash nodes/base_images/cp2k/build.sh
# 拉取：docker pull docker.1ms.run/cp2k/cp2k:2025.2_openmpi_x86_64_psmp
# =============================================================================
FROM docker.1ms.run/cp2k/cp2k:2025.2_openmpi_x86_64_psmp

# 安装 Python + numpy（官方镜像可能不含 Python）
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip bc \
    && pip3 install --no-cache-dir --break-system-packages numpy \
    && rm -rf /var/lib/apt/lists/*

# OpenMPI root 运行（K8s 环境必需）
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
ENV OMPI_MCA_btl_vader_single_copy_mechanism=none
ENV OMP_STACKSIZE=64M
# CP2K 数据目录（基组、势函数等）
ENV CP2K_DATA_DIR=/opt/cp2k/share/cp2k/data

# MiQroForge 工作目录约定 + PATH
# 官方镜像 entrypoint.sh 中设置 /opt/spack/bin，但 Argo emissary 会跳过 entrypoint，
# 必须通过 ENV 确保 PATH 在所有运行时环境中生效。
ENV PATH="/opt/cp2k/bin:/opt/spack/bin:${PATH}"
RUN mkdir -p /mf/profile /mf/input /mf/output /mf/workdir
WORKDIR /mf/workdir

# 验证安装
RUN cp2k.psmp --version 2>&1 | head -3 || true

LABEL maintainer="MiQroForge Team" \
      software="cp2k" \
      version="2025.2" \
      description="CP2K 2025.2 periodic DFT (official image + MF dirs)"
