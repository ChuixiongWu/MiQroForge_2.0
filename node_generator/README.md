# node_generator/ — Phase 3 占位

> **当前阶段（Phase 1-2）不开发此目录，请勿在此处添加业务代码。**

## Phase 3 规划功能

- **NodeGen Agent**：接受自然语言描述，自动生成节点 Python 代码 + Dockerfile
- **E2B 沙箱**：在安全隔离环境中测试 Agent 生成的代码，确认无副作用后注册到节点库
- **自动 Debug Agent**：通过 Argo Events 捕获节点运行失败事件，分析日志并推送修复建议

## 参考文档

- 详细设计见 `docs/architecture/phase3.md`（待填充）
- Argo Events 文档：https://argoproj.github.io/argo-events/
- E2B 文档：https://e2b.dev/docs
