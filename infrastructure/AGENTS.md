# Infrastructure

**Hierarchy:** `infrastructure/` — Kubernetes and Argo deployment configuration for MF2.

---

## STRUCTURE

```
infrastructure/
├── AGENTS.md              # ★ This file (index)
├── k8s/
│   ├── README.md          # K8s manifests overview (namespaces, RBAC, quick-apply)
│   └── aws-braket-creds-injection.md  # Braket credential injection design (authoritative)
├── argo/                  # Argo Workflow server deployment
└── registry/              # Container registry configuration
```

---

## 速查

| 你想做什么 | 去哪里 |
|-----------|-------|
| 理解 K8s 命名空间 / RBAC / PVC | `k8s/README.md` |
| 理解 AWS Braket 凭证如何注入节点 | `k8s/aws-braket-creds-injection.md` |
| 创建 / 轮换 AWS 凭证 | `nodes/quantum/AGENTS.md` §"如何添加 / 轮换 AWS 凭证" |
| 部署基础设施到新集群 | `scripts/setup_infra.sh` |

---

## AWS Braket 凭证注入（摘要）

凭证机制由两个组件配合工作：

1. **K8s Secret**（一次性 admin 操作）：在 `miqroforge-dev` namespace 创建
   `aws-braket-creds` Secret，包含 `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、
   `AWS_DEFAULT_REGION`（大写 key，boto3 标准）。

2. **编译器 envFrom 注入**：`hardware-execute` 节点的 `nodespec.yaml` 声明
   `execution.secret_refs: [aws-braket-creds]`。编译器自动生成
   `envFrom.secretRef(optional: true)`，kubelet 在 pod 准入时解析 Secret 并注入环境变量。

完整设计决策和废弃的 PVC staging 方案历史见 `k8s/aws-braket-creds-injection.md`。
