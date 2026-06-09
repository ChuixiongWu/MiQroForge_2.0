# quantum-exec — 量子计算执行基础镜像

> 构建方法见 [../README.md](../README.md)。本文件仅说明 quantum-exec 特异性内容。

## 特异性：量子计算全栈

- **OpenFermion**：量子化学 → 量子比特映射（Jordan-Wigner / Bravyi-Kitaev 变换）
- **PennyLane 0.42.3**：量子机器学习框架，支持自动微分和混合量子-经典模型
- **Amazon Braket SDK 1.110.1**：AWS 量子计算服务 SDK（本地模拟器 + 量子硬件后端）
- **amazon-braket-pennylane-plugin 1.33.7**：PennyLane ↔ Braket 桥接，将 PennyLane 电路映射到 Braket 模拟器/硬件

## 与 cirq 镜像的区别

| 镜像 | 量子框架 | 用途 |
|------|----------|------|
| `cirq:1` | Cirq + qsim | 电路构建、高精度模拟、噪声建模 |
| `quantum-exec:0.1` | PennyLane + Braket + OpenFermion | VQE、QAOA、量子机器学习、混合算法 |

## 版本锁定

| 包 | 版本 | 原因 |
|----|------|------|
| pennylane | 0.42.3 | 稳定 API，与 braket 插件兼容 |
| amazon-braket-sdk | 1.110.1 | AWS 后端支持 |
| amazon-braket-pennylane-plugin | 1.33.7 | PennyLane ↔ Braket 桥接 |

## 不包含

- **pyscf / vayesta**：经典量子化学（使用现有化学节点如 ORCA/PSi4）
- **AWS 凭证 / region**：运行时由环境变量注入，不写入镜像

## 部署

镜像仅导入本地 k3s containerd，不推送到 Harbor：

```bash
bash nodes/base_images/quantum-exec/build.sh
```
