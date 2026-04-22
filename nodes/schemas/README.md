# nodes/schemas — 节点 Schema 体系

本目录是 MiQroForge 节点规范的 **Pydantic 实现层**，定义了所有节点的结构约束。
每个节点通过 `nodespec.yaml` 表达自身规格，由本目录的 Schema 负责校验。

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `node.py` | `NodeSpec` — 完整节点定义（唯一事实来源），含执行配置 |
| `io.py` | Stream I/O 四分类 + On-Board I/O + Quality Gate |
| `resources.py` | `ComputeResources` / `LightweightResources` |
| `connection.py` | 端口兼容性规则（连线合法性校验） |
| `base.py` | `NodeMetadata`、`NodeType`、`NodeCategory` 等基础模型 |
| `units.py` | 已知物理量单位注册表（`KNOWN_UNITS`）及量纲查询 |
| `semantic_registry.py` | 语义类型注册表（Python 接口） |
| `semantic_registry.yaml` | 语义类型数据文件（`geo_opt`、`single_point` 等） |
| `base_image.py` | `BaseImageEntry` — 镜像注册表条目模型 |

---

## Schema 层级

```
NodeSpec (node.py)
├── metadata: NodeMetadata          # base.py — 名称、版本、分类、标签
├── stream_inputs:  [StreamInputPort]   # io.py
├── stream_outputs: [StreamOutputPort]  # io.py
├── onboard_inputs:  [OnBoardInput]     # io.py
├── onboard_outputs: [OnBoardOutput]    # io.py — 含 Quality Gate 字段
├── resources: ComputeResources | LightweightResources   # resources.py
└── execution: ComputeExecutionConfig | LightweightExecutionConfig  # node.py
```

`NodeSpec` 对应磁盘上的 `nodespec.yaml`，通过 `NodeSpec.from_yaml(path)` 加载并校验。

---

## Stream I/O 四分类

| 类别 (`category`) | 类 | 连接规则 |
|-------------------|----|----------|
| `physical_quantity` | `PhysicalQuantityType` | 同 `dimension`（由 `unit` 查询）可连；不同单位自动转换 |
| `software_data_package` | `SoftwareDataPackageType` | `ecosystem` + `data_type` 严格匹配 |
| `logic_value` | `LogicValueType` | 同 `kind` 可连；`boolean` ↔ `signal` 可隐式转换 |
| `report_object` | `ReportObjectType` | 同 `format` 直接连通；不同格式发出警告 |

> **大型二进制约束**：`software_data_package` 类输出（如 GBW 波函数）体积可达数 GB，
> **不能**作为 Argo output parameter 直接收集（上限 3 MB）。
> MiQroForge 编译器的 `connected_outputs` 机制会自动跳过未被下游节点消费的此类端口。

---

## 资源估算字段

### ComputeResources（计算节点，全部必填）

| 字段 | 类型 | 说明 |
|------|------|------|
| `cpu_cores` | `int ≥ 1` | 所需 CPU 核数 |
| `memory_gb` | `float > 0` | 所需内存（GiB） |
| `estimated_walltime_hours` | `float > 0` | 预估运行时长（小时） |
| `gpu_count` | `int ≥ 0`，默认 0 | 所需 GPU 数量 |
| `gpu_type` | `str \| None` | GPU 型号要求，如 `nvidia-a100` |
| `scratch_disk_gb` | `float ≥ 0`，默认 0 | 临时磁盘空间（GiB） |
| `parallel_tasks` | `int ≥ 1`，默认 1 | MPI 并行任务数 |
| `parametrize` | `list[str] \| None` | 需要参数化的资源字段列表（见下方说明） |

#### parametrize — 资源参数化

**解决的问题**：`n_cores` 改为 8，ORCA PAL 用 8 核，但 Argo pod 仍只分配 4 核 → 资源争抢/OOM。

**工作原理**：`parametrize` 是一个**资源字段名列表**，告诉编译器"编译时用 onboard input 的值覆盖对应的静态资源声明"。每个字段对应的 onboard input 名称（`param_name`）和默认属性由 `nodes/schemas/resource_defaults.yaml` 统一定义，nodespec 无需重复声明。

```yaml
resources:
  type: compute
  cpu_cores: 4         # 静态默认值，同时作为自动注入的 n_cores 的 default
  memory_gb: 8.0
  mem_gb: 8.0          # 应用层内存（如 Gaussian %mem）
  estimated_walltime_hours: 2.0
  parallel_tasks: 4
  parametrize:
    - cpu_cores        # → resource_defaults.yaml 定义 param_name: n_cores
    - parallel_tasks   # → 同样映射到 n_cores，不重复注入
    - mem_gb           # → resource_defaults.yaml 定义 param_name: mem_gb
```

`resource_defaults.yaml` 定义了 `cpu_cores` 和 `parallel_tasks` 都使用 `param_name: n_cores`，所以两条 binding 只生成一个 `OnBoardInput(name="n_cores", kind=integer, default=4, resource_param=True)`。

如果需要自定义（如改 `max_value`），在 `onboard_inputs` 中手动声明同名参数，自动注入会跳过已存在的参数。

**端到端流程示例**（用户设置 `n_cores: 8`）：
1. workflow YAML → `onboard_params: {n_cores: 8}`
2. `mf2 compile` → 编译器读到 binding，取 `8`
3. 生成 Argo YAML → `resources.requests: {cpu: '8', memory: 8.0Gi}`
4. Argo 提交 → pod 分配 8 核，ORCA PAL 也跑 8 进程，两边一致 ✓

约束（Schema 在加载 nodespec.yaml 时自动校验）：
- 列表中每项必须是 `ComputeResources` 的有效字段名（`cpu_cores`、`memory_gb`、`mem_gb`、`gpu_count` 等）
- 被绑定的 onboard input 的 `kind` 必须为 `integer` 或 `float`
- 自动注入的 onboard input 带有 `resource_param: true`，前端会将其显示在资源区域

### LightweightResources（轻量节点，均有默认值）

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `cpu_cores` | 1 | CPU 核数 |
| `memory_gb` | 1.0 | 内存（GiB） |
| `estimated_walltime_hours` | 0.083 | 约 5 分钟 |
| `timeout_seconds` | 300 | 硬超时（秒） |

---

## OnBoardInput 填写指南

### `kind` — 数据类型选型

| `kind` | 何时使用 | 关联字段 | UI 组件 | 示例 |
|--------|---------|---------|---------|------|
| `string` | 自由文本标识符，无固定候选值 | — | text input | `method: B3LYP`，`basis_set: def2-SVP` |
| `integer` | 整数计数，含负数 | `min_value`, `max_value` | number input | `n_cores: 4`，`charge: -1`，`max_iter: 200` |
| `float` | 带小数的物理量 | `min_value`, `max_value`, `unit` | number input | `temperature: 298.15`，`pressure: 1.0` |
| `boolean` | 开关 | — | toggle/checkbox | `use_solvent: false` |
| `enum` | 有限候选值集合，**必须**同时填 `allowed_values` | `allowed_values`（必填） | dropdown | `dispersion: D3BJ` |
| `textarea` | 需要换行的文本块 | — | textarea | XYZ 坐标，内联脚本 |

**选型决策树**：
```
参数有固定候选值？ → YES → enum（配 allowed_values）
                  → NO
                    ↓
              需要换行？ → YES → textarea
                         → NO
                           ↓
                      是整数？ → YES → integer
                               → NO
                                 ↓
                            是浮点数？ → YES → float（带 unit 如 "K"/"atm"）
                                       → NO  → string
```

> **注意**：`integer` 和 `float` 可被 `parametrize` 自动注入（如 `cpu_cores: n_cores` 会自动生成 `n_cores` 输入）。
> `boolean` 是 `OnBoardOutput` 中 `quality_gate: true` 的唯一合法 kind。

### `default` — 必填/可选规则

- 省略 `default`（或写 `default: null`） → **必填**，用户必须提供值
- 写了 `default: <任意值>` → **可选**，用户不填时用默认值
- `default` 的类型须与 `kind` 匹配：`integer`→整数，`float`→浮点，`boolean`→`true`/`false`，`enum`→`allowed_values` 中的某个值

### 完整示例

```yaml
onboard_inputs:
  # 必填：无 default（用户必须提供）
  - name: xyz_geometry
    kind: textarea
    description: "分子坐标（XYZ 格式），或 workspace 文件名（如 h2o.xyz）"

  # 注意：n_cores 不需要手动声明 — parametrize 会自动生成
  # 如果需要覆盖自动生成的属性（如改 max_value），可手动声明

  # 枚举，必须有 allowed_values
  - name: dispersion
    kind: enum
    default: D3BJ
    allowed_values: ["none", "D3", "D3BJ", "D4"]
    description: "色散修正方案，推荐 D3BJ"

  # 浮点，带单位
  - name: temperature
    kind: float
    default: 298.15
    min_value: 1.0
    unit: K
```

---

## Quality Gate 机制

`OnBoardOutput` 支持将某个布尔输出标记为质量控制门控：

```yaml
onboard_outputs:
  - name: opt_converged
    display_name: "优化已收敛"
    kind: boolean
    quality_gate: true
    gate_default: must_pass        # must_pass | warn | ignore
    gate_description: "检查几何优化是否收敛"
```

- `quality_gate: true` 时，`kind` 必须为 `boolean`
- `gate_default: must_pass` — Gate 为 false 时阻止下游节点运行（编译为 Argo `when` 条件）
- `gate_default: warn` — Gate 为 false 时仅记录警告，不阻断工作流
- `gate_default: ignore` — 不生成任何 Argo 条件

---

## LightweightExecutionConfig 字段说明

轻量节点的执行配置支持三种**互斥**模式：

| 字段 | 模式 | 说明 |
|------|------|------|
| `inline_script` | Python 内联 | 直接将 Python 代码写入 `nodespec.yaml` |
| `script_path` | Python 外置文件 | 指向 `profile/` 目录下的 `.py` 文件，编译时读入 |
| `entrypoint_script` | Profile-based shell | 与 compute 节点行为一致，使用 `sh + ConfigMap`，只换了镜像 |

三者互斥，必须且只能使用一种。

### 通用字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `python_version` | `str` | `"3.10"` | Python 基础镜像版本（`python:{version}-slim`） |
| `pip_dependencies` | `list[str]` | `[]` | 运行时 pip 依赖（仅 inline/script_path 模式有效） |
| `environment` | `dict[str, str]` | `{}` | 额外环境变量（主要用于 entrypoint_script 模式） |

### 模式 A：Python 内联脚本（`inline_script`）

最常见的轻量节点形式，适合逻辑简单的数据处理步骤：

```yaml
execution:
  type: lightweight
  python_version: "3.11"
  pip_dependencies: ["numpy", "matplotlib"]
  inline_script: |
    import os, json
    import numpy as np
    output_dir = os.environ.get("MF_OUTPUT_DIR", "/mf/output")
    # ... 处理逻辑
```

参数通过环境变量注入，脚本用 `os.environ.get(param_name)` 读取。

### 模式 B：外置 Python 文件（`script_path`）

适合脚本较长、需要版本管理的场景：

```yaml
execution:
  type: lightweight
  python_version: "3.10"
  script_path: "profile/extract.py"   # 相对于节点目录
```

编译时自动读取文件内容内联到 Argo script template。

### 模式 C：Profile-based Shell 入口（`entrypoint_script`）

适合需要 shell 编排、调用命令行工具或复用 `mf2_init.sh` 功能的场景。
行为与 compute 节点完全一致，只是镜像换为 `python:{version}-slim`（内置 bash）。

```yaml
execution:
  type: lightweight
  python_version: "3.11"
  entrypoint_script: "run.sh"       # profile/ 子目录下的脚本
  environment:
    SOME_FLAG: "1"
```

节点目录结构：

```
nodes/<domain>/<node-name>/
├── nodespec.yaml
└── profile/
    ├── run.sh          ← entrypoint_script 指向此文件
    └── helper.sh       ← 其他 profile 文件（也会注入 ConfigMap）
```

`run.sh` 中可正常使用 `mf2_init.sh` 的全部功能（`mf_param`、`mf_banner`、`WORKSPACE_DIR` 等）：

```bash
#!/usr/bin/env bash
# MF2 init      ← 编译器自动替换为 source /mf/profile/mf2_init.sh
source /mf/profile/mf_node_params.sh

mf_banner "my-lightweight-node" "Data extraction step"
# WORKSPACE_DIR=/mf/workspace（已由 mf2_init.sh 设置）
# 可读写 PVC 挂载的持久化目录
cp "${WORKSPACE_DIR}/input_data.bin" /mf/input/
# ... 处理逻辑
```

---

## Workspace PVC 挂载机制

Workspace 是**用户/Main Agent ↔ 节点**之间的输入输出交换区，不是节点间数据传递通道。

### 项目级文件隔离

每个项目有独立的 workspace 子目录，运行时通过 PVC `subPath` 实现隔离：

```
userdata/workspace/                    ← PV hostPath 根目录
  .files/
    proj_xxx/                          ← 项目 A 的文件
    proj_yyy/                          ← 项目 B 的文件
```

- 编译器为每个工作流模板注入 `subPath: .files/{project_id}`，容器内 `/mf/workspace`
  直接映射到项目的文件子目录，节点只看到本项目的文件。
- 全局 workspace 根目录仍可通过 Files 面板访问（作为文件中转站）。
- `userdata/projects/{project_id}/files` 是指向 `workspace/.files/{project_id}` 的 symlink，
  方便手动浏览，不影响 MF 运行时。

当 `project_id` 为空时（向后兼容），不使用 subPath，挂载整个 `userdata/workspace/`。

**两种典型用途：**
- 用途1：用户上传输入文件（如分子坐标 `.xyz`、力场参数），节点在运行时从
  `/mf/workspace/<filename>` 读取。
  MF YAML 的 `onboard_params` 中只填文件名（如 `geometry_file: h2o.xyz`），
  节点脚本自行在运行时定位文件，**编译器不做任何解引用**。
- 用途2：节点将大型输出（如波函数 `.gbw`、轨迹 `.trj`）写入 workspace，
  供人/Agent 事后检查，绕过 Argo 3 MB 参数限制。

**节点间数据传递仍使用 StreamIO**（未来用 Argo artifact 彻底解除大小限制），
workspace 不参与节点间数据流。

**Shell 脚本中的访问方式：**

```bash
source /mf/profile/mf2_init.sh
# WORKSPACE_DIR 已由 mf2_init.sh 设置为 /mf/workspace（已是项目级子目录）
ls "${WORKSPACE_DIR}/"
cp "${WORKSPACE_DIR}/large_file.bin" /mf/workdir/
```

**Python 脚本中的访问方式：**

```python
import os
workspace_dir = os.environ.get("MF_WORKSPACE_DIR", "/mf/workspace")
with open(f"{workspace_dir}/large_file.bin", "rb") as f:
    data = f.read()
```

**基础设施部署（一次性，hostPath 模式无需 NFS 操作）：**

```bash
kubectl apply -f infrastructure/k8s/workspace.yaml
kubectl get pvc mf-workspace -n miqroforge-v2  # 应显示 Bound
```

---

## 添加新节点的流程

1. **确定节点类型**：`compute`（需要基础镜像）或 `lightweight`（Python 脚本）

2. **创建节点目录**：

   ```
   nodes/<domain>/<node-name>/
   ├── nodespec.yaml      # NodeSpec 的 YAML 序列化（唯一事实来源）
   └── profile/           # 计算节点：run.sh + 输入模板（.template）；轻量节点：script.py
   ```

3. **编写 `nodespec.yaml`**，以 `nodes/NODESPEC_TEMPLATE.yaml` 为模板（含所有字段的注释说明）：

   ```bash
   cp nodes/NODESPEC_TEMPLATE.yaml nodes/<domain>/<node-name>/nodespec.yaml
   ```

   对于领域特有的注意事项（ORCA 的 MPI 变量、`xyzfile` 约定、Argo 3 MB 限制等），
   参阅对应的领域 README，如 `nodes/chemistry/orca/README.md`。

4. **运行索引重建**，使新节点可被工具链发现：

   ```bash
   bash scripts/mf2.sh nodes reindex
   ```

5. **添加 Schema 校验测试**（`tests/unit/test_orca_nodes.py`、`test_gaussian_nodes.py`、`test_psi4_nodes.py`、`test_cp2k_nodes.py` 可作参考）

> **量子节点例外**：`nodes/quantum/` 中的节点始终由领域专家手动编写和审核，不引入 Agent 生成。

---

## MPI / OpenMPI 节点强制要求

Kubernetes pod 默认以 root 用户运行，OpenMPI 默认拒绝 root 启动。
所有通过 OpenMPI 并行的节点（ORCA、CP2K 等），OMPI 环境变量应在**基础镜像 Dockerfile** 中通过 `ENV` 声明：

```dockerfile
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
```

这样 `nodespec.yaml` 中使用 `execution: {}` 即可，无需重复声明。
参考实现：`nodes/base_images/orca/Dockerfile`。
