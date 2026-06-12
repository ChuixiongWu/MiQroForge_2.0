# Node System

**Hierarchy:** `nodes/` — The core asset of MiQroForge: structured, schema-validated computational nodes.

This file covers the **node classification system** and **platform-level node conventions**.
For the Pydantic schema layer (NodeSpec, IO types, Resources), see `nodes/schemas/AGENTS.md`.
For container/image conventions (BYOB, MPI), see `nodes/base_images/AGENTS.md`.

## STRUCTURE
```
nodes/
├── AGENTS.md              # ★ This file: node classification + platform conventions
├── schemas/AGENTS.md      # Pydantic Schema system (NodeSpec, IO, Resources)
├── base_images/AGENTS.md  # Docker images: BYOB, MPI, Workspace PVC
├── chemistry/             # 32 formal nodes: ORCA(9), Gaussian(9), Psi4(9), CP2K(4), preprocessing(1)
├── test/                  # 4 test/debug nodes
├── quantum/               # Quantum nodes (Phase 3, expert hand-written only)
├── node_index.yaml        # Generated (gitignored): run `mf2 nodes reindex`
└── NODESPEC_TEMPLATE.yaml # Template for new nodes
```

---

## 节点分类体系

### 正式节点（Formal Nodes）
- 完整 NodeSpec（`nodespec.yaml`），入节点库（`node_index.yaml`）
- 严格 I/O Schema + 语义类型 + (可选)Quality Gate + 资源声明
- 适用于：核心计算（ORCA、Gaussian、GROMACS）、量子计算、关键后处理
- 分为 Compute（重型容器）和 Lightweight（Python 脚本或 Shell 入口）两种执行类型
  - Lightweight 支持三种模式：`inline_script`（内联 Python）、`script_path`（外置 .py）、
    `entrypoint_script`（Profile-based shell，行为与 compute 一致，仅换镜像）
- Phase 2 M4 起，非量子/非AI增强的正式节点可由 Node Generator Agent（Prefab 模式）辅助生成

### 生成类节点

- 目前包含临时节点(ephemeral)和预制节点(prefab)
- 生成类节点与正式节点可自由连接；编译器做基本类型兼容检查（file/text/json/number/boolean），不做语义类型检查
- I/O 路径约定与正式节点一致：`/mf/input/I1`、`/mf/output/O1`
- **Sweep 限制**：生成类节点不可作为 sweep 源（`parallel_sweep`），也不可出现在 sweep 内部分支（auto_fan_out）中。仅可作为 fan-in 结束节点（如收集 sweep 各分支数据并画图）

#### 临时节点（Ephemeral Nodes）
- **纯一次性**：只存在于单次工作流执行中，不入节点库，不保留
- MF YAML 中**仅做声明**：`ephemeral: true` + `onboard_params.description` + 端口数量（自动命名 I1/I2…、O1/O2…）+ Stream IO 连接关系
- **不在 MF YAML 中写脚本**——实际 Python 脚本由**运行时 Ephemeral Agent API** 根据声明和上下文自动生成
- 适用于：绘图、格式转换、数据提取、一次性胶水逻辑
- Agent 通过 `pip_install` 工具按需安装额外依赖（`ephemeral-py` 镜像已预装 numpy/matplotlib/scipy/pandas 等）
- 编译器生成薄 wrapper 脚本，Pod 运行时调用 Agent API 完成脚本生成 + 沙箱执行 + 评估

**MF YAML 临时节点声明示例：**
```yaml
  - id: plot-energy-curve
    ephemeral: true
    onboard_params:
      description: "将几何优化各步能量绘制为势能曲线，输出 PNG 图片"
    ports:
      inputs: 1    # I1
      outputs: 1   # O1
connections:
  - from: xxx.xxx
    to: plot-energy-curve.I1
  - from: plot-energy-curve.O1
    to: yyy.yyy
```

**两阶段架构：**
1. **编译时**：编译器（`mf2 compile`）扫描 MF YAML，识别 `ephemeral: true` 节点，为每个生成一个薄 wrapper 脚本
2. **运行时**：Argo Pod 启动后，wrapper 调用 `POST /api/v1/agents/ephemeral`，服务端完成：
   - ReAct Agent 内循环：LLM 绑定 `sandbox_execute` + `pip_install` 工具，自主生成并执行脚本
   - 沙箱执行：Docker 容器隔离（`ephemeral-py:3.11` 镜像），需 Docker daemon 运行
   - 评估：执行结果检查 + 视觉评估（对生成的图片做多模态检查）
   - 外循环：generate → evaluate → retry（默认最多 2 轮）
3. 最终产出可直接提交的 Argo YAML（wrapper 脚本内联到 Argo script template）

#### Prefab 节点（Prefab Nodes）

- 由 **Node Generator Agent（Prefab 模式）** 通过 Generator-Evaluator 循环辅助生成的正式节点。在 MF YAML 中使用 `prefab: true` 字段（与 ephemeral 互斥）。节点 ID 即为 `tmp/` 子目录名——编译器自动从 `proj/tmp/<node_id>/` 读取预生成 files。
- 双路径工作流：
  - **设计+运行（-1 循环）**：用户在前端拖入 Prefab 节点，填写 prompt、设定端口，**点击 Generate**。LLM 生成 nodespec.yaml + profile/run.sh + 输入模板，此过程无 sandbox 测试。用户可通过 Inspector 修改 Onboard 参数值。节点连入工作流后，ReAct Agent 内循环（含 sandbox 测试）+ Evaluator 评判，最多 2 轮外循环。对 Generator 来说如同一次"有已生成 nodespec 等文件、无 Evaluator 意见"的外循环新轮次
  - **直接运行（runtime）**：用户在前端拖入 Prefab 节点，填写 prompt、设定端口，**不**点击 Generate，节点直接连入工作流运行。ReAct Agent 内循环（含 sandbox 测试）+ Evaluator 评判，最多 2 轮外循环。
- 生成结果保存到 `userdata/projects/{proj}/tmp/{node_name}/`，经人工审核后通过 `POST /api/v1/agents/node/accept` 端点入库
- 入库位置：`userdata/nodes/{category}/{node_name}/nodespec.yaml`
- 与手写正式节点享有相同的 Schema 校验和节点索引流程

---

## 平台级节点约束

### 节点目录结构

每个节点目录包含 `nodespec.yaml` 和 `profile/`（计算节点还含 `run.sh` 及输入模板 `.template`）。
完整字段说明见 `nodes/schemas/README.md`。

> **节点输入模板约定**：`.template` 文件使用 Python 标准库 `string.Template` 语法（`$var` / `${var}`），**不依赖 jinja2**。
> 条件逻辑（如 dispersion 是否启用）在 `run.sh` 的 Python 渲染块中预计算后以变量形式注入，而不是放进模板语法。
> 这样每个计算镜像无需安装任何额外依赖，只需容器内置的 Python 标准库即可。

### 大型二进制输出（Argo 3 MB 限制）

Argo output parameter 上限为 **3 MB**。GBW 波函数等大型二进制输出的
`io_type.category` 必须为 `software_data_package`；编译器的 `connected_outputs`
机制会自动跳过未被消费的大型端口，避免触发 `Request entity too large` 错误。

> **SDP 端口如何跨节点传输？** `software_data_package` 类端口不经过 Argo parameter，
> 而是通过 workspace PVC 的 `.stream/` 目录在节点间 `cp`。
> 完整机制见 [`nodes/schemas/README.md`](schemas/README.md#sdp-节点间传输完整机制)。
