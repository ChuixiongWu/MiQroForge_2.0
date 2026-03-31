"""orca-freq post-processing: parse thermochemistry data from ORCA output.

Temperature is passed via the TEMPERATURE_VAL environment variable (set by run.sh).
"""
import os
import re
import json

workdir = "/mf/workdir"
output_dir = "/mf/output"
log_file = workdir + "/output.log"

temperature_str = os.environ.get("TEMPERATURE_VAL", "298.15")

with open(log_file) as f:
    content = f.read()


def extract_float(pattern, content, default=None):
    m = re.search(pattern, content)
    if m:
        try:
            return float(m.group(1))
        except (ValueError, IndexError):
            return default
    return default


# 提取热力学量
zpe = extract_float(r"Zero point energy\s+\.\.\.\s+([-\d.]+)\s*Eh", content)
total_enthalpy = extract_float(r"Total enthalpy\s+\.\.\.\s+([-\d.]+)\s*Eh", content)
final_gibbs = extract_float(r"Final Gibbs free energy\s+\.\.\.\s+([-\d.]+)\s*Eh", content)
entropy = extract_float(r"Total entropy correction\s+\.\.\.\s+([-\d.]+)\s*Eh", content)
total_energy = extract_float(r"FINAL SINGLE POINT ENERGY\s+([-\d.]+)", content)

# 提取频率
freq_pattern = re.compile(r":\s*([-\d.]+)\s+cm\*\*-1")
frequencies = [float(m.group(1)) for m in freq_pattern.finditer(content)]

# 计算虚频数
n_imaginary = sum(1 for f in frequencies if f < 0)
is_true_minimum = (n_imaginary == 0)

print(f"[orca-freq] ZPE={zpe} Ha, Gibbs={final_gibbs} Ha, Enthalpy={total_enthalpy} Ha")
print(f"[orca-freq] N(imaginary)={n_imaginary}, IsMinimum={is_true_minimum}")
print(f"[orca-freq] N(frequencies)={len(frequencies)}")

# 写入热力学数据包
thermo = {
    "zpe_ha": zpe,
    "total_energy_ha": total_energy,
    "enthalpy_ha": total_enthalpy,
    "gibbs_ha": final_gibbs,
    "entropy_ha_per_k": entropy,
    "n_imaginary": n_imaginary,
    "is_true_minimum": is_true_minimum,
    "frequencies_cm1": frequencies[:20],  # 只保存前20个频率
    "temperature_k": float(temperature_str),
}

with open(output_dir + "/thermo_package", "w") as f:
    json.dump(thermo, f, indent=2)

# 写入 ZPE
with open(output_dir + "/zpe", "w") as f:
    f.write(str(zpe or 0.0))

# 写入最小值标志
with open(output_dir + "/is_true_minimum", "w") as f:
    f.write("true" if is_true_minimum else "false")

# 写入新增 stream outputs
with open(output_dir + "/gibbs_free_energy", "w") as f:
    f.write(str(final_gibbs or 0.0))

with open(output_dir + "/enthalpy", "w") as f:
    f.write(str(total_enthalpy or 0.0))

# thermo_report (report_object) — 与 thermo_package 内容相同但语义不同
# thermo_package 是 SDP（供程序消费），thermo_report 是 report（供人/AI 阅读）
with open(output_dir + "/thermo_report", "w") as f:
    json.dump(thermo, f, indent=2)

# On-board 输出
with open(output_dir + "/n_imaginary", "w") as f:
    f.write(str(n_imaginary))
with open(output_dir + "/gibbs_energy", "w") as f:
    f.write(str(final_gibbs or 0.0))
with open(output_dir + "/enthalpy_ha", "w") as f:
    f.write(str(total_enthalpy or 0.0))
