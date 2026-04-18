# CP2K 2025.2 基础镜像

> 构建方法见 [../README.md](../README.md)。本文件仅说明 CP2K 特异性内容。

## 特异性：基于官方镜像 + MPI+OpenMP 混合并行

- 基于 `cp2k/cp2k:2025.2_openmpi_x86_64_psmp` 官方 Docker 镜像
- 使用 MPI + OpenMP 混合并行：`mpirun -np N cp2k.psmp`
- `OMPI_ALLOW_RUN_AS_ROOT=1` 已在镜像中设置
- `CP2K_DATA_DIR` 指向内置基组文件（BASIS_MOLOPT、GTH 势函数等）
- 内存需求较高（平面波网格 + FFT），默认 16GB
- 主要面向周期性体系的 DFT 计算（GPW/GAPW 方法）
