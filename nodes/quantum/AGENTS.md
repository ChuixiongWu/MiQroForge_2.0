# Quantum Nodes

**Hierarchy:** `nodes/quantum/` — Phase 3, expert hand-written quantum computing nodes.

> **Phase 3** — No Agent generation. Every quantum node is manually authored and reviewed
> by domain experts. The AI toolchain (Planner, YAML Coder, Node Generator) does NOT touch
> quantum nodes. Quantum workflows are composed from these hand-built nodes via MF YAML.

---

## STRUCTURE

```
quantum/
├── AGENTS.md              # ★ This file
├── README.md              # Data contract strings + pipeline topology
├── chem-prep/             # RHF mean-field preparation (PySCF)
├── ewf-decompose/         # Embedded wavefunction decomposition (Vayesta)
├── qsci-prep/             # QSCI circuit preparation (OpenFermion, Qiskit)
├── hardware-execute/      # AWS Braket circuit execution (this doc's focus)
└── qsci-assemble/         # QSCI subspace assembly + energy estimation
```

---

## 管道总览

Quantum EWF-QSCI 五节点管道：

```
chem-prep ──► ewf-decompose ──► qsci-prep ──► hardware-execute ──► qsci-assemble
```

输入：一个优化过的分子几何结构（XYZ）。输出：QSCI 子空间能量估计。

各节点的 I/O 数据契约（ecosystem:data_type 字符串）见 `nodes/quantum/README.md` 的
"Data Contract Strings" 表格。本文件不重复列出；需要查端口连接兼容性时以该表格为准。

---

## 如何编写量子节点

每个量子节点遵循与 `nodes/chemistry/` 下的计算节点完全相同的目录结构约定。
以下以 `chem-prep`（最干净的例子）为模板说明。

### 目录结构

```
nodes/quantum/<node-name>/
├── nodespec.yaml          # NodeSpec — Single Source of Truth
└── profile/
    ├── run.sh             # Shell 入口（compiler 设为 container command）
    └── main.py            # Python 计算逻辑（由 run.sh 调用）
```

`mf2 compile` 时，编译器从 `nodespec.yaml` 旁边的 `profile/` 目录读取所有文件，
注入到 K8s ConfigMap（`mf-profile-<node-name>-<version>`），并在容器启动后挂载到
`/mf/profile/`。`run.sh` 被设为容器的 `command`。

### run.sh 约定

`run.sh` 是 shell 编排层。职责：
1. 初始化运行时环境
2. 校验并 staging 输入
3. 将 onboard 参数 `export` 为环境变量
4. 调用 `python3 /mf/profile/main.py`

```bash
#!/usr/bin/env bash
# <node-name> — <one-line description>
set -euo pipefail

# ── MF2 runtime bootstrap ────────────────────────────────────────────────
# compiler injects: source /mf/profile/mf2_init.sh
source /mf/profile/mf2_init.sh

mf_banner "<node-name>" "brief description"

# ── Stage stream inputs ──────────────────────────────────────────────────
# 上游节点的输出被挂载到 /mf/input/<port_name>
# （software_data_package 经 Workspace PVC 传递，其余经 Argo parameter）
STREAM_DATA=$(cat "${INPUT_DIR}/<port_name>")

# ── Export onboard params for Python ─────────────────────────────────────
# 编译器自动生成 mf_node_params.sh（由 mf2_init.sh auto-source），
# 将每个 onboard_input.name 转为同名的 shell 变量。
export MF_<PARAM>="<value or variable reference>"

# ── Execute ──────────────────────────────────────────────────────────────
python3 /mf/profile/main.py
```

**关键点：**

- 编译器在构建 ConfigMap 时**自动注入** `nodes/common/mf2_init.sh` 到每个节点的
  ConfigMap 中（路径 `/mf/profile/mf2_init.sh`），因此 `run.sh` 顶部直接写
  `source /mf/profile/mf2_init.sh` 即可（当前所有量子节点都这样做）。
  - 编译器也支持把单独一行 `# MF2 init` 自动替换为该 source 命令（见 compiler 的
    `_process_run_sh`，未命中则原样保留）；两种写法均可，直接写 source 更直观。
  - `mf2_init.sh` 提供：`INPUT_DIR=/mf/input`、`OUTPUT_DIR=/mf/output`、
    `WORKDIR=/mf/workdir`、`WORKSPACE_DIR=/mf/workspace`，以及 helper 函数
    `mf_param`、`mf_banner`、`mf_write_xyz`。
  - `mf2_init.sh` 在加载时自动 `source /mf/profile/mf_node_params.sh`——
    编译器为每个节点生成此文件，内含所有 `onboard_inputs` 的变量赋值。
    因此在 `run.sh` 中**不需要**手动调用 `mf_param`，直接使用 shell 变量即可
    （如 `$charge`、`$basis_set`）。

- **禁止**在 `run.sh` 中内联 Python heredoc（`python3 << 'PYEOF' ... PYEOF`）。
  这是 Phase 2 早期的临时形式，已经被废弃。必须使用独立的 `main.py` 文件。

### main.py 约定

`main.py` 是纯 Python 计算逻辑。职责：
1. 从 `os.environ` 读取 onboard 参数
2. 从 `/mf/input/<port_name>` 读取 stream input
3. 执行计算
4. 将结果写入 `/mf/output/<port_name>`

```python
#!/usr/bin/env python3
import os
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get("MF_OUTPUT_DIR", "/mf/output"))
INPUT_DIR = Path(os.environ.get("MF_INPUT_DIR", "/mf/input"))

# ── Read onboard params (exported by run.sh) ─────────────────────────────
param_x = os.environ.get("MF_PARAM_X", "default")

# ── Read stream inputs ───────────────────────────────────────────────────
raw_data = (INPUT_DIR / "stream_port_name").read_text()

# ── Compute ──────────────────────────────────────────────────────────────
result = do_computation(raw_data, param_x)

# ── Write outputs ────────────────────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "output_port_name").write_text(str(result))
```

**输出写入的位置必须是 `/mf/output/<port_name>`**，其中 `<port_name>` 严格匹配
`nodespec.yaml` 中 `stream_outputs` 和 `onboard_outputs` 的 `name` 字段。
编译器会按名称收集这些文件作为 Argo output parameters。

---

## 基础镜像

| 镜像逻辑名 | 包含软件 | 适用节点 |
|-----------|---------|---------|
| `quantum-exec-0.1` | amazon-braket-sdk 1.110.1, pennylane 0.42.3, openfermion | 电路构建、量子硬件/SV1 执行 |
| `classical-chem-0.1` | pyscf 2.8.0, vayesta, openfermion 1.7.1 | 经典量子化学（RHF、嵌入） |

镜像注册表：`nodes/base_images/registry.yaml`。
节点通过 `metadata.base_image_ref` 字段引用镜像逻辑名（如 `base_image_ref: quantum-exec-0.1`），
编译器运行时从 `registry.yaml` 解析为 `image:tag`。

---

## I/O Schema 要点

量子节点的 `stream_inputs` 和 `stream_outputs` 使用四类 `io_type.category`（定义见
`nodes/schemas/README.md`）：

| `category` | 含义 | 量子节点中何时使用 |
|-----------|------|-------------------|
| `physical_quantity` | 带量纲的科学量（如几何坐标） | XYZ 坐标输入（`unit: Ang`） |
| `software_data_package` | 特定生态系统内的数据格式 | HDF5 波函数、OpenQASM3 电路、Braket measurement counts |
| `report_object` | 人类/AI 可读产出 | 暂未使用 |
| `logic_value` | 流程控制量 | 暂未使用 |

`software_data_package` 是最常见的量子端口类型，需要同时声明 `ecosystem` 和 `data_type`
两个字段（如 `{ecosystem: openqasm, data_type: circuit-qasm3}`）。连接时两个字段必须严格匹配。

`onboard_inputs` 是面板参数（用户在前端 Inspector 中填写），`onboard_outputs` 是面板返回值。
`onboard_outputs` 可以设置 `quality_gate: true` 来控制工作流分支（如 `scf_converged`）。

完整字段说明见 `nodes/schemas/README.md`。

---

## AWS Braket 硬件节点模式 (hardware-execute)

`hardware-execute` 是连接 AWS Braket 真实量子硬件的唯一节点。其关键设计如下。

### 凭证注入

```yaml
# nodes/quantum/hardware-execute/nodespec.yaml:
execution:
  secret_refs:
    - aws-braket-creds
```

`secret_refs` 是 `ComputeExecutionConfig` 上的 `list[str]` 字段（默认 `[]`）。
编译器在 `_build_compute_template()` 中将其转换为 Argo container spec 的 `envFrom` 块：

```yaml
# 编译器生成的 Argo YAML：
container:
  envFrom:
    - secretRef:
        name: aws-braket-creds
        optional: true
```

Kubelet 在 pod 准入时解析 Secret，将所有 key 注入为容器环境变量。
Boto3 SDK 按标准约定从 `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、
`AWS_DEFAULT_REGION` 读取。无需 pod ServiceAccount 的 `secrets` 权限。

> **废弃方案（不要使用）：** Wave 1 曾将凭证 staging 到 Workspace PVC 中
> （`/mf/workspace/.aws/credentials`）。该方案已被 `envFrom` 替代，
> 新部署只需创建一次 Secret，不需要 per-project staging。
> 详见 `infrastructure/k8s/aws-braket-creds-injection.md` §3。

完整凭证机制文档：[infrastructure/k8s/aws-braket-creds-injection.md](../../infrastructure/k8s/aws-braket-creds-injection.md)

### 后端选择

硬件执行节点通过 `onboard_inputs` 中的 `backend` 枚举字段选择执行后端：

| `backend` 值 | 目标 | region | 是否需要凭证 |
|--------------|------|--------|-------------|
| `local` | `LocalSimulator`（免费） | — | 否 |
| `sv1` | Amazon SV1 云模拟器 | us-east-1（固定） | 是 |
| `rigetti-cepheus` | Rigetti Cepheus-1-108Q | us-west-1 | 是 |
| `iqm-emerald` | IQM Emerald | eu-north-1 | 是 |
| `ionq-forte` | IonQ Forte-Enterprise-1 | us-east-1 | 是 |
| `aqt-ibex` | AQT Ibex-Q1 | eu-north-1 | 是 |
| `iqm-garnet` | IQM Garnet | eu-north-1 | 是 |

`profile/main.py` 根据 backend 枚举决定执行路径：`local` 用 `LocalSimulator`（无凭证）；
`sv1` 固定 `AWS_DEFAULT_REGION=us-east-1`；具名 QPU 从 `main.py` 内的 `DEVICE_ARNS`
映射查出唯一 ARN，并从 ARN 第 4 个冒号字段提取 region，在创建 Braket session 前导出，
覆盖凭证 Secret 的默认 region（ARN 格式 `arn:aws:braket:<region>::device/qpu/<vendor>/<name>`）。

### 电路输入 / 测量输出

- **输入**：`stream_inputs.ansatz_circuit`，类型 `software_data_package(ecosystem: openqasm, data_type: circuit-qasm3)`。
  期望包含 measurement 指令的有效 OpenQASM 3.0 源字符串。
  通常由 `qsci-prep` 节点生成。
- **输出**：`stream_outputs.measurement_counts`，类型 `software_data_package(ecosystem: braket, data_type: measurement-counts-json)`。
  JSON 对象，将 measurement bitstring 映射到整数 shot counts
  （示例：`{"00": 512, "11": 488}`）。Bitstring 零填充到电路 qubit 数。

### 如何添加新的 QPU 设备

设备选择通过 `backend` 枚举完成。每个具名 QPU 在 `profile/main.py` 的 `DEVICE_ARNS`
字典中映射到其全球唯一 ARN（region 编码在 ARN 第 4 个冒号字段，运行时自动提取）。
添加新设备两步：

1. 在 `hardware-execute/profile/main.py` 的 `DEVICE_ARNS` 中加一行：
   `"<short-name>": "arn:aws:braket:<region>::device/qpu/<vendor>/<model>"`
2. 在 `hardware-execute/nodespec.yaml` 的 `backend.allowed_values` 中加入同名 `<short-name>`

ARN 可在 AWS Braket 控制台或 `aws braket search-devices` 查到。自由文本的
`device_arn` onboard input 已被移除（避免无效 ARN 与面板冗余）。

---

## 如何添加 / 轮换 AWS 凭证

### 一次性创建（首次配置时）

```bash
kubectl create secret generic aws-braket-creds \
  --namespace=miqroforge-dev \
  --from-literal=AWS_ACCESS_KEY_ID=... \
  --from-literal=AWS_SECRET_ACCESS_KEY=... \
  --from-literal=AWS_DEFAULT_REGION=us-east-1
```

或使用声明式模板（参考 `infrastructure/k8s/aws-braket-secret.example.yaml`，
**不要直接 apply 示例文件**——复制后填入真实 key 再 apply）：

```bash
cp infrastructure/k8s/aws-braket-secret.example.yaml \
   infrastructure/k8s/aws-braket-secret.yaml
# 编辑 aws-braket-secret.yaml，替换 placeholder key
kubectl apply -f infrastructure/k8s/aws-braket-secret.yaml
```

### 轮换凭证

直接重新 apply Secret。无需 per-project staging，无需重建节点 image，
无需修改任何 `nodespec.yaml`。所有使用 `secret_refs: [aws-braket-creds]` 的节点
在下次 pod 启动时自动拿到新凭证。

```bash
kubectl delete secret aws-braket-creds --namespace=miqroforge-dev
kubectl create secret generic aws-braket-creds \
  --namespace=miqroforge-dev \
  --from-literal=AWS_ACCESS_KEY_ID=<new-key> \
  --from-literal=AWS_SECRET_ACCESS_KEY=<new-secret> \
  --from-literal=AWS_DEFAULT_REGION=us-east-1
```

### 凭证来源

| 项目 | 值 |
|------|-----|
| AWS Account | 533612071261 |
| IAM User | mqe-quantum-dev |
| Region | us-east-1 |
| S3 Bucket | amazon-braket-mqe-533612071261 |
| K8s Namespace | miqroforge-dev |
| Secret Name | aws-braket-creds |
| Secret Keys | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`（大写，boto3 标准） |

详见 `infrastructure/k8s/aws-braket-creds-injection.md` §2 和 §5。

---

## 反膨胀约束

量子节点数量极少（5 个），每个节点解决一个明确的计算步骤。
在添加新节点之前，先问：
1. 这个计算步骤是否可以通过**修改已有节点的 onboard 参数**完成？（如 `charge`、`basis_set`）
2. 这个输出是否**下游已有节点可以直接消费**？

大部分"新需求"通过参数化已有节点即可满足，不需要新增节点目录。
如果确实需要新节点，请先审阅 `nodes/NODESPEC_TEMPLATE.yaml` 并参考本章节的模板。
