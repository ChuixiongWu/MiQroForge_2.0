# Classical Chemistry 基础镜像

> 构建方法见 [../README.md](../README.md)。本文件仅说明 Classical Chemistry 特异性内容。

## 镜像内容

| 包 | 版本 | 说明 |
|---|------|------|
| PySCF | 2.8.0 | Python 量子化学框架（HF, DFT, CC, CASSCF 等） |
| Vayesta | git HEAD | 嵌入式波函数方法（DMET, SEET 等） |
| OpenFermion | 1.7.1 | 量子化学 ↔ 量子计算映射 |
| OpenFermion-PySCF | 0.5 | OpenFermion PySCF 插件 |
| numpy | latest | 科学计算 |
| scipy | latest | 科学计算 |
| h5py | latest | HDF5 文件读写 |

## 特异性：经典量子化学栈

- 基于 `python:3.11-slim`，通过 pip 安装所有包
- Vayesta 从 GitHub 主分支安装（`git+https://github.com/BoothGroup/Vayesta.git`）
- 构建时临时安装 `gcc`/`gfortran`/`libopenblas-dev` 编译依赖，构建后清理
- 用于电子结构计算、量子嵌入和量子计算桥接
