# MiQroForge 2.0

面向工业级生产的**量子 + AI 科学计算平台**。以规范化节点为核心资产，以 Argo Workflow 为执行引擎，以 LLM Agent 驱动工作流编排。

---

## 前提条件

开始之前请确认以下软件已在服务器上就绪：

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| Python | >= 3.10 | 节点 Schema 开发和 Agent 开发 |
| Docker | 任意 | 构建计算节点镜像 |
| kubectl | 任意 | 操作 Kubernetes 集群 |
| Kubernetes 集群 | >= 1.24 | 运行 Argo Workflow |
| Argo Workflow | >= 3.0 | 工作流调度引擎 |

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
- 输出完整 log 至 `logs/setup/`

> 已有 KubeSphere / 云厂商集群等？配好 kubeconfig 后此脚本会自动识别并跳过 k3s 安装。

### 第二步：Python 开发环境

```bash
bash scripts/setup_phase1.sh
```

安装 Phase 1 所需 Python 依赖（pydantic v2、pytest、pyyaml、python-dotenv）。
**无需 sudo**，推荐在虚拟环境中运行：

```bash
python3 -m venv .venv && source .venv/bin/activate
bash scripts/setup_phase1.sh --yes
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
| `submit <yaml>` | 提交工作流到 `miqroforge-v2` |
| `list` | 列出所有工作流 |
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
| 国内服务器 / 私有集群 | 填写私有 Harbor 前缀，如 `harbor.example.local/library` |

修改 `.env` 中的 `IMAGE_REGISTRY`，同时更新 `workflows/examples/hello-world.yaml` 中的 `image-registry` 默认参数值。

> **注意**：示例工作流 `hello-world.yaml` 使用 `busybox` 镜像。请确保该镜像在你的仓库中可用，或替换为集群内已有的等效镜像。

---

## 运行测试

```bash
# 单元测试（无需集群）
pytest tests/unit/ -v

# 集成测试（需要运行中的 Argo 集群）
pytest tests/integration/ -v
```

集成测试会自动提交 `hello-world.yaml` 并验证工作流成功完成，完成后自动清理。

---

## 目录结构速查

```
nodes/          ★ 核心资产：规范化计算节点（Pydantic Schema + Dockerfile）
workflows/      Argo Workflow YAML 模板和示例
agents/         Phase 2: LangGraph Agent（Planner + YAML Coder）
api/            Phase 2: FastAPI 网关
vectorstore/    Phase 2: 节点 RAG 检索（ChromaDB）
infrastructure/ Kubernetes / Argo 部署配置
scripts/        环境检测与安装脚本（含 mf2.sh CLI）
tests/          单元测试 / 集成测试
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
| `IMAGE_REGISTRY` | **第一步完成后立即填写** | 问运维你的集群用什么镜像仓库。无私有仓库则留空（需能访问 Docker Hub） |
| `ARGO_SERVER_URL` | **第一步完成后立即填写** | 运行 `bash scripts/mf2.sh ui` 会显示地址；或 `kubectl get svc argo-server -n argo` |
| `ARGO_NAMESPACE` | 默认 `miqroforge-v2`，通常不需要改 | — |
| `ARGO_TOKEN` | 提交工作流时若提示鉴权失败 | 运行 `argo auth token` |
| `REGISTRY_URL` / `REGISTRY_PROJECT` | 构建并推送节点 Docker 镜像时 | 问运维你的 Harbor / Registry 地址 |
| `OPENAI_API_KEY` | Phase 2 开发 Agent 时 | 从 OpenAI 控制台获取 |
| `CHROMA_PERSIST_DIR` | Phase 2 开发 RAG 检索时 | 默认 `./data/chroma`，通常不需要改 |

**典型的新开发者流程：**

```bash
# 1. 基础设施就绪后
cp .env.example .env

# 2. 填写镜像仓库（必填，否则工作流拉不到镜像）
#    编辑 .env，设置 IMAGE_REGISTRY=harbor.xxx.local/library

# 3. 填写 Argo 地址（运行 mf2 ui 可自动获取）
#    编辑 .env，设置 ARGO_SERVER_URL=https://...

# 4. 跑一次集成测试验证配置正确
pytest tests/integration/ -v
```

---

## 开发阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 基础设施 + 规范节点建库 | 🔨 当前开发 |
| Phase 2 | LLM 驱动工作流编排 | 🔨 当前开发 |
| Phase 3 | Agent 节点生成与自动 Debug | 🔲 未开始 |
| Phase 4 | 人类审核与智能分析前端 | 🔲 未开始 |
