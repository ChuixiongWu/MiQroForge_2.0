# nodes/quantum — Quantum Computing Nodes

> **Phase 3** — Expert hand-written only. No Agent generation.

## Data Contract Strings

The following data contracts define the I/O format for quantum pipeline nodes.
Each contract string uniquely identifies a software ecosystem + data type combination
used in `StreamInputPort` / `StreamOutputPort` of quantum nodes.

```
pyscf/scf-meanfield-h5          — PySCF CHKFILE / MF HDF5: converged mean-field object
vayesta/cluster-hamiltonian-h5  — Vayesta cluster embedding Hamiltonian (HDF5)
openfermion/qubit-hamiltonian-json — OpenFermion QubitHamiltonian serialized as JSON
openqasm/circuit-qasm3          — OpenQASM 3.0 circuit definition
braket/measurement-counts-json  — Amazon Braket measurement outcome counts (JSON)
qsci/qsci-state-h5              — QSCI subspace state / energy data (HDF5)
```

## Pipeline: quantum-ewf-qsci

```
quantum-meanfield-prep ──► quantum-ewf-embedding ──► quantum-qsci-preparation ──► quantum-hardware-sampling ──► quantum-qsci-energy
     │                          │                           │                            │
     │ pyscf/scf-meanfield-h5   │ vayesta/cluster-          │ openfermion/qubit-          │ braket/measurement-
     │                          │ hamiltonian-h5            │ hamiltonian-json            │ counts-json
     ▼                          ▼                           │                            │
  [MF HDF5]               [Cluster Ham HDF5]                │ openqasm/circuit-qasm3     │
                                                             ▼                            │
                                                        [Qubit Ham JSON]                 │
                                                        [QASM 3 Circuit] ────────────────►
                                                                                    [Measurement Counts]
                                                                                          │
                                                                                          ▼
                                                                                    [QSCI Energy]
                                                                                 qsci/qsci-state-h5
```

### Semantic Type → Data Contract Mapping

| Semantic Type | Input Contract(s) | Output Contract(s) | Toolchain |
|---|---|---|---|
| `quantum-meanfield-prep` | — | `pyscf/scf-meanfield-h5` | PySCF |
| `quantum-ewf-embedding` | `pyscf/scf-meanfield-h5` | `vayesta/cluster-hamiltonian-h5` | Vayesta |
| `quantum-qsci-preparation` | `vayesta/cluster-hamiltonian-h5` | `openfermion/qubit-hamiltonian-json`, `openqasm/circuit-qasm3` | OpenFermion, Qiskit |
| `quantum-hardware-sampling` | `openqasm/circuit-qasm3` | `braket/measurement-counts-json` | Amazon Braket |
| `quantum-qsci-energy` | `braket/measurement-counts-json` | `qsci/qsci-state-h5` | QSCI solver |
