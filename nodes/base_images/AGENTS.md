# Base Images & Infrastructure Conventions

**Hierarchy:** `nodes/base_images/` — Docker images for all node execution environments.

## STRUCTURE
```
base_images/
├── AGENTS.md            # ★ This file: image conventions, BYOB, MPI, Workspace PVC
├── README.md            # Top-level install guide (developer reference)
├── registry.yaml        # Image registry: maps software → image:tag
├── orca/                # ORCA 6.1 BYOB (OpenMPI parallel)
├── gaussian/            # Gaussian 16 BYOB (thread parallel)
├── psi4/                # Psi4 1.10 (official image based)
├── cp2k/                # CP2K 2025.2 (MPI+OpenMP hybrid)
├── cirq/                # Cirq + qsim (quantum simulation)
└── ephemeral-py/        # Ephemeral node Python base image
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Build an image | `nodes/base_images/<software>/build.sh` |
| Modify registry | `registry.yaml` |
| Add new software image | Create `<software>/` with Dockerfile + build.sh, update registry.yaml |
| Understand MPI setup | This file, or `nodes/base_images/orca/Dockerfile` |

---

## BYOB 镜像（Build-Your-Own-Base）

对于不可再分发的软件（如 ORCA、Gaussian），在 `nodes/base_images/<software>/` 下提供
`Dockerfile` + `build.sh` + `README.md`，`registry.yaml` 中标记 `source_type: user-built`。
参考实现：`nodes/base_images/orca/`。

构建流程：
```bash
bash nodes/base_images/<software>/build.sh
# 自动构建本地镜像 + 推送到 Harbor（需先 docker login harbor.era.local）
```

---

## MPI / OpenMPI 节点

Kubernetes pod 默认以 root 用户运行，OpenMPI 默认拒绝 root 启动。
所有 OpenMPI 并行节点（ORCA、CP2K 等）的 `OMPI_ALLOW_RUN_AS_ROOT` 和
`OMPI_ALLOW_RUN_AS_ROOT_CONFIRM` 环境变量应在**基础镜像 Dockerfile** 中通过 `ENV` 声明，
`nodespec.yaml` 中使用 `execution: {}` 即可（不重复声明）。这样可以避免每个节点重复配置，
且确保所有基于该镜像的节点都自动获得正确的 MPI 行为。

```dockerfile
# 在 base_images/<software>/Dockerfile 中
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
```

---

## Workspace PVC 持久化挂载

Workspace PVC 在 MiQroForge 中承担**两个不同角色**：

1. **用户 ↔ 节点文件交换**（手动上传/下载）
2. **节点 ↔ 节点 SDP 数据传输**（`software_data_package` 类型 Stream IO）

下面分开说明。节点间 SDP 传输的完整机制（含 compiler `cp` 注入、`STREAM_DIR`、与 Argo parameter 的分工规则）
见 [`nodes/schemas/README.md`](../schemas/README.md#sdp-节点间传输完整机制)。

---

### 挂载方式（所有节点统一）

每个节点容器**无条件**将 workspace PVC 挂载到 `/mf/workspace`，通过 `subPath` 实现项目级隔离：

- **subPath**：`proj_{project_id}`（全程真实目录，零 symlink）
- **mountPath**：`/mf/workspace`
- **PVC 名**：`ARGO_NAMESPACE` 环境变量值（`mf-workspace`）
- **hostPath**：`userdata/workspace/`（PV 定义在 `infrastructure/k8s/workspace.yaml`）
- 当 `project_id` 为空时（向后兼容），不使用 subPath，挂载整个 `userdata/workspace/`。

编译器 helper：`_workspace_volume_mount()` → `_workspace_volume()`（`compiler.py` L69-86）。PVC claim 名通过 `_get_pvc_name()` 取 `ARGO_NAMESPACE` 环境变量（L63-66）。

---

### 角色 1：用户 ↔ 节点文件交换

用户上传输入文件（如分子坐标 `.xyz`、力场参数），节点在运行时从 `/mf/workspace/<filename>` 读取。
MF YAML 的 `onboard_params` 中只填文件名（如 `geometry_file: h2o.xyz`），节点脚本自行在运行时定位文件，
**编译器不做任何解引用**。

节点也可以将大型输出（如波函数、轨迹）写入 workspace，供人/Agent 事后检查。

---

### 角色 2：节点间 SDP 传输（Stream IO `software_data_package`）

Stream IO 中 `io_type.category == "software_data_package"` 的端口（HDF5 meanfield package、Vayesta cluster Hamiltonian、ORCA GBW 等二进制大文件）
**不走 Argo output parameter**（Argo 上限 3 MB，无法容纳），而是通过 PVC 的 `.stream/` 子目录在节点间传递。

这只是**整个运输机制的摘要**；完整 end-to-end 流程（含 compiler 注入的 `cp` 命令、`STREAM_DIR`、与 Argo parameter 的分工规则、ordering/safety、end-to-end 示例）
见 [`nodes/schemas/README.md`](../schemas/README.md#sdp-节点间传输完整机制)。

---

### Shell / Python 访问方式

- Shell：`source /mf/profile/mf2_init.sh` → `$WORKSPACE_DIR` 指向 `/mf/workspace`
- Python：`os.environ.get("MF_WORKSPACE_DIR", "/mf/workspace")`

---

**基础设施部署（一次性，hostPath 模式无需 NFS 操作）：**
```bash
kubectl apply -f infrastructure/k8s/workspace.yaml
kubectl get pvc mf-workspace -n miqroforge-v2   # 应显示 Bound
```
