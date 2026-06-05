# AWS Braket Credential Injection — Decision Note

> **Date:** 2026-06-01 | **Node:** N4 (hardware-execute) | **Wave:** 1  
> **Context:** quantum-ewf-qsci-pipeline — AWS Braket hardware execution node needs
> AWS credentials at runtime to submit circuits and retrieve results.

---

## 1. Investigation: Compiler Secret/Env Injection Support

The MF YAML compiler (`workflows/pipeline/compiler.py`) was audited for `envFrom`,
`secretKeyRef`, or any K8s secret injection mechanism. **Result: not supported.**

The compiler generates Argo templates with the following env patterns:

| Template type | Env mechanism | Source | Supports secrets? |
|---------------|---------------|--------|-------------------|
| `compute` (container) | `env: [{name, value}]` | `exec_cfg.environment` (static) | No |
| `lightweight` (script) | `env: [{name, value}]` | hardcoded + input params | No |
| `lightweight` (profile container) | `env: [{name, value}]` | `exec_cfg.environment` (static) | No |
| `ephemeral` (script) | `env: [{name, value}]` | hardcoded (`MF_API_URL` etc.) | No |
| `prefab` (script) | `env: [{name, value}]` | hardcoded (`MF_API_URL` etc.) | No |

**No template emits `envFrom` or `valueFrom.secretKeyRef`.** The `exec_cfg.environment`
field (`nodes/schemas/execution.py`) is `dict[str, str]` — plaintext values baked into
the compiled Argo YAML, unsuitable for secrets.

### What would need to change (Wave 2+)

To support K8s-native secret injection, the compiler would need:

1. **Schema change:** Add `Credentials` model to `nodes/schemas/` or
   `workflows/pipeline/models.py`, referencing a named K8s secret + keys to expose
   as env vars.

2. **Compiler change:** In `_build_compute_template()`, `_build_lightweight_script_template()`,
   `_build_ephemeral_template()`, and `_build_prefab_template()`, add optional
   `envFrom: [{secretRef: {name: ...}}]` when credentials are declared.

3. **MF YAML model change:** Allow nodes to declare a `credentials` block referencing
   a pre-created K8s secret (not inline values).

This is deferred to a future wave. For Wave 1, the workspace-PVC fallback is used.

---

## 2. Decision: Workspace-PVC Fallback (Wave 1)

**The N4 hardware-execute node reads AWS credentials from the Workspace PVC at runtime.**

### Mechanism

```
┌──────────────────────────────────────────────────────────┐
│  K8s Cluster (namespace: miqroforge-dev)                 │
│                                                          │
│  ┌─────────────┐     ┌──────────────────────────────┐   │
│  │  K8s Secret │     │  N4 Pod (hardware-execute)   │   │
│  │             │     │                              │   │
│  │ aws-braket- │  ┌─▶│  /mf/workspace/              │   │
│  │ creds       │  │  │    └─ .aws/                  │   │
│  │ (opaque)    │  │  │       ├─ credentials  ◀──┐   │   │
│  └─────────────┘  │  │       └─ config        │   │   │
│        │          │  └─────────────────────────│───┘   │
│        │          │                            │       │
│        ▼          │  ┌─────────────────────────│───┐   │
│  ┌─────────────┐  │  │  Workspace PVC         │   │   │
│  │ initContainer│──┘  │  (hostPath:            │   │   │
│  │ or manual   │     │   userdata/workspace/)  │   │   │
│  │ staging     │     │                         │   │   │
│  └─────────────┘     └─────────────────────────┘───┘   │
└──────────────────────────────────────────────────────────┘
```

### How it works

1. **K8s Secret exists** (`aws-braket-creds` in `miqroforge-dev`) but is NOT injected
   into pods via the compiler. It serves as the canonical source of truth for credential
   rotation and audit.

2. **Workspace PVC staging** — credentials are staged into the Workspace PVC
   (`/mf/workspace/.aws/`) once, either:
   - Manually via `kubectl exec` into any pod with workspace mounted, or
   - Via the MF API upload endpoint (`POST /projects/{pid}/workspace/`), or
   - Via a one-shot `initContainer` in the N4 pod spec (manually added to compiled Argo YAML post-compilation for Wave 1).

3. **Runtime read** — the N4 `run.sh` script reads credentials from
   `/mf/workspace/.aws/credentials` and sets `AWS_SHARED_CREDENTIALS_FILE`
   before invoking Braket SDK calls:

   ```bash
   export AWS_SHARED_CREDENTIALS_FILE=/mf/workspace/.aws/credentials
   export AWS_CONFIG_FILE=/mf/workspace/.aws/config
   export AWS_DEFAULT_REGION=us-east-1
   ```

### Credential staging command (manual)

```bash
# From the cluster admin machine:
kubectl create secret generic aws-braket-creds \
  --namespace=miqroforge-dev \
  --from-literal=AWS_ACCESS_KEY_ID=... \
  --from-literal=AWS_SECRET_ACCESS_KEY=... \
  --from-literal=AWS_DEFAULT_REGION=us-east-1

# Stage into workspace PVC (one-time). Use a temporary one-shot pod since no
# persistent pod with workspace mount exists. The pod reads credentials from the
# K8s secret and writes both .aws/credentials and .aws/config, then exits.
kubectl run mf-cred-stage --namespace=miqroforge-dev --restart=Never \
  --image=busybox --overrides='
{
  "spec": {
    "volumes": [{"name":"ws","persistentVolumeClaim":{"claimName":"miqroforge-dev"}}],
    "containers": [{
      "name":"stager",
      "image":"busybox",
      "command":["sh","-c"],
      "args":["mkdir -p /mf/workspace/.aws && echo \"[default]\" > /mf/workspace/.aws/credentials && echo \"aws_access_key_id = ${AWS_ACCESS_KEY_ID}\" >> /mf/workspace/.aws/credentials && echo \"aws_secret_access_key = ${AWS_SECRET_ACCESS_KEY}\" >> /mf/workspace/.aws/credentials && echo \"[default]\" > /mf/workspace/.aws/config && echo \"region = us-east-1\" >> /mf/workspace/.aws/config && sleep 5"],
      "volumeMounts":[{"name":"ws","mountPath":"/mf/workspace","subPath":"proj_proj_04636b4ebc"}],
      "env":[
        {"name":"AWS_ACCESS_KEY_ID","valueFrom":{"secretKeyRef":{"name":"aws-braket-creds","key":"AWS_ACCESS_KEY_ID"}}},
        {"name":"AWS_SECRET_ACCESS_KEY","valueFrom":{"secretKeyRef":{"name":"aws-braket-creds","key":"AWS_SECRET_ACCESS_KEY"}}}
      ]
    }]
  }
}'
kubectl delete pod -n miqroforge-dev mf-cred-stage --ignore-not-found
```

> **Region priority:** `run.sh` exports `AWS_DEFAULT_REGION=us-east-1` (see line 94 above).
> The AWS SDK resolves region with env var priority over file config (`AWS_DEFAULT_REGION`
> wins over `.aws/config`), so the config file serves as a fallback for any non-Braket
> SDK calls within the container.

### Tradeoffs

| Aspect | Workspace-PVC fallback | K8s native envFrom (future) |
|--------|------------------------|----------------------------|
| Compiler changes | None (Wave 1) | Schema + compiler (Wave 2+) |
| Security | Credentials visible to any pod with workspace mount | Scoped to nodes that declare credentials |
| Rotation | Re-stage in PVC | Update Secret + restart pods |
| Audit | Manual | K8s audit log on secret read |
| Effort (Wave 1) | Minimal — one manual staging | Significant — multi-file compiler changes |

---

## 3. K8s Secret Purpose (Wave 1)

Even without compiler integration, the `aws-braket-creds` Secret serves as:

- **Single source of truth** for credential values
- **Rotation target** — update the Secret, re-stage to workspace
- **Future-ready** — when compiler gains `envFrom` support, pods will reference
  this exact Secret name (`aws-braket-creds`)

---

## 4. Future: Wave 2+ Compiler Integration

When compiler gains secret injection support, the N4 node can declare:

```yaml
# In MF YAML (conceptual, not implemented):
nodes:
  - id: hardware-execute
    credentials:
      - secret_name: aws-braket-creds
        keys:
          - AWS_ACCESS_KEY_ID
          - AWS_SECRET_ACCESS_KEY
          - AWS_DEFAULT_REGION
```

Compiler emits:
```yaml
container:
  envFrom:
    - secretRef:
        name: aws-braket-creds
```

At that point, workspace staging is no longer needed and credentials are
scoped to the specific node's pod.

---

## 5. Credential Source

Per `wcx_data/hardware_explore/aws_braket_setup.md` (2026-05-27):

| Field | Value |
|-------|-------|
| AWS Account | 533612071261 |
| IAM User | mqe-quantum-dev |
| Region | us-east-1 |
| S3 Bucket | amazon-braket-mqe-533612071261 |
| Auth file | `~/.aws/credentials` (local dev machine) |
| SDK | `amazon-braket-sdk`, `amazon-braket-pennylane-plugin` |

---

## References

- `infrastructure/k8s/aws-braket-secret.example.yaml` — Secret template (placeholders)
- `infrastructure/k8s/rbac-dev.yaml` — `miqroforge-dev` namespace + ServiceAccount
- `infrastructure/k8s/workspace.yaml` — PVC definition (`/mf/workspace`)
- `workflows/pipeline/compiler.py` — Compiler (audited for env injection)
- `wcx_data/hardware_explore/aws_braket_setup.md` — Braket setup record
