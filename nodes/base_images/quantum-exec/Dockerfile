# =============================================================================
# quantum-exec — MiQroForge 量子计算执行镜像
#
# 包含：
#   - OpenFermion: 量子化学 → 量子电路映射
#   - PennyLane: 量子机器学习框架
#   - Amazon Braket SDK + PennyLane 插件: AWS 量子后端
#
# 用途：VQE、QAOA、量子机器学习、混合量子-经典算法
#
# 构建：bash nodes/base_images/quantum-exec/build.sh
# =============================================================================
FROM docker.1ms.run/library/python:3.11-slim

# 国内镜像源加速
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list \
    && sed -i 's|http://security.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

# 系统依赖：OpenMP runtime + 字体（与 cirq / ephemeral-py 一致）
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# 科学计算基础库（预装，避免量子库重复拉取依赖）
RUN pip install --no-cache-dir \
    numpy \
    scipy \
    h5py

# 量子计算核心（版本锁定以保证可复现性）
RUN pip install --no-cache-dir \
    openfermion \
    pennylane==0.42.3 \
    amazon-braket-sdk==1.110.1 \
    amazon-braket-pennylane-plugin==1.33.7

# MiQroForge 工作目录约定
RUN mkdir -p /mf/profile /mf/input /mf/output /mf/workdir
WORKDIR /mf/workdir

# 验证安装
RUN python -c "import openfermion; print('[OK] openfermion loaded')" \
    && python -c "import pennylane; print(f'[OK] pennylane {pennylane.__version__}')" \
    && python -c "import braket; print('[OK] braket-sdk loaded')" \
    && python -c "from braket.aws import AwsDevice; print('[OK] braket.aws AwsDevice importable')"

LABEL maintainer="MiQroForge Team" \
      software="quantum-exec" \
      version="0.1" \
      description="OpenFermion + PennyLane + Amazon Braket SDK for quantum computing workflows"
