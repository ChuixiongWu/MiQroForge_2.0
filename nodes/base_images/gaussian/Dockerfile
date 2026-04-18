# =============================================================================
# Gaussian 16 — MiQroForge 量子化学基础镜像（BYOB）
#
# 包含：
#   - Gaussian 16 C.01 二进制（用户提供 tarball）
#   - formchk 用于 .chk → .fchk 转换
#   - Python 3 用于后处理
#
# 构建：bash nodes/base_images/gaussian/build.sh
#
# 前置条件：将 Gaussian 16 tarball 放到本目录
#   文件名示例：G16-C01-AVX.tbJ（XZ 压缩）
# =============================================================================
ARG GAUSS_TARBALL=G16-C01-AVX.tbJ

# Stage 1: 解压 tarball
FROM ubuntu:22.04 AS builder

ARG GAUSS_TARBALL
# 国内镜像源加速
RUN sed -i 's|http://archive.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list \
    && sed -i 's|http://security.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list
RUN apt-get update && apt-get install -y --no-install-recommends xz-utils tar \
    && rm -rf /var/lib/apt/lists/*

COPY ${GAUSS_TARBALL} /tmp/g16.tbJ
RUN mkdir -p /opt/gaussian \
    && tar xf /tmp/g16.tbJ -C /opt/gaussian --strip-components=1 \
    && rm /tmp/g16.tbJ

# Stage 2: 运行时
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
# 国内镜像源加速
RUN sed -i 's|http://archive.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list \
    && sed -i 's|http://security.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip bc libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/gaussian /opt/gaussian

ENV g16root="/opt/gaussian"
ENV GAUSS_EXEDIR="/opt/gaussian"
ENV GAUSS_SCRDIR="/tmp"
ENV PATH="/opt/gaussian:${PATH}"

# MiQroForge 工作目录约定
RUN mkdir -p /mf/profile /mf/input /mf/output /mf/workdir
WORKDIR /mf/workdir

# 验证安装
RUN g16 < /dev/null 2>&1 | head -3 || true

LABEL maintainer="MiQroForge Team" \
      software="gaussian" \
      version="16-C.01" \
      description="Gaussian 16 C.01 AVX quantum chemistry (BYOB)"
