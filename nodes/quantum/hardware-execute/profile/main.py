#!/usr/bin/env python3
"""hardware-execute — AWS Braket circuit execution.

Reads an OpenQASM 3.0 circuit (MF_OQ3_FILE) and the onboard parameters
MF_BACKEND / MF_N_SHOTS from the environment, executes it on the selected
Braket backend (local simulator, SV1 cloud simulator, or a named QPU), and
writes measurement counts (JSON) plus a task_succeeded gate.

Each QPU backend name maps to a globally-unique device ARN; the AWS region is
derived from the ARN's 4th colon-field and exported before the Braket session
is created, overriding the credential Secret's default region (QPUs are
region-bound and the SV1 results bucket lives in us-east-1).
"""
import json
import os
import sys
import time

# Named Braket QPU devices: backend enum value -> globally-unique device ARN.
# The region is encoded in the ARN's 4th colon-field; add a new device by adding
# a line here (and the matching enum value in nodespec.yaml).
DEVICE_ARNS = {
    "rigetti-cepheus": "arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1-108Q",
    "iqm-emerald":     "arn:aws:braket:eu-north-1::device/qpu/iqm/Emerald",
    "ionq-forte":      "arn:aws:braket:us-east-1::device/qpu/ionq/Forte-Enterprise-1",
    "aqt-ibex":        "arn:aws:braket:eu-north-1::device/qpu/aqt/Ibex-Q1",
    "iqm-garnet":      "arn:aws:braket:eu-north-1::device/qpu/iqm/Garnet",
}
SV1_ARN = "arn:aws:braket:::device/quantum-simulator/amazon/sv1"

backend = os.environ["MF_BACKEND"]
n_shots = int(os.environ["MF_N_SHOTS"])
oq3_file = os.environ["MF_OQ3_FILE"]
output_dir = os.environ["MF_OUTPUT_DIR"]

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
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    print(f"[hardware-execute] Submitting to SV1 ({SV1_ARN}) …", file=sys.stderr)
    task = AwsDevice(SV1_ARN).run(circuit, shots=n_shots)
    print(f"[hardware-execute] Task ARN: {task.id}", file=sys.stderr)
    while task.state() not in ("COMPLETED", "FAILED", "CANCELLED"):
        time.sleep(2)
    if task.state() != "COMPLETED":
        print(f"[hardware-execute][ERROR] SV1 task {task.state()}", file=sys.stderr)
        sys.exit(1)
    result = task.result()

else:  # named QPU
    from braket.aws import AwsDevice
    if backend not in DEVICE_ARNS:
        print(f"[hardware-execute][ERROR] Unknown backend '{backend}'", file=sys.stderr)
        sys.exit(1)
    device_arn = DEVICE_ARNS[backend]
    # Region is the 4th colon-field of the ARN; export it before the Braket
    # session is created so boto3 targets the device's region.
    os.environ["AWS_DEFAULT_REGION"] = device_arn.split(":")[3]
    print(f"[hardware-execute] Submitting to QPU {backend}: {device_arn} "
          f"(region {os.environ['AWS_DEFAULT_REGION']}) …", file=sys.stderr)
    task = AwsDevice(device_arn).run(circuit, shots=n_shots)
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
