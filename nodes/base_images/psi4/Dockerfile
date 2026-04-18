# =============================================================================
# Psi4 — MiQroForge 量子化学基础镜像
#
# 基于 psi4/psi4 官方 Docker 镜像，仅添加 MF 工作目录约定。
#
# 构建：bash nodes/base_images/psi4/build.sh
# 拉取：docker pull docker.1ms.run/psi4/psi4:1.10
# =============================================================================
FROM docker.1ms.run/psi4/psi4:1.10

# 官方镜像以 mambauser 运行，需 root 权限创建 /mf 目录
USER root
RUN mkdir -p /mf/profile /mf/input /mf/output /mf/workdir \
    && chown -R mambauser:mambauser /mf
USER mambauser

# 将 conda 环境加入 PATH，使 run.sh 中的 python3/psi4 命令可直接调用
# （编译器用 sh -c 执行 run.sh，不会激活 conda 环境）
ENV PATH="/opt/conda/envs/psi4/bin:/opt/conda/bin:${PATH}"
# 不设置 OMP_NUM_THREADS — Psi4 通过 psi4.set_num_threads() 在运行时控制线程数，
# 设置环境变量会覆盖它，导致多核并行失效。

# 验证安装
RUN python -c "import psi4; print(f'[OK] psi4 {psi4.__version__}')" \
    && psi4 --version

WORKDIR /mf/workdir

LABEL maintainer="MiQroForge Team" \
      software="psi4" \
      version="1.10" \
      description="Psi4 open-source quantum chemistry (official image + MF dirs)"
