# =============================================================================
# Cirq + qsim — MiQroForge 量子模拟基础镜像
#
# 包含：
#   - cirq-core: Google 量子电路构建框架
#   - qsimcirq: Google 高性能量子模拟器
#
# 构建：bash nodes/base_images/cirq/build.sh
# =============================================================================
FROM docker.1ms.run/library/python:3.11-slim

# 国内镜像源加速
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list \
    && sed -i 's|http://security.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
# 系统依赖：matplotlib 需要字体（与 ephemeral-py 一致）
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# 量子计算核心
RUN pip install --no-cache-dir \
    cirq-core \
    qsimcirq

# MiQroForge 工作目录约定
RUN mkdir -p /mf/profile /mf/input /mf/output /mf/workdir
WORKDIR /mf/workdir

# 验证安装
RUN python -c "import cirq; print(f'[OK] cirq {cirq.__version__}')" \
    && python -c "import qsimcirq; print('[OK] qsimcirq loaded')"

LABEL maintainer="MiQroForge Team" \
      software="cirq" \
      version="1.x" \
      description="Cirq quantum framework + qsim high-performance simulator"
