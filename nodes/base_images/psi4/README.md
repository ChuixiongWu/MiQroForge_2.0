# Psi4 1.10 基础镜像

> 构建方法见 [../README.md](../README.md)。本文件仅说明 Psi4 特异性内容。

## 特异性：基于官方镜像 + 线程并行

- 基于 `psi4/psi4:1.10` 官方 Docker 镜像，仅添加 MiQroForge 工作目录约定
- 不使用 MPI，通过 OpenMP 线程并行（Psi4 内部自动管理）
- 首次构建需拉取官方镜像（约 2 GB）
