# =============================================================================
# Classical Chemistry — MiQroForge 经典量子化学模拟基础镜像
#
# 包含：
#   - PySCF 2.8.0: Python 量子化学框架
#   - Vayesta (git): 嵌入式波函数方法（DMET, SEET 等）
#   - OpenFermion 1.7.1: 量子化学 ↔ 量子计算映射
#   - OpenFermion-PySCF 0.5: OpenFermion PySCF 插件
#   - numpy, scipy, h5py: 科学计算基础库
#
# 构建：bash nodes/base_images/classical-chem/build.sh
# =============================================================================
FROM docker.1ms.run/library/python:3.11-slim

# 国内镜像源加速（DEB822 格式）
RUN sed -i 's|URIs: http://deb.debian.org|URIs: http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources
# 系统依赖：BLAS/LAPACK 运行时 + 编译器临时依赖（Vayesta 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        liblapack3 \
        libblas3 \
        gcc \
        g++ \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
        cmake \
        make \
        git \
    && rm -rf /var/lib/apt/lists/*

# 基础科学计算库（先装，供后续包依赖）
RUN pip install --no-cache-dir \
    numpy \
    scipy \
    h5py

# PySCF 2.8.0（核心量子化学框架）
RUN pip install --no-cache-dir \
    pyscf==2.8.0

# Vayesta（嵌入式波函数）
# 手动 cmake + 文件安装，绕过 setup.py CMakeExtension(sources=[]) 兼容问题
COPY vayesta_src/ /tmp/vayesta/
RUN pip install --no-cache-dir Cython \
    && cd /tmp/vayesta \
    && cmake -Svayesta/libs -Bbuild \
    && cmake --build build \
    && cp -r vayesta /usr/local/lib/python3.11/site-packages/ \
    && cp -r Vayesta.egg-info /usr/local/lib/python3.11/site-packages/ 2>/dev/null || true \
    && cd / \
    && pip install --no-cache-dir cvxpy \
    && rm -rf /tmp/vayesta/

# OpenFermion + PySCF 插件（量子化学 → 量子计算桥接）
RUN pip install --no-cache-dir \
    openfermion==1.7.1 \
    openfermionpyscf==0.5

# 清理构建依赖（减小镜像体积）
RUN apt-get purge -y gcc g++ gfortran libopenblas-dev liblapack-dev cmake make \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# MiQroForge 工作目录约定
RUN mkdir -p /mf/profile /mf/input /mf/output /mf/workdir
WORKDIR /mf/workdir

# 验证安装
RUN python -c "import pyscf; print(f'[OK] PySCF {pyscf.__version__}')" \
    && python -c "import vayesta; print('[OK] Vayesta loaded')" \
    && python -c "import openfermion; print(f'[OK] OpenFermion {openfermion.__version__}')" \
    && python -c "import openfermionpyscf; print('[OK] OpenFermion-PySCF loaded')" \
    && python -c "import h5py, scipy; print('[OK] h5py + scipy loaded')"

LABEL maintainer="MiQroForge Team" \
      software="classical-chem" \
      version="0.1" \
      description="PySCF 2.8.0 + Vayesta + OpenFermion 1.7.1 classical quantum chemistry stack"
