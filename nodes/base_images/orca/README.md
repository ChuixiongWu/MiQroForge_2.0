# ORCA 6.1 基础镜像

> 构建方法见 [../README.md](../README.md)。本文件仅说明 ORCA 特异性内容。

## BYOB 模式

ORCA 是学术免费软件，**不可再分发**。需要用户自行下载 tarball：

1. 在 [orcaforum.kofo.mpg.de](https://orcaforum.kofo.mpg.de) 注册
2. 下载 tarball 放到本目录（支持 AVX2 和通用版）
3. 运行 `bash nodes/base_images/orca/build.sh`

## 特异性：OpenMPI 并行

ORCA 使用 OpenMPI 做并行计算，镜像中已设置：
- `OMPI_ALLOW_RUN_AS_ROOT=1` — K8s 以 root 运行，允许 MPI 启动
- `OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1` — 同上
- `OMP_NUM_THREADS=1` — 默认单线程，可通过 onboard_params.n_cores 覆盖

## 故障排查

**`docker build` 中途 OOM**
构建过程中解压 tarball 需要约 2GB 内存。调至 4GB 以上。

**AVX2 版本运行时 `Illegal instruction`**
节点机器不支持 AVX2。改用通用版 tarball 重新构建。

**多节点集群 pod `ImagePullBackOff`**
worker 节点无法访问镜像。将镜像推送到可访问的 registry，或用 `k3s ctr images import` 导入。

**ORCA 运行时 `orted: command not found`**
OpenMPI 未正确安装。检查 `docker run --rm orca:6.1 which mpirun`。

## 镜像内容

| 路径 | 内容 |
|------|------|
| `/opt/orca/` | ORCA 6.1 二进制及共享库 |
| `/mf/profile/` | 运行时由 ConfigMap 挂载（run.sh、input.orca.j2） |
| `/mf/input/` | 运行时由 Argo 注入 onboard 参数 |
| `/mf/output/` | 节点计算结果写出位置 |
| `/mf/workdir/` | ORCA 工作目录（临时文件） |
