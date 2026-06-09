#!/usr/bin/env bash
# hardware-execute/profile/run.sh — AWS Braket circuit execution
set -euo pipefail
source /mf/profile/mf2_init.sh

mf_banner "hardware-execute" "AWS Braket circuit execution"

# ── Read OQ3 circuit from stream input ────────────────────────────────────────
OQ3_FILE="${INPUT_DIR}/ansatz_circuit"
if [[ ! -f "$OQ3_FILE" ]]; then
    echo "[hardware-execute][ERROR] Stream input 'ansatz_circuit' not found at ${OQ3_FILE}" >&2
    exit 1
fi
echo "[hardware-execute] Loaded OQ3 circuit: $(wc -c < "$OQ3_FILE") bytes"

# ── Export onboard params for Python ──────────────────────────────────────────
export MF_BACKEND="$backend"
export MF_N_SHOTS="$n_shots"
export MF_DEVICE_ARN="$device_arn"
export MF_OQ3_FILE="$OQ3_FILE"
export MF_OUTPUT_DIR="$OUTPUT_DIR"

echo "[hardware-execute] Backend=${MF_BACKEND}  Shots=${MF_N_SHOTS}"

# ── Export AWS_DEFAULT_REGION for non-local backends ──────────────────────────
if [[ "$MF_BACKEND" == "local" ]]; then
    :
elif [[ "$MF_BACKEND" == "sv1" ]]; then
    export AWS_DEFAULT_REGION="us-east-1"
else
    region="$(cut -d: -f4 <<< "$MF_DEVICE_ARN")"
    if [[ -z "$region" ]]; then
        echo "[hardware-execute][ERROR] device_arn not set or invalid" >&2
        exit 1
    fi
    export AWS_DEFAULT_REGION="$region"
fi
echo "[hardware-execute] AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-N/A}"

# ── Execute Braket (Python inline) ────────────────────────────────────────────
python3 << 'PYEOF'
import json, os, sys, time

backend   = os.environ["MF_BACKEND"]
n_shots   = int(os.environ["MF_N_SHOTS"])
oq3_file  = os.environ["MF_OQ3_FILE"]
output_dir = os.environ["MF_OUTPUT_DIR"]

device_arn = os.environ.get("MF_DEVICE_ARN", "")

# ── Read OpenQASM 3.0 circuit ──────────────────────────────────────────────
with open(oq3_file) as f:
    oq3_source = f.read()

# ── Parse circuit ──────────────────────────────────────────────────────────
from braket.circuits import Circuit
circuit = Circuit.from_ir(source=oq3_source)
n_qubits = circuit.qubit_count
print(f"[hardware-execute] Parsed circuit: {n_qubits} qubits", file=sys.stderr)

# ── Execute on chosen backend ──────────────────────────────────────────────
if backend == "local":
    from braket.devices import LocalSimulator
    print("[hardware-execute] Running on LocalSimulator …", file=sys.stderr)
    result = LocalSimulator().run(circuit, shots=n_shots).result()

elif backend == "sv1":
    from braket.aws import AwsDevice
    sv1_arn = "arn:aws:braket:::device/quantum-simulator/amazon/sv1"
    print(f"[hardware-execute] Submitting to SV1 ({sv1_arn}) …", file=sys.stderr)
    task = AwsDevice(sv1_arn).run(
        circuit, shots=n_shots,
    )
    print(f"[hardware-execute] Task ARN: {task.id}", file=sys.stderr)
    while task.state() not in ("COMPLETED", "FAILED", "CANCELLED"):
        time.sleep(2)
    if task.state() != "COMPLETED":
        print(f"[hardware-execute][ERROR] SV1 task {task.state()}", file=sys.stderr)
        sys.exit(1)
    result = task.result()

else:  # qpu
    from braket.aws import AwsDevice
    if not device_arn:
        print("[hardware-execute][ERROR] device_arn required for qpu backend", file=sys.stderr)
        sys.exit(1)
    print(f"[hardware-execute] Submitting to QPU: {device_arn} …", file=sys.stderr)
    task = AwsDevice(device_arn).run(
        circuit, shots=n_shots,
    )
    print(f"[hardware-execute] Task ARN: {task.id}", file=sys.stderr)
    while task.state() not in ("COMPLETED", "FAILED", "CANCELLED"):
        time.sleep(2)
    if task.state() != "COMPLETED":
        print(f"[hardware-execute][ERROR] QPU task {task.state()}", file=sys.stderr)
        sys.exit(1)
    result = task.result()

# ── Extract measurement counts ─────────────────────────────────────────────
counts = dict(result.measurement_counts)
# Braket returns either int keys (AWS backends) or binary-str keys (LocalSimulator).
# For int keys, zero-pad to binary strings; string keys are already binary repr.
if counts and not isinstance(next(iter(counts)), str):
    counts = {format(k, f"0{n_qubits}b"): v for k, v in counts.items()}

os.makedirs(output_dir, exist_ok=True)
with open(f"{output_dir}/measurement_counts", "w") as f:
    json.dump(counts, f)

with open(f"{output_dir}/task_succeeded", "w") as f:
    f.write("true\n")

print(
    f"[hardware-execute] Done. {len(counts)} outcomes, "
    f"{sum(counts.values())} total shots.",
    file=sys.stderr,
)
PYEOF

echo "[hardware-execute] Complete."
