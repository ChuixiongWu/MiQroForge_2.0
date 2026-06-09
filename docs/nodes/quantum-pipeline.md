# Quantum Pipeline — End-to-End Run Guide

> **Pipeline:** quantum-ewf-qsci | **Molecule:** H₂ / STO-3G | **Status:** ✅ Local backend passes

---

## Overview

The `quantum-ewf-qsci` pipeline performs an end-to-end quantum computing simulation of
molecular electronic structure:

```
geom-input → chem-prep → ewf-decompose → qsci-prep → hardware-execute → qsci-assemble
```

| Step | Node | Description | Tool |
|------|------|-------------|------|
| N0 | `geom-input` | Supply H₂ XYZ geometry | inline |
| N1 | `chem-prep` | RHF mean-field calculation | PySCF |
| N2 | `ewf-decompose` | EWF single-fragment embedding | Vayesta |
| N3 | `qsci-prep` | JW mapping + LUCJ ansatz | OpenFermion, PennyLane |
| N4 | `hardware-execute` | Circuit execution on backend | Braket (local/SV1/QPU) |
| N5 | `qsci-assemble` | QSCI subspace diagonalisation + FCI benchmark | PySCF FCI |

---

## Acceptance Criteria

From `qsci-assemble` nodespec (`energy_validated` quality gate):

| Criterion | Value |
|-----------|-------|
| `total_energy` produced | Finite float |
| `\|E_qsci - E_fci\|` | < 1e-3 Ha (1 mHa) |
| `energy_validated` | `True` |
| `qsci_report` present | JSON with `E_qsci`, `E_fci`, `delta_Ha` |

---

## Path 1: Local Backend (Python-only, free)

This runs the QSCI pipeline entirely in Python without Docker or Argo,
using `openfermionpyscf` for Hamiltonian construction and synthetic
measurement counts from the FCI wavefunction (simulating infinite-shot hardware).

### Requirements

- Python >= 3.10
- `pyscf>=2.8`, `openfermion>=1.7`, `openfermionpyscf`, `scipy`, `numpy`, `h5py`

### Run

```bash
cd /home/quantum/MF2_dev
python3 -m pytest tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal -v
```

### Expected Output

```
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_energy_validated PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_total_energy_produced PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_delta_below_tolerance PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_subspace_dimension PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_qubit_count PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_fci_not_skipped PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_report_structure PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_e_mf_negative PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_energy_conservation_assembly PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_reproducibility PASSED
tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal::test_hf_config_in_subspace PASSED

============================== 11 passed in ~1.3s ==============================
```

### Expected Energy Values

| Quantity | Value (Ha) |
|----------|------------|
| `E_qsci` (total) | -1.1372701747 |
| `E_fci` (reference) | -1.1372701747 |
| `\|delta\|` | ≤ 1e-15 (effectively exact) |
| `e_mf` (HF) | -1.1166843871 |
| Correlation captured | -0.020586 Ha |

---

## Path 2: Argo Pipeline (Local Backend)

Runs the full pipeline through Argo with `hardware-execute.backend=local`
(Braket LocalSimulator — no AWS credentials needed).

### Requirements

- Argo Workflow >= 3.0
- Kubernetes cluster
- Docker images: `classical-chem-0.1`, `quantum-exec-0.1`

### Run

```bash
# 1. Validate
bash scripts/mf2.sh validate workflows/examples/h2-quantum-pipeline-mf.yaml

# 2. Compile to Argo YAML
bash scripts/mf2.sh compile workflows/examples/h2-quantum-pipeline-mf.yaml

# 3. Submit + follow logs
bash scripts/mf2.sh run workflows/examples/h2-quantum-pipeline-mf.yaml

# 4. Inspect results
bash scripts/mf2.sh logs h2-quantum-pipeline
```

### Expected Output Parameters (qsci-assemble)

| Parameter | Expected |
|-----------|----------|
| `total_energy` | ~-1.0 to -1.2 Ha |
| `energy_validated` | `true` |
| `qsci_report.E_qsci` | Close to `E_fci` |
| `qsci_report.fci_skipped` | `false` |

---

## Path 3: Argo Pipeline (SV1 Backend)

Runs the pipeline with AWS Braket SV1 cloud simulator.
**ONE RUN MAXIMUM — cost constraint.**

### Prerequisites

1. **AWS Braket credentials** — admin creates the `aws-braket-creds` Secret once
   in `miqroforge-dev` (see `infrastructure/k8s/aws-braket-creds-injection.md`).
   The compiler reads `secret_refs` from the NodeSpec and injects the Secret as
   `envFrom.secretRef` into the pod. No `.aws/` file staging or workspace PVC
   manipulation is needed.

   ```bash
   kubectl create secret generic aws-braket-creds \
     --namespace=miqroforge-dev \
     --from-literal=AWS_ACCESS_KEY_ID=... \
     --from-literal=AWS_SECRET_ACCESS_KEY=... \
     --from-literal=AWS_DEFAULT_REGION=us-east-1
   ```

2. S3 bucket `amazon-braket-mqe-533612071261` in us-east-1

> **Region precedence:** For Braket SV1/QPU backends, `run.sh` exports
> `AWS_DEFAULT_REGION=us-east-1`, which overrides whatever value the Secret
> contains. The Secret's `AWS_DEFAULT_REGION` key serves as a fallback for
> non-Braket AWS SDK calls and has no effect on Braket execution.

### Modify workflow for SV1

Edit `workflows/examples/h2-quantum-pipeline-mf.yaml`:
```yaml
  - id: hardware-execute
    nodespec_path: nodes/quantum/hardware-execute/nodespec.yaml
    onboard_params:
      backend: sv1        # ← change from 'local' to 'sv1'
      n_shots: 5000
```

### Run

```bash
MF_RUN_SV1=1 python3 -m pytest tests/integration/test_quantum_pipeline.py::TestQuantumPipelineArgoSV1 -v
```

Or manually:
```bash
bash scripts/mf2.sh run workflows/examples/h2-quantum-pipeline-mf.yaml
```

---

## Integration Test

```bash
# Local pipeline (always runs, no deps beyond Python packages)
pytest tests/integration/test_quantum_pipeline.py::TestQuantumPipelineLocal -v

# SV1 pipeline (requires MF_RUN_SV1=1)
MF_RUN_SV1=1 pytest tests/integration/test_quantum_pipeline.py::TestQuantumPipelineArgoSV1 -v
```

---

## File Index

| File | Purpose |
|------|---------|
| `workflows/examples/h2-quantum-pipeline-mf.yaml` | MF YAML workflow definition |
| `tests/integration/test_quantum_pipeline.py` | Integration test (local + SV1) |
| `nodes/quantum/chem-prep/` | RHF mean-field preparation node |
| `nodes/quantum/ewf-decompose/` | Vayesta EWF embedding node |
| `nodes/quantum/qsci-prep/` | JW mapping + LUCJ ansatz node |
| `nodes/quantum/hardware-execute/` | Braket circuit execution node |
| `nodes/quantum/qsci-assemble/` | QSCI assembly + FCI benchmark node |
| `nodes/quantum/_reference/qsci_reference.py` | QSCI algorithm reference |
| `nodes/quantum/_reference/cluster_contract.py` | Cluster Hamiltonian HDF5 contract |
