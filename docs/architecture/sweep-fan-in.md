# Sweep 编译策略架构

## 编译流水线总览

```
MF YAML
  │
  ▼
Validator (validator.py)          — 校验 sweep 节点约束
  │
  ▼
Compiler  (compiler.py)
  ├─ _find_sweep_param()          — 找出声明了 parallel_sweep 的节点
  ├─ _detect_fan_in_nodes()       — 识别 fan-in 汇聚节点
  ├─ _identify_sweep_chains()     — 从 auto_fan_out 集合中提取 SweepChain
  ├─ _build_sweep_pipeline_template()  — 构建嵌套 DAG Pipeline 模板
  ├─ _build_sweep_pipeline_dag_task()  — 构建外层 DAG task（withParam）
  └─ compile_to_argo()            — 串联上述步骤，生成最终 Argo YAML
```

## 核心数据结构

### SweepChain

表示一个完整的 sweep 链（包含所有 auto fan-out 节点）：

```python
@dataclass
class SweepChain:
    sweep_node_id: str               # sweep 源节点 ID
    sweep_values: list[Any]          # 扫描值列表
    inner_node_ids: set[str]         # 嵌套 DAG 中所有节点 ID
    fan_in_connections:              # (inner_src_id, inner_src_port, outer_dst_id, outer_dst_port)
    inner_deps:                      # inner node ID → 其在链内依赖的 node ID 集合
    output_ports:                    # (inner_node_id, port_name) 用于 pipeline 输出
    external_inputs:                 # 链内节点依赖的链外节点
    external_deps:                   # 链内节点依赖的链外节点 ID 集合
```

## 编译步骤详解

### 1. Sweep Chain 提取 (`_identify_sweep_chains`)

从 sweep 源节点出发，使用 BFS/DFS 沿 `conn_map` 遍历下游节点，收集所有被 `auto_fan_out` 传播到的节点。

**停止条件（fan-in 边界）：**
- 节点被显式 `fan_in: true` 标记
- 节点不在 `auto_fan_out` 集合中（不是 sweep 链的一部分）

**输出：** 一个或多个 `SweepChain` 对象。

### 2. Pipeline 模板构建 (`_build_sweep_pipeline_template`)

每个 `SweepChain` 生成一个 Argo DAG 模板：

```
Template: sweep-pipeline-{sweep_node_id}
  inputs:
    parameters:
      - name: sweep_item           # 当前扫描值
      - name: ext__{node}__{port}  # 外部输入（链依赖的链外节点输出）
  dag:
    tasks:
      - name: {inner-node-id}      # 链内每个节点一个 task
        template: mf-{node-spec}
        arguments.parameters:
          - name: onboard_{param}
            value: "{{inputs.parameters.sweep_item}}"  # {{item}} 替换
        depends: "{deps}"          # 链内依赖关系
        when:                      # quality gate 条件（如有）
```

**关键细节：**

- `{{item}}` 在 `onboard_params` 中被替换为 `{{inputs.parameters.sweep_item}}`
- Quality gate 的 `when` 条件生成在嵌套 DAG 内部（操作标量值）
- Pipeline 输出参数带有 `default: ""`，处理 quality gate 跳过场景
- 外部输入作为 Pipeline 的 input parameters 传入，值来自外层 DAG 节点的输出

### 3. 外层 DAG Task 构建 (`_build_sweep_pipeline_dag_task`)

生成外层 DAG 中的 task，使用 `withParam` 进行扇出：

```yaml
- name: sweep-pipeline-{sweep_node_id}
  template: sweep-pipeline-{sweep_node_id}
  withParam: "{{item}}: [v1, v2, ...]"    # JSON array
  arguments:
    parameters:
      - name: sweep_item
        value: "{{item}}"
      - name: ext__{node}__{port}
        value: "{{tasks.{outer_task}.outputs.parameters.{port}}}"
```

### 4. dep_map / conn_map 重映射

Sweep 链中的节点从外层 DAG 中移除后，其他节点的依赖关系和连接引用需要重映射：

- **dep_map：** 原来依赖链内节点 A 的节点，改为依赖 `sweep-pipeline-{sweep_node_id}`
- **conn_map：** 原来从链内节点 A 某端口读取的节点，改为从 `sweep-pipeline-{sweep_node_id}` 的对应输出参数读取

重映射表由 `compile_to_argo()` 中的 `inner_to_pipeline` 和 `port_remap` 字典维护。

## Quality Gate 在 Sweep 中的处理

### 问题

在 flat DAG 中，quality gate 的 `when` 条件（如 `{{tasks.node.outputs.parameters.gate}} == 'true'`）作用于聚合后的数组，导致逻辑不正确。

### 解决方案

嵌套 DAG 方案天然解决了这个问题：quality gate 的 `when` 条件在 Pipeline 模板内部生成，每个扫描值实例独立判断。

```
Pipeline 内部（每个 item 独立）:

  geo-opt (item=0.5)
    ↓ gate: converged == 'true'?    ← 标量判断
  sp-calc (item=0.5)  or  跳过

  geo-opt (item=0.6)
    ↓ gate: converged == 'true'?
  sp-calc (item=0.6)  or  跳过
```

### 各策略行为

| 策略 | gate 不通过时 | `when` 条件 | Pipeline 输出 |
|------|-------------|------------|--------------|
| `must_pass` | 该实例后续节点跳过，实例失败 | `when: ...` | `default: ""` |
| `warn` | 警告但继续执行 | 无 `when` | 正常输出 |
| `ignore` | 完全跳过检查 | 无 `when` | 正常输出 |

## 前端集成

编译后的 Argo YAML 中，sweep pipeline 的每个实例在 Argo 节点状态中显示为独立 Pod，共享同一个 `templateName`（如 `mf-geom-input`）。

前端 `RunsPanel.tsx` 的 `parseSteps()` 按 `templateName` 分组：

- **单实例节点：** 直接显示 phase badge（现有行为）
- **多实例节点（sweep）：** 显示分段进度条
  - 绿色 = Succeeded
  - 蓝色 = Running（带脉冲动画）
  - 红色 = Failed
  - 灰色 = Pending
  - 点击可展开查看每个实例的状态
  - Steps 区域有独立滚动（`max-h-48 overflow-y-auto`）
