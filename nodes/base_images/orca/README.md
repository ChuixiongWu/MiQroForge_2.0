# ORCA 6.1 基础镜像构建指南

> **受众**：部署 MiQroForge 的 operator。每台需要运行 ORCA 工作流的机器只需执行一次。

ORCA 是学术免费软件，**不可再分发**。MiQroForge 采用 BYOB（Bring Your Own Binary）模式：
用户自行从官方渠道下载二进制，由脚本打包进 Docker 镜像。

---

## 快速开始

在**项目根目录**运行下载引导脚本：

```bash
# 下载 tarball（交互式引导）
bash nodes/base_images/orca/download_orca.sh

# 或一步到位：下载完成后自动构建镜像
bash nodes/base_images/orca/download_orca.sh --build
```

脚本会自动完成：
1. 呈现学术用途声明，要求用户明确同意 EULA
2. 检测当前系统架构，推荐 AVX2 或通用版
3. 引导从官方论坛下载 tarball（支持手动路径输入 / URL 粘贴两种方式）
4. 校验文件完整性
5. 将 tarball 放置到 `nodes/base_images/orca/`

tarball 就位后，如果没有用 `--build` 自动触发，手动运行构建：

```bash
bash nodes/base_images/orca/build.sh
```

---

## 前置条件

| 依赖 | 说明 |
|------|------|
| Docker | 已安装且 daemon 正在运行 |
| ORCA 账号 | 在 [orcaforum.kofo.mpg.de](https://orcaforum.kofo.mpg.de) 注册（免费） |

---

## 构建完成后的镜像分发

`build.sh` 构建完成后，镜像以 `harbor.era.local/library/orca:6.1` 为标签存在于本机
Docker 中。根据你的集群形态选择后续操作：

**单节点集群（build 机即 worker 节点）**

无需额外操作。Kubernetes 使用 `imagePullPolicy: IfNotPresent`（MiQroForge 编译器默认值），
直接使用本地镜像，不会尝试从网络拉取。

**多节点集群（worker 节点与 build 机不同）**

需要将镜像推送到集群内所有节点可访问的 registry，例如：

```bash
# 推送到本地 Harbor
docker push harbor.era.local/library/orca:6.1

# 或推送到其他内网 registry，并相应修改 registry.yaml 中的镜像地址
```

> 如果使用的是 k3s，也可以通过 `k3s ctr images import` 直接导入镜像，
> 无需搭建 registry。

---

## 验证

```bash
# 验证 ORCA 可执行（预期输出含 "Starting time"）
docker run --rm harbor.era.local/library/orca:6.1 /opt/orca/orca 2>&1 | head -5

# 确认 MPI 正常
docker run --rm harbor.era.local/library/orca:6.1 mpirun --version
```

---

## 故障排查

**`docker build` 中途 OOM**
构建过程中解压 tarball 需要约 2GB 内存。进入
Docker Desktop → Settings → Resources → Memory，调至 4GB 以上。

**AVX2 版本运行时 `Illegal instruction`**
节点机器不支持 AVX2。删除现有镜像，改用通用版 tarball 重新构建：
```bash
docker rmi harbor.era.local/library/orca:6.1
# 运行 download_orca.sh，在架构选择时选通用 x86-64 版本
bash nodes/base_images/orca/download_orca.sh --build
```

**多节点集群：pod 出现 `ImagePullBackOff`**
worker 节点无法访问镜像。参考上方"多节点集群"部分，将镜像推送到可访问的 registry。

**ORCA 运行时 `orted: command not found`**
OpenMPI 运行时未正确安装。检查镜像内：
```bash
docker run --rm harbor.era.local/library/orca:6.1 which mpirun
```

---

## 镜像内容说明

| 路径 | 内容 |
|------|------|
| `/opt/orca/` | ORCA 6.1 二进制及共享库 |
| `/mf/profile/` | 运行时由 ConfigMap 挂载（run.sh、input.orca.j2） |
| `/mf/input/` | 运行时由 Argo 注入 onboard 参数 |
| `/mf/output/` | 节点计算结果写出位置 |
| `/mf/workdir/` | ORCA 工作目录（临时文件，容器结束后丢弃） |

镜像本身**不含任何计算输入**；所有计算逻辑通过 profile 文件在运行时注入。
