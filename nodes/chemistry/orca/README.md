# ORCA 节点集合

> **受众**：向 MiQroForge 添加或修改 ORCA 节点的 node author。
> 运行工作流的用户请参阅 [../../base_images/orca/README.md](../../base_images/orca/README.md)。

本目录包含以下四个 ORCA 节点：

| 节点 | 类型 | 功能 |
|------|------|------|
| `orca-geo-opt` | compute | DFT 几何优化，输出 GBW 波函数 + 优化后 XYZ |
| `orca-single-point` | compute | DFT 单点能量计算 |
| `orca-freq` | compute | 频率分析 + 热力学数据（接受 geo-opt 的 GBW） |
| `orca-thermo-extractor` | lightweight | 从 orca-freq 的 JSON 包提取/转换热力学数据 |

---

## 必读：在 Kubernetes 上运行 MPI 程序的注意事项

### 问题根源

Kubernetes pod 默认以 **root 用户**运行（uid=0）。OpenMPI 出于安全考虑，
**默认拒绝以 root 身份启动**，会立即退出并报错：

```
mpirun has detected an attempt to run as root.
mpirun was configured to not allow running as root.
```

即使 ORCA 本身没有报错，OpenMPI 的守护进程（`orted`）也无法启动，
导致多核 PAL 计算静默失败或直接崩溃。

### 解决方案

所有使用 OpenMPI 的节点，**必须**在 `nodespec.yaml` 的 `execution.environment` 中声明：

```yaml
execution:
  type: compute
  environment:
    OMPI_ALLOW_RUN_AS_ROOT: "1"
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM: "1"
```

这两个变量缺一不可：第一个解除禁止，第二个是 OpenMPI 要求的二次确认。

> **适用范围**：任何在 nodespec 中通过 OpenMPI 并行的节点，不限于 ORCA。
> 这是 MiQroForge 在 Kubernetes 上运行 MPI 程序的**平台级规范**。

---

## 分子几何输入：使用 xyzfile 而非内联坐标

ORCA 支持内联坐标（`* xyz`）和外部文件（`* xyzfile`）两种方式。
MiQroForge 的 ORCA 节点统一使用外部文件方式：

```
* xyzfile 0 1 input.xyz
```

**原因**：`run.sh` 负责将 `xyz_geometry` 参数写成标准 XYZ 文件，
ORCA 输入模板（`.j2`）只需引用文件名即可，职责清晰，大分子也不会撑爆模板。

用户输入的格式问题（标准 XYZ vs 纯坐标行）由 `run.sh` 处理；
格式完全错误时 ORCA 会直接报错，符合快速失败原则。

---

## Argo 输出参数大小限制

**Argo Workflow 的 output parameter 上限为 3MB。**

ORCA 产生的 `.gbw` 波函数文件通常为几十 MB 到几百 MB，**不能**作为 Argo output parameter 收集。

### MiQroForge 的解决方案

编译器（`compiler.py`）采用 `connected_outputs` 机制：
**只有被下游节点消费的 stream output 端口才会生成 Argo output parameter 收集规则。**

因此：
- `gbw_file` 连接到 `orca-freq` → 自动收集，用于节点间传递
- `gbw_file` 未连接（工作流末尾） → 跳过收集，避免 3MB 超限错误

> **注意**：`quality_gate` 输出（`opt_converged` 等）无论是否连接都会收集，
> 因为 DAG depends 条件需要读取它们。

---

## 节点执行流程（compute 节点）

```
Kubernetes Pod 启动
  │
  ├── /mf/profile/   ← ConfigMap 挂载 (run.sh, input.orca.j2)
  ├── /mf/input/     ← Argo 注入 onboard 参数（每个参数一个文件）
  │     ├── method          # "B3LYP"
  │     ├── basis_set       # "def2-SVP"
  │     ├── xyz_geometry    # XYZ 坐标文本
  │     └── ...
  │
  ├── bash /mf/profile/run.sh
  │     ├── 读取 /mf/input/* 中的参数
  │     ├── 写出 /mf/workdir/input.xyz（格式标准化）
  │     ├── 渲染 input.orca.j2 → /mf/workdir/input.inp
  │     ├── 运行 mpirun -np $N_CORES /opt/orca/orca input.inp
  │     └── 解析输出 → 写入 /mf/output/*
  │
  └── Argo 读取 /mf/output/* → 存入 workflow 参数状态
```

---

## 添加新 ORCA 节点的检查清单

- [ ] `nodespec.yaml` 的 `execution.environment` 包含两个 OMPI 变量
- [ ] `profile/input.orca.j2` 使用 `* xyzfile` 而非内联坐标（如需几何输入）
- [ ] `profile/run.sh` 使用 `#!/usr/bin/env bash` + `set -euo pipefail`
- [ ] 运行 `bash scripts/mf2.sh nodes reindex` 重建索引
- [ ] 运行 `pytest tests/unit/ -v` 确认测试通过
