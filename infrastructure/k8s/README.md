# MiQroForge 2.0 — Kubernetes Manifests

K8s resources for MF2 platform runtime. Two namespaces are used:
- **`miqroforge-v2`** — production/staging namespace (workflow execution)
- **`miqroforge-dev`** — development namespace (Phase 2 dev + HIL hardware)

---

## Manifests

| File | Kind | Namespace | Purpose |
|------|------|-----------|---------|
| `namespace.yaml` | Namespace | `miqroforge-v2` | Production namespace |
| `rbac.yaml` | SA + Role + Binding | `miqroforge-v2` | Production RBAC for Argo workflows |
| `rbac-dev.yaml` | SA + Role + Binding | `miqroforge-dev` | Dev RBAC (includes secrets access for credential injection) |
| `workspace.yaml` | PV + PVC | `__MF_NAMESPACE__` | Workspace persistent storage (hostPath) |
| `aws-braket-secret.example.yaml` | Secret | `miqroforge-dev` | AWS Braket credentials template (placeholder keys) |

## Docs

| File | Purpose |
|------|---------|
| `aws-braket-creds-injection.md` | Decision note: workspace-PVC fallback for N4 Braket credentials |

---

## Quick Apply

### Development namespace

```bash
# Ensure namespace exists (rbac-dev.yaml creates it implicitly via SA/role resources)
kubectl apply -f infrastructure/k8s/rbac-dev.yaml

# Workspace PVC (replace __MF_NAMESPACE__ with miqroforge-dev)
MF_NS=miqroforge-dev
sed "s|__MF_PROJECT_ROOT__|$(pwd)|g; s|__MF_NAMESPACE__|$MF_NS|g" \
    infrastructure/k8s/workspace.yaml | kubectl apply -f -

# AWS Braket credentials (fill real values first)
cp infrastructure/k8s/aws-braket-secret.example.yaml infrastructure/k8s/aws-braket-secret.yaml
# Edit aws-braket-secret.yaml with real keys
kubectl apply -f infrastructure/k8s/aws-braket-secret.yaml
```

### Production namespace

```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/rbac.yaml
MF_NS=miqroforge-v2
sed "s|__MF_PROJECT_ROOT__|$(pwd)|g; s|__MF_NAMESPACE__|$MF_NS|g" \
    infrastructure/k8s/workspace.yaml | kubectl apply -f -
```

---

## Guard: Confirm Target Namespace

Before applying any manifest, verify `ARGO_NAMESPACE` matches your intent:

```bash
grep ARGO_NAMESPACE .env | cut -d= -f2
```

Manifests that use `__MF_NAMESPACE__` must be processed through `sed` (see above).
Manifests with hardcoded namespace (`miqroforge-dev`) should only be applied if
`ARGO_NAMESPACE=miqroforge-dev`.

---

## Pre-requisites

- `kubectl` configured with cluster access
- `ARGO_NAMESPACE` set in `.env` (used by compiler for PVC name resolution)
- Docker daemon running (for `setup_infra.sh` automated deployment)
- For Braket: AWS IAM user with Braket + S3 permissions (account 533612071261)
