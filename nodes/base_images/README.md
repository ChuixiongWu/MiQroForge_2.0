# 基础镜像指南

## Harbor 仓库

所有基础镜像推送到 `harbor.era.local/miqroforge2.0/`，编译时通过 `registry.yaml` 解析：

```
nodespec.yaml (base_image_ref) → registry.yaml (逻辑名 → image:tag) → 编译器注入 Argo YAML
```

## 构建镜像

```bash
# 前置：docker login harbor.era.local

bash nodes/base_images/<software>/build.sh
```

自动完成：构建本地镜像 → 验证 → 推送到 Harbor。

| 镜像 | 本地名 | 说明 |
|------|--------|------|
| ORCA 6.1 | `orca:6.1` | BYOB，需自行放置 tarball |
| Gaussian 16 | `gaussian:16` | BYOB，需自行放置 tarball |
| Psi4 1.10 | `psi4:1.10` | 基于官方镜像 |
| CP2K 2025.2 | `cp2k:2025.2` | 基于官方镜像 |
| Cirq 1 | `cirq:1` | 基于 python:3.11-slim |
| ephemeral-py | `ephemeral-py:3.11` | 临时节点 Python 基础 |

## 新增镜像

1. 创建 `nodes/base_images/<software>/` 目录
2. 编写 `Dockerfile`，遵循以下规范：
   - 工作目录：`RUN mkdir -p /mf/profile /mf/input /mf/output /mf/workdir` + `WORKDIR /mf/workdir`
   - 国内 apt 源：在 `apt-get update` 前加 `sed -i 's|http://archive.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list`（Debian 系用 `deb.debian.org`）
   - Docker Hub 镜像：使用 `docker.1ms.run/library/` 前缀（如 `python:3.11-slim`）
   - MPI 节点：设置 `ENV OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1`
   - 构建完加 `LABEL` 标注 software/version
3. 编写 `build.sh`，参考已有脚本的统一模式（`LOCAL_NAME`/`LOCAL_TAG`/`REGISTRY_PREFIX`）
4. 在 `registry.yaml` 添加条目（`name`/`image`/`tag`/`software_name` 等）
5. 运行 `bash scripts/mf2.sh nodes reindex` 更新节点索引
