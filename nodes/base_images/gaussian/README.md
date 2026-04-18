# Gaussian 16 基础镜像

> 构建方法见 [../README.md](../README.md)。本文件仅说明 Gaussian 特异性内容。

## BYOB 模式

Gaussian 16 是商业软件，需要用户持有 license 并自行下载 tarball（`.tbJ` 或 `.tar.gz`）放到本目录。

## 特异性：线程并行

Gaussian 不使用 MPI，通过 `%nprocshared` 控制内部线程并行。镜像设置：
- `GAUSS_SCRDIR=/tmp` — scratch 目录
- 计算完成后需运行 `formchk` 将 `.chk` 转为 `.fchk`

## 镜像内容

| 路径 | 内容 |
|------|------|
| `/opt/gaussian/` | Gaussian 16 二进制（g16, formchk, cubegen 等） |
| `/mf/profile/` | 运行时由 ConfigMap 挂载（run.sh、.gjf 模板） |
| `/mf/input/` | 运行时由 Argo 注入 onboard 参数 |
| `/mf/output/` | 节点计算结果写出位置 |
| `/mf/workdir/` | Gaussian 工作目录 |
