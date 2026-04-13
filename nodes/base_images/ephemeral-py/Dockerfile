# =============================================================================
# ephemeral-py — MiQroForge 临时节点基础镜像
#
# 在 python:3.11-slim 基础上预装科学计算常用库，
# 覆盖 Agent 生成脚本最常见的依赖，避免每次运行时 pip install。
# =============================================================================
FROM docker.1ms.run/library/python:3.11-slim

# 系统依赖：matplotlib 需要 libgomp（OpenMP）和字体
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# 科学计算核心库
RUN pip install --no-cache-dir \
    numpy \
    scipy \
    pandas \
    matplotlib \
    pyyaml \
    jinja2 \
    requests \
    jsonschema

# 运行时工作目录（Argo 覆盖）
WORKDIR /mf/workdir
