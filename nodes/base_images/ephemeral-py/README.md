# ephemeral-py — 临时节点基础镜像

MiQroForge 临时节点（Agent 运行时生成的脚本）的基础镜像。

## 特异性说明

- 基于 `python:3.11-slim`，预装科学计算库，避免每次运行时 pip install
- 预装库：numpy, scipy, pandas, matplotlib, pyyaml, jinja2, requests, jsonschema
- Agent 通过 `pip_install` 工具可按需安装额外依赖
- 不需要 `/mf/profile` 挂载（脚本由 Agent 内联生成，不走 profile 机制）
