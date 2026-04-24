# 软件手册文档

本目录包含 ORCA 和 Gaussian 的官方文档，用于节点开发和合规性审查。

## 目录结构

```
software_manuals/
├── README.md                          # 本文件
├── orca/                             # ORCA 6.0 手册章节
│   ├── dft_methods.md                # DFT 方法
│   ├── geometry_optimization.md      # 几何优化
│   ├── frequency_calculations.md     # 频率分析
│   ├── hf_method.md                  # Hartree-Fock
│   ├── mp2_method.md                 # MP2 微扰理论
│   ├── ccsd_method.md                # CCSD 耦合簇
│   ├── casscf_method.md              # CASSCF
│   └── tddft.md                      # TD-DFT
├── gaussian/                         # Gaussian 16 手册章节
│   ├── gaussian_dft.md               # DFT 方法
│   ├── gaussian_opt.md               # 几何优化
│   ├── gaussian_freq.md              # 频率分析
│   ├── gaussian_hf.md                # Hartree-Fock
│   ├── gaussian_mp.md                # MP 微扰理论
│   ├── gaussian_cc.md                # 耦合簇方法
│   ├── gaussian_cas.md               # CASSCF
│   └── gaussian_td.md                # TD-DFT
├── orca_6.0_manual.tar.gz            # ORCA 完整手册 (PDF 章节)
├── gaussian_16_manual.tar.gz         # Gaussian 完整手册 (网页抓取)
└── node_compliance_report.md         # 节点合规性审查报告
```

## 文档来源

### ORCA 6.0
- **来源**: https://www.faccts.de/docs/orca/6.0/manual/
- **格式**: PDF (1357 页)
- **版本**: ORCA 6.0 (Release 6.0, 2025-06-16)
- **提取方式**: PyMuPDF 提取关键章节

### Gaussian 16
- **来源**: https://gaussian.com/man/
- **格式**: HTML (网页)
- **版本**: Gaussian 16, Revision C.01 (2019-08-22)
- **提取方式**: lynx 抓取并转换为 markdown

## 用途

1. **节点开发参考**: 开发新节点时参考软件支持的功能和参数
2. **合规性审查**: 验证现有节点是否正确反映软件功能
3. **Node Generator Agent**: 为 AI 节点生成提供软件知识库
4. **用户文档**: 帮助用户理解软件功能和限制

## 审查报告

详细的节点合规性审查报告请参见:
- [node_compliance_report.md](node_compliance_report.md)

**关键发现**:
- 节点泛函支持严重不完整 (ORCA: 8/95+, Gaussian: 8/50+)
- 缺少 CCSD(T) 支持
- 缺少范围分离和双杂化泛函

## 使用建议

### 对于节点开发者
1. 在开发新节点前，先查阅对应软件的手册章节
2. 确保节点支持的功能与软件文档一致
3. 添加软件文档中提到的所有相关参数

### 对于 Node Generator Agent
1. 使用这些文档作为训练数据，理解软件功能
2. 生成节点时参考文档中的参数和选项
3. 验证生成的节点是否符合软件本体

### 对于用户
1. 了解软件支持的功能范围
2. 理解节点参数的含义和限制
3. 参考文档选择合适的计算方法

## 更新频率

- **ORCA**: 每个主要版本更新 (如 6.0, 6.1, 7.0)
- **Gaussian**: 每个修订版本更新 (如 C.01, D.01)
- **审查报告**: 每次节点库更新后重新审查

## 注意事项

1. ORCA 手册版本为 6.0，但项目使用 ORCA 6.1 镜像
   - 功能差异应该很小，但建议检查 6.1 的更新日志
2. Gaussian 手册版本为 C.01，项目使用相同版本
3. 文档仅用于参考，实际功能以软件运行结果为准
4. 节点配置可能不完全反映软件的所有功能，需要定期审查

## 相关文件

- 节点配置: `nodes/chemistry/orca/`, `nodes/chemistry/gaussian/`
- 镜像配置: `nodes/base_images/orca/`, `nodes/base_images/gaussian/`
- 节点索引: `nodes/node_index.yaml`
- 节点开发指南: `nodes/schemas/README.md`
