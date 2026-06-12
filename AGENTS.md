# MiQroForge 2.0 — AGENTS.md

**Branch:** dev | **Phase:** 2 (当前开发) | **Updated:** 2026-05-26

> **Root hierarchy:** Project overview, design philosophy, and development principles.
> Domain-specific detail lives in subdirectory `AGENTS.md` files — see the [index](#子-agentsmd-索引) below.

---

## HIERARCHY

```
MF2_dev/
├── AGENTS.md                    # ★ Root (this file)
├── nodes/
│   ├── AGENTS.md                # Node classification (formal/ephemeral/prefab)
│   ├── schemas/AGENTS.md        # Pydantic schema system (NodeSpec, IO, Resources)
│   ├── base_images/AGENTS.md    # Docker images (BYOB, MPI, Workspace PVC)
│   └── quantum/AGENTS.md        # Quantum nodes (Phase 3), AWS Braket hardware execution
├── agents/AGENTS.md             # LangGraph Agent layer + Phase 2 milestones
├── api/AGENTS.md                # FastAPI backend
├── frontend/src/AGENTS.md       # React frontend (canvas, stores, components)
├── node_index/AGENTS.md         # Node indexing engine
├── vectorstore/AGENTS.md        # RAG vector retrieval (ChromaDB)
└── workflows/pipeline/AGENTS.md # MF YAML compiler (validate, compile, loader)
```

---

## 项目概述

MiQroForge 2.0 (MF) 是一个**量子 + AI 科学计算平台**：以规范化节点为核心资产，以 Argo Workflow 为执行引擎，以 LLM Agent 驱动工作流编排。

---

## 设计哲学

MiQroForge 的节点本质上是**牺牲了灵活性的可组装 Skills**——通过严格的 I/O Schema、语义类型、资源声明来换取科学计算必需的可复现性、类型安全和审计追踪能力。

我们不是在构建一个越来越重的节点管理系统，而是在构建一个**渐进式放松约束**的 AI-native 科学计算平台。

---

## 当前开发阶段

| Phase | 名称 | 状态 |
|-------|------|------|
| Phase 1 | 基础设施与规范节点建库 | ✅ 完成 |
| Phase 2 | 智能工作流编排 | ✅ M4 完成（里程碑见 `agents/AGENTS.md`） |
| Phase 3 | 全面智能化 | 🔲 未开始 |

---

## 开发准则

1. 第一性原理，在审查时从原始逻辑出发。已完成的代码可能是考虑不周，符合总体设计和逻辑更重要。
2. 开发阶段，考虑主要逻辑，不加fallback，异常直接抛出。
3. 合理建议，对看到的异常地方可以谈谈想法。
4. 不清楚直接问，不要假设某些设计考虑。

---

## 架构分层

| Layer | 名称 | 技术 | 职责 |
|-------|------|------|------|
| L4 | 前端 | React Flow + Chat UI | 可视化编辑 + 对话交互 |
| L3 | API | FastAPI + WebSocket | 路由、认证、实时通信 |
| L2 | Agent | LangGraph | 多 Agent 状态图、工具调用 |
| L1 | 基础设施 | LLM Gateway, Argo Events | LLM 代理、事件驱动 |
| L0 | 执行引擎 | K8s + Argo Workflow | 节点容器运行、DAG 调度 |

---

## 子 AGENTS.md 索引

| 文件 | 涵盖领域 | 典型任务 | 何时读 |
|------|----------|----------|--------|
| `nodes/AGENTS.md` | 节点分类体系、临时/prefab 节点、sweep 限制 | 添加新节点类型、理解生成式节点 | 涉及节点类型判断 |
| `nodes/schemas/AGENTS.md` | Pydantic Schema、IO 类型、资源定义 | 修改 NodeSpec、添加端口类型 | 涉及 Schema 变更 |
| `nodes/base_images/AGENTS.md` | BYOB 镜像、MPI、Workspace PVC | 构建镜像、配置 MPI 并行 | 涉及容器化或文件系统 |
| `agents/AGENTS.md` | LangGraph Agent 层、Phase 2 里程碑、RAG | 开发/修改 Agent、理解编排流程 | 涉及 Agent 代码 |
| `api/AGENTS.md` | FastAPI 后端、路由、服务层 | 添加 API 端点、修改路由 | 涉及 API 变更 |
| `frontend/src/AGENTS.md` | React 画布、Zustand stores、组件 | 修改前端 UI、状态管理 | 涉及前端代码 |
| `node_index/AGENTS.md` | 节点扫描器、搜索、CLI | 修改索引格式、搜索权重 | 涉及索引逻辑 |
| `vectorstore/AGENTS.md` | ChromaDB 向量检索、RAG | 重建索引、修改检索策略 | 涉及向量检索 |
| `workflows/pipeline/AGENTS.md` | MF YAML 编译器、校验器 | 修改编译逻辑、校验规则 | 涉及编译/校验 |
| `nodes/quantum/AGENTS.md` | 量子节点、AWS Braket 真机执行、凭证注入 | 编写量子节点、添加 QPU 设备、轮换 AWS 凭证 | 涉及量子节点或 Braket 硬件 |
| `infrastructure/k8s/README.md` | K8s 部署清单、RBAC、AWS Braket 凭证注入设计 | 部署/修改 K8s 资源、配置 Braket 凭证 Secret | 涉及 K8s 基础设施或 AWS 凭证 |

---

## 技术栈速查

| 层次 | 技术 |
|------|------|
| 容器/调度 | Docker, Kubernetes, Argo Workflow |
| Schema | Python + Pydantic v2 |
| AI 编排 | LangGraph + LangChain |
| LLM | OpenAI GPT-4o / DeepSeek-Coder |
| 向量检索 | ChromaDB (dev) / FAISS (prod) |
| API | FastAPI + WebSocket |
| 前端 | React + Vite + @xyflow/react + Zustand + Tailwind CSS v3 |

---

## 未来阶段规划（仅供了解，当前不开发）

### Phase 3 — 全面智能化
- **Main Agent**：长生命周期项目级 Agent，统一调度各子 Agent
- **审查与人机协作**：Review Agent、Argo Suspend/Resume 审批门禁
- **自动 Debug**：Argo Events + Webhook 触发 Debug Agent

