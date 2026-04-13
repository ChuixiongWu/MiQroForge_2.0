# MiQroForge 2.0

面向工业级生产的**量子 + AI 科学计算平台**。以规范化节点为核心资产，以 Argo Workflow 为执行引擎，以 LLM Agent 驱动工作流编排。

---

## 前提条件

开始之前请确认以下软件已在服务器上就绪：

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| Python | >= 3.10 | Schema 开发和 Agent 开发 |
| Docker | 任意 | 构建计算节点镜像 |
| kubectl | 任意 | 操作 Kubernetes 集群 |
| Kubernetes 集群 | >= 1.24 | 运行 Argo Workflow |
| Argo Workflow | >= 3.0 | 工作流调度引擎 |
| Node.js | >= 18 | 前端开发（可选，仅前端开发时需要） |

**已有 Kubernetes 集群？** 只需确保 `~/.kube/config` 配置正确，直接跳到[快速开始](#快速开始)。

**没有集群？** 用 `setup_infra.sh` 自动处理，见下文。

---

## 快速开始

### 第一步：基础设施（需要 sudo，首次配置时运行）

```bash
sudo bash scripts/setup_infra.sh
```

此脚本会自动：
- 启动 Docker daemon
- **若已有集群**（检测到 `/etc/kubernetes/admin.conf` 等）：直接配置 kubeconfig，跳过安装
- **若无集群**：安装 k3s 单节点本地集群（开发用途），优先使用国内镜像源
- 部署 Argo Workflow Server 到集群
- 部署 Workspace PV/PVC（`mf-workspace`，挂载 `userdata/workspace/`，节点读写用户文件）
- 输出完整 log 至 `logs/setup/`

> 已有 KubeSphere / 云厂商集群等？配好 kubeconfig 后此脚本会自动识别并跳过 k3s 安装。

### 第二步：Python 开发环境

```bash
python3 -m venv .venv && source .venv/bin/activate
bash scripts/setup_phase1.sh --yes
```

安装所需 Python 依赖（pydantic v2、pytest、pyyaml、python-dotenv、langchain、langgraph 等）。

### 第三步：配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写 ARGO_SERVER_URL、IMAGE_REGISTRY 等
```

### 第四步：初始化节点索引

```bash
bash scripts/mf2.sh nodes reindex
```

### 验证环境

```bash
bash scripts/check_env.sh
```

全部 ✔ 即可开始开发。

---

## mf2 开发者 CLI

`scripts/mf2.sh` 是面向开发者的命令行工具，封装了常用的集群操作。

```bash
bash scripts/mf2.sh <command> [args]
```

| 命令 | 说明 |
|------|------|
| `status` | 检测开发环境状态 |
| `ui [port]` | 输出 Argo UI 的 SSH 转发命令 |
| `nodes list` | 列出节点库中所有节点 |
| `nodes search <keyword>` | 搜索节点 |
| `nodes info <node-id>` | 查看节点详情 |
| `nodes reindex` | 重建 `node_index.yaml`（节点有变更时运行） |
| `validate <mf.yaml>` | 校验 MF 工作流 |
| `compile <mf.yaml>` | 编译 MF → Argo YAML |
| `run <mf.yaml>` | 校验 + 编译 + 提交到 Argo + 流式日志 |
| `logs <name>` | 查看工作流日志 |

### 远程访问 Argo UI

通过 SSH 连接到开发服务器的用户，在**服务器端**运行：

```bash
bash scripts/mf2.sh ui
```

脚本会自动读取集群实际 NodePort，输出需要在**本地电脑**执行的 SSH 转发命令，格式如下：

```bash
# 在本地电脑执行（示例）
ssh -L 8088:<node-ip>:<node-port> -N <SSH别名>
```

然后在本地浏览器打开 `https://localhost:8088`，切换 namespace 至 `miqroforge-v2` 即可查看工作流。

> 浏览器提示证书不安全属正常现象（自签名证书），直接跳过继续即可。

---

## 镜像仓库配置

工作流中的节点容器镜像需要从仓库拉取。不同网络环境下配置不同：

| 环境 | 配置方式 |
|------|----------|
| 可访问 Docker Hub | `.env` 中 `IMAGE_REGISTRY=`（留空） |
| 国内服务器 | `.env` 中填 `DOCKER_HUB_MIRROR=docker.m.daocloud.io` 等镜像站 |
| 私有集群 | `.env` 中填 `IMAGE_REGISTRY=harbor.example.local/library` |

---

## 运行测试

```bash
# 单元测试（无需集群）
pytest tests/unit/ -v

# 集成测试（需要运行中的 Argo 集群）
pytest tests/integration/ -v
```

---

## 目录结构速查

```
nodes/          ★ 核心资产：规范化计算节点（Pydantic Schema + nodespec.yaml）
workflows/      MF 工作流 YAML + 编译管线（validate / compile / run）
agents/         Phase 2: LangGraph Agent 层（Planner / YAML Coder / Node Generator）
api/            FastAPI 网关（nodes / workflows / runs / agents API）
node_index/     节点索引引擎（扫描 nodespec.yaml → node_index.yaml）
llm_gateway/    Phase 2 M3: LLM Gateway Service（AI 增强节点的 LLM 代理）
frontend/       React Flow 可视化编辑器（Vite + TypeScript）
infrastructure/ Kubernetes / Argo 部署配置（含 Workspace PVC）
scripts/        开发者 CLI（mf2.sh）与环境初始化脚本
tests/          单元测试 / 集成测试
userdata/       运行时数据（gitignored）：workspace / runs / 向量库 / AI 生成节点
docs/           架构文档
```

---

## 配置环境变量

复制 `.env.example` 并填写：

```bash
cp .env.example .env
```

### 什么时候填、填什么

| 变量 | 何时需要 | 如何获取 |
|------|----------|----------|
| `IMAGE_REGISTRY` | **第一步完成后立即填写** | 无私有仓库则留空（需能访问 Docker Hub） |
| `ARGO_SERVER_URL` | **第一步完成后立即填写** | 运行 `bash scripts/mf2.sh ui` 会显示地址 |
| `ARGO_NAMESPACE` | 默认 `miqroforge-v2`，通常不需要改 | — |
| `ARGO_TOKEN` | 提交工作流时若提示鉴权失败 | 运行 `argo auth token` |
| `DOCKER_HUB_MIRROR` | 国内服务器拉取 Docker Hub 镜像慢时 | 填入镜像站域名，如 `docker.m.daocloud.io` |
| `userdata/models.yaml` | **Phase 2 开发 Agent 时必须配置** | 从 `models.yaml.example` 复制，填入 `proxy.api_key` |

**典型的新开发者流程：**

```bash
# 1. 基础设施就绪后
cp .env.example .env

# 2. 填写 Argo 地址（运行 mf2 status 可自动获取）
#    编辑 .env，设置 ARGO_SERVER_URL=https://...

# 3. 重建节点索引
bash scripts/mf2.sh nodes reindex

# 4. 跑一次单元测试验证配置正确
pytest tests/unit/ -v
```

---

## 开发阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 基础设施与规范节点建库 | ✅ 完成 |
| Phase 2 | 智能工作流编排（LangGraph Agent + 临时节点 + AI 增强节点） | 🔨 当前开发 |
| Phase 3 | 全面智能化：项目记忆、自动 Debug 与跨项目知识 | 🔲 未开始 |
