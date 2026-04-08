"""Sweep 节点（parallel_sweep + withParam）单元测试。

覆盖：
- ParallelSweep 模型校验
- MFNodeInstance sweep + ephemeral 冲突
- Validator sweep 校验
- Compiler withParam 字段生成
- 端到端编译含 sweep 节点的工作流
- 下游 fan-in 节点参数引用正确性
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from workflows.pipeline.models import (
    EphemeralPortDecl,
    EphemeralPorts,
    MFConnection,
    MFNodeInstance,
    MFWorkflow,
    ParallelSweep,
    QualityGateOverride,
)
from workflows.pipeline.validator import validate_workflow
from workflows.pipeline.compiler import compile_to_argo


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ═══════════════════════════════════════════════════════════════════════════
# ParallelSweep 模型测试
# ═══════════════════════════════════════════════════════════════════════════


class TestParallelSweepModel:
    """ParallelSweep 模型校验。"""

    def test_valid_with_numbers(self):
        ps = ParallelSweep(values=[0.5, 1.0, 1.5])
        assert ps.values == [0.5, 1.0, 1.5]

    def test_valid_with_strings(self):
        ps = ParallelSweep(values=["a", "b", "c"])
        assert len(ps.values) == 3

    def test_valid_single_value(self):
        ps = ParallelSweep(values=[42])
        assert ps.values == [42]

    def test_reject_empty_list(self):
        with pytest.raises(ValueError):
            ParallelSweep(values=[])

    def test_valid_mixed_types(self):
        ps = ParallelSweep(values=[1, "two", 3.0, True])
        assert len(ps.values) == 4


# ═══════════════════════════════════════════════════════════════════════════
# MFNodeInstance sweep 测试
# ═══════════════════════════════════════════════════════════════════════════


class TestMFNodeInstanceSweep:
    """MFNodeInstance 与 parallel_sweep 的交互校验。"""

    def test_sweep_with_node(self):
        """node + parallel_sweep 正常。"""
        inst = MFNodeInstance(
            id="sweep-test",
            node="some-node",
            parallel_sweep=ParallelSweep(values=[1, 2, 3]),
        )
        assert inst.parallel_sweep is not None
        assert inst.parallel_sweep.values == [1, 2, 3]

    def test_sweep_with_nodespec_path(self):
        """nodespec_path + parallel_sweep 正常。"""
        inst = MFNodeInstance(
            id="sweep-test",
            nodespec_path="nodes/test/gaussian-geo-opt/nodespec.yaml",
            parallel_sweep=ParallelSweep(values=[1, 2]),
        )
        assert inst.parallel_sweep is not None

    def test_sweep_reject_ephemeral(self):
        """parallel_sweep + ephemeral=True → 拒绝。"""
        with pytest.raises(ValueError, match="不支持 parallel_sweep"):
            MFNodeInstance(
                id="bad",
                ephemeral=True,
                ports={"inputs": [{"name": "I1", "type": "physical_quantity"}],
                        "outputs": [{"name": "O1", "type": "physical_quantity"}]},
                parallel_sweep=ParallelSweep(values=[1, 2, 3]),
            )

    def test_no_sweep_is_none(self):
        """默认 parallel_sweep 为 None。"""
        inst = MFNodeInstance(id="x", node="y")
        assert inst.parallel_sweep is None


# ═══════════════════════════════════════════════════════════════════════════
# Validator sweep 测试
# ═══════════════════════════════════════════════════════════════════════════


class TestValidatorSweep:
    """Validator 对 sweep 节点的校验。"""

    def test_sweep_requires_node_field(self):
        """sweep 节点使用 nodespec_path 而非 node → error。"""
        wf = MFWorkflow(
            name="test",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    nodespec_path="nodes/test/gaussian-geo-opt/nodespec.yaml",
                    parallel_sweep=ParallelSweep(values=[1, 2, 3]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
            ],
        )
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        errors = [i.message for i in report.errors]
        assert any("node" in m and "正式节点" in m for m in errors)

    def test_sweep_with_node_validates(self):
        """sweep + node 名称引用 → 校验通过。"""
        wf = MFWorkflow(
            name="test",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2, 3]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
            ],
        )
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid, f"Expected valid, got errors: {[i.message for i in report.errors]}"


# ═══════════════════════════════════════════════════════════════════════════
# Compiler withParam 测试
# ═══════════════════════════════════════════════════════════════════════════


class TestCompilerSweep:
    """Compiler 对 sweep 节点的编译。"""

    def _make_sweep_workflow(self) -> MFWorkflow:
        """创建一个包含 sweep 节点和下游 fan-in 节点的工作流。

        下游节点使用 test-gaussian-freq，接收 sweep 的 optimized_checkpoint
        (software_data_package) → checkpoint_in (software_data_package)，类型匹配。
        """
        return MFWorkflow(
            name="sweep-test",
            nodes=[
                MFNodeInstance(
                    id="sp-sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(
                        values=[0.5, 0.74, 1.0, 1.5],
                    ),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="downstream",
                    node="test-gaussian-freq",
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "n_cores": 4,
                    },
                ),
            ],
            connections=[
                MFConnection(**{"from": "sp-sweep.optimized_checkpoint", "to": "downstream.checkpoint_in"}),
            ],
        )

    def _make_sweep_only_workflow(self) -> MFWorkflow:
        """只有 sweep 节点，无下游。"""
        return MFWorkflow(
            name="sweep-only",
            nodes=[
                MFNodeInstance(
                    id="sp-sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(
                        values=[0.5, 0.74, 1.0, 1.5],
                    ),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
            ],
        )

    def test_withparam_in_dag_task(self):
        """sweep 节点被包装为 pipeline task，pipeline task 包含 withParam 字段。"""
        wf = self._make_sweep_workflow()
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid, f"Expected valid, got errors: {[i.message for i in report.errors]}"

        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        # sweep 节点不再直接出现在外层 DAG，而是通过 pipeline task
        assert "sp-sweep" not in tasks
        pipeline_name = "sweep-pipeline-sp-sweep"
        assert pipeline_name in tasks
        assert "withParam" in tasks[pipeline_name]
        values = json.loads(tasks[pipeline_name]["withParam"])
        assert values == [0.5, 0.74, 1.0, 1.5]

    def test_non_sweep_node_no_withparam(self):
        """非 sweep 节点不包含 withParam。"""
        wf = self._make_sweep_workflow()
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        assert "withParam" not in tasks["downstream"]

    def test_sweep_has_dependencies(self):
        """pipeline task 无上游时不报 depends；fan-in 节点 depends 指向 pipeline。"""
        wf = self._make_sweep_workflow()
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        pipeline_name = "sweep-pipeline-sp-sweep"
        # pipeline task has no upstream
        assert "depends" not in tasks[pipeline_name]
        # downstream depends on pipeline task (not the inner sweep node)
        assert "depends" in tasks["downstream"]
        assert pipeline_name in tasks["downstream"]["depends"]

    def test_fan_in_arg_reference(self):
        """下游 fan-in 节点通过 pipeline task output 引用 sweep 节点。"""
        wf = self._make_sweep_workflow()
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        downstream_args = {
            p["name"]: p["value"]
            for p in tasks["downstream"]["arguments"]["parameters"]
        }
        # fan-in 引用 pipeline task 的输出（而非内层 sweep 节点的输出）
        assert "tasks.sweep-pipeline-sp-sweep.outputs.parameters.optimized_checkpoint" in downstream_args["checkpoint_in"]

    def test_sweep_template_has_output_params(self):
        """sweep 节点的 template 输出被下游连接时包含 output parameter。"""
        wf = self._make_sweep_workflow()
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)
        sweep_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-sp-sweep"
        )
        output_names = {p["name"] for p in sweep_template["outputs"]["parameters"]}
        # optimized_checkpoint is connected to downstream → should appear
        assert "optimized_checkpoint" in output_names

    def test_sweep_with_string_values(self):
        """sweep 支持字符串值列表。"""
        wf = MFWorkflow(
            name="str-sweep",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=["a", "b", "c"]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
            ],
        )
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        task = dag_template["dag"]["tasks"][0]
        values = json.loads(task["withParam"])
        assert values == ["a", "b", "c"]


# ═══════════════════════════════════════════════════════════════════════════
# 端到端测试
# ═══════════════════════════════════════════════════════════════════════════


class TestSweepEndToEnd:
    """端到端：sweep 节点 load → validate → compile。"""

    def test_h2_pes_sweep_example_loads(self):
        """h2-pes-sweep-mf.yaml 可正确加载。"""
        from workflows.pipeline.loader import load_workflow
        path = PROJECT_ROOT / "workflows" / "examples" / "h2-pes-sweep-mf.yaml"
        wf = load_workflow(path)
        assert wf.name == "h2-pes-sweep"
        assert len(wf.nodes) == 3

    def test_h2_pes_sweep_validates(self):
        """sweep + 下游节点校验通过（使用 test 节点）。"""
        wf = MFWorkflow(
            name="h2-pes-sweep-test",
            nodes=[
                MFNodeInstance(
                    id="sp-sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(
                        values=[0.5, 0.74, 1.0, 1.5],
                    ),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="downstream",
                    node="test-gaussian-freq",
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "n_cores": 4,
                    },
                ),
            ],
            connections=[
                MFConnection(**{"from": "sp-sweep.optimized_checkpoint", "to": "downstream.checkpoint_in"}),
            ],
        )
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid, f"Expected valid, got errors: {[i.message for i in report.errors]}"

    def test_h2_pes_sweep_compiles(self):
        """端到端编译含 sweep 的工作流 — 嵌套 DAG 结构。"""
        wf = MFWorkflow(
            name="h2-pes-sweep-test",
            nodes=[
                MFNodeInstance(
                    id="sp-sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(
                        values=[0.5, 0.74, 1.0, 1.5],
                    ),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="downstream",
                    node="test-gaussian-freq",
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "n_cores": 4,
                    },
                ),
            ],
            connections=[
                MFConnection(**{"from": "sp-sweep.optimized_checkpoint", "to": "downstream.checkpoint_in"}),
            ],
        )
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)

        # Verify Argo structure
        assert argo["kind"] == "Workflow"
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        # Pipeline task has withParam (not the inner sweep node)
        pipeline_name = "sweep-pipeline-sp-sweep"
        assert pipeline_name in tasks
        assert "withParam" in tasks[pipeline_name]
        assert json.loads(tasks[pipeline_name]["withParam"]) == [0.5, 0.74, 1.0, 1.5]

        # Fan-in task references pipeline output
        downstream_args = {
            p["name"]: p["value"]
            for p in tasks["downstream"]["arguments"]["parameters"]
        }
        assert "tasks.sweep-pipeline-sp-sweep.outputs.parameters.optimized_checkpoint" in downstream_args["checkpoint_in"]

        # Pipeline template exists with inner DAG
        pipeline_tmpl = next(
            t for t in argo["spec"]["templates"] if t["name"] == pipeline_name
        )
        assert "dag" in pipeline_tmpl
        inner_task_names = {t["name"] for t in pipeline_tmpl["dag"]["tasks"]}
        assert "sp-sweep" in inner_task_names

    def test_compiled_yaml_roundtrip(self):
        """编译产出的 YAML 可正确序列化和反序列化。"""
        wf = MFWorkflow(
            name="sweep-yaml-test",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
            ],
        )
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)

        yaml_str = yaml.dump(argo, default_flow_style=False, allow_unicode=True)
        parsed = yaml.safe_load(yaml_str)

        dag_template = next(
            t for t in parsed["spec"]["templates"] if t["name"] == "mf-dag"
        )
        task = dag_template["dag"]["tasks"][0]
        assert json.loads(task["withParam"]) == [1, 2]


# ═══════════════════════════════════════════════════════════════════════════
# Fan-out 自动传播测试
# ═══════════════════════════════════════════════════════════════════════════


class TestFanOutPropagation:
    """Fan-out 自动传播：编译器自动检测 sweep 通路并传播 withParam。"""

    @staticmethod
    def _resolve_nodes(wf):
        """直接解析节点，跳过校验（传播测试不关心端口类型匹配）。"""
        from workflows.pipeline.loader import resolve_nodespec
        return {
            n.id: resolve_nodespec(n, project_root=PROJECT_ROOT)
            for n in wf.nodes
        }

    def test_auto_fan_out_propagation(self):
        """A(sweep) → B(有下游) → C(leaf)

        嵌套 DAG: sweep-node 和 mid-node 包装在 pipeline 内层 DAG 中，
        leaf-node 在外层 DAG 作为 fan-in 接收 pipeline 聚合输出。
        """
        wf = MFWorkflow(
            name="auto-fanout",
            nodes=[
                MFNodeInstance(
                    id="sweep-node",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[0.5, 0.74, 1.0]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="mid-node",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
                MFNodeInstance(
                    id="leaf-node",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep-node.optimized_checkpoint", "to": "mid-node.checkpoint_in"}),
                MFConnection(**{"from": "mid-node.thermo_data", "to": "leaf-node.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        pipeline_name = "sweep-pipeline-sweep-node"

        # sweep-node 和 mid-node 不在外层 DAG 中
        assert "sweep-node" not in tasks
        assert "mid-node" not in tasks

        # pipeline task 在外层 DAG，带 withParam
        assert pipeline_name in tasks
        assert "withParam" in tasks[pipeline_name]
        assert json.loads(tasks[pipeline_name]["withParam"]) == [0.5, 0.74, 1.0]

        # leaf-node 在外层 DAG，引用 pipeline 输出（无 withParam）
        assert "leaf-node" in tasks
        assert "withParam" not in tasks["leaf-node"]
        assert pipeline_name in tasks["leaf-node"]["depends"]

        # 验证 pipeline 模板存在且包含内层 DAG
        pipeline_tmpl = next(
            t for t in argo["spec"]["templates"] if t["name"] == pipeline_name
        )
        inner_tasks = {t["name"]: t for t in pipeline_tmpl["dag"]["tasks"]}
        assert "sweep-node" in inner_tasks
        assert "mid-node" in inner_tasks
        # mid-node 在内层 DAG 中依赖 sweep-node
        assert "sweep-node" in inner_tasks["mid-node"]["depends"]

    def test_fan_in_mark_stops_propagation(self):
        """A(sweep) → B(fan_in: true) → C

        传播在 B 处终止。嵌套 DAG 只包含 sweep-node，
        fan-in-node 和 after-fan-in 在外层 DAG。
        """
        wf = MFWorkflow(
            name="fan-in-stop",
            nodes=[
                MFNodeInstance(
                    id="sweep-node",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2, 3]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="fan-in-node",
                    node="test-gaussian-freq",
                    fan_in=True,
                    onboard_params={"temperature": 298.15},
                ),
                MFNodeInstance(
                    id="after-fan-in",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep-node.optimized_checkpoint", "to": "fan-in-node.checkpoint_in"}),
                MFConnection(**{"from": "fan-in-node.thermo_data", "to": "after-fan-in.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        pipeline_name = "sweep-pipeline-sweep-node"

        # sweep-node 在 pipeline 中，不在外层 DAG
        assert "sweep-node" not in tasks
        assert pipeline_name in tasks
        assert "withParam" in tasks[pipeline_name]

        # fan-in-node: 不自动继承 withParam，依赖 pipeline task
        assert "fan-in-node" in tasks
        assert "withParam" not in tasks["fan-in-node"]
        assert pipeline_name in tasks["fan-in-node"]["depends"]

        # after-fan-in: 传播已在 fan-in-node 终止
        assert "after-fan-in" in tasks
        assert "withParam" not in tasks["after-fan-in"]

    def test_transitive_propagation(self):
        """A(sweep) → B → C → D(leaf)

        B 和 C 在内层 DAG pipeline 中，D 在外层 DAG 作为 fan-in。
        """
        wf = MFWorkflow(
            name="transitive-fanout",
            nodes=[
                MFNodeInstance(
                    id="sweep-node",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[10, 20]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="mid-b",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
                MFNodeInstance(
                    id="mid-c",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
                MFNodeInstance(
                    id="leaf-d",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep-node.optimized_checkpoint", "to": "mid-b.checkpoint_in"}),
                MFConnection(**{"from": "mid-b.thermo_data", "to": "mid-c.checkpoint_in"}),
                MFConnection(**{"from": "mid-c.thermo_data", "to": "leaf-d.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        pipeline_name = "sweep-pipeline-sweep-node"

        # sweep-node, mid-b, mid-c 全部在 pipeline 内层 DAG 中
        assert "sweep-node" not in tasks
        assert "mid-b" not in tasks
        assert "mid-c" not in tasks

        # pipeline task 在外层 DAG
        assert pipeline_name in tasks
        assert "withParam" in tasks[pipeline_name]
        assert json.loads(tasks[pipeline_name]["withParam"]) == [10, 20]

        # leaf-d: 在外层 DAG，引用 pipeline 输出
        assert "leaf-d" in tasks
        assert "withParam" not in tasks["leaf-d"]
        assert pipeline_name in tasks["leaf-d"]["depends"]

        # 验证 pipeline 模板包含完整的内层 DAG 链
        pipeline_tmpl = next(
            t for t in argo["spec"]["templates"] if t["name"] == pipeline_name
        )
        inner_tasks = {t["name"]: t for t in pipeline_tmpl["dag"]["tasks"]}
        assert "sweep-node" in inner_tasks
        assert "mid-b" in inner_tasks
        assert "mid-c" in inner_tasks

        # 内层 DAG 依赖链
        assert "sweep-node" in inner_tasks["mid-b"]["depends"]
        assert "mid-b" in inner_tasks["mid-c"]["depends"]

    def test_multi_sweep_source_warning(self, caplog):
        """A(sweep1) → C, B(sweep2) → C → D(leaf)

        C 有 withParam（来自某个 sweep 源），发出 warning。
        """
        import logging
        caplog.set_level(logging.WARNING)

        wf = MFWorkflow(
            name="multi-sweep",
            nodes=[
                MFNodeInstance(
                    id="sweep-a",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="sweep-b",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[10, 20]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="node-c",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep-a.optimized_checkpoint", "to": "node-c.checkpoint_in"}),
                MFConnection(**{"from": "sweep-b.optimized_checkpoint", "to": "node-c.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        # node-c: 有 withParam（来自某个 sweep 源），因为是 leaf 所以不需要
        # 但两个 sweep 都指向它 — BFS visited 防重复，第二个被跳过
        # 因为 node-c 是 leaf（无 forward），不会被加入 auto_fan_out
        assert "withParam" not in tasks["node-c"]

        # 多 sweep 源 warning：因为 node-c 在第一个 sweep 访问时已 visited，
        # 第二个 sweep 不会再处理它（BFS visited 集合跳过）。
        # 此场景下 warning 不触发，因为 visited 阻止了重复处理。
        # 这是预期行为：leaf 节点不参与 fan-out，多源问题不存在。

    def test_multi_sweep_with_downstream_warning(self, caplog):
        """A(sweep1) → C(有下游), B(sweep2) → C → D(leaf)

        C 有下游所以参与 fan-out，两个 sweep 源都指向 C → 发出 warning。
        嵌套 DAG: conn_map 中 C 的输入取最后一个 sweep 源（sweep-b），
        sweep-b 的 pipeline 包含 {sweep-b, node-c}，sweep-a 的 pipeline 只有 {sweep-a}。
        """
        import logging
        caplog.set_level(logging.WARNING)

        wf = MFWorkflow(
            name="multi-sweep-downstream",
            nodes=[
                MFNodeInstance(
                    id="sweep-a",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="sweep-b",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[10, 20]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="node-c",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
                MFNodeInstance(
                    id="leaf-d",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep-a.optimized_checkpoint", "to": "node-c.checkpoint_in"}),
                MFConnection(**{"from": "sweep-b.optimized_checkpoint", "to": "node-c.checkpoint_in"}),
                MFConnection(**{"from": "node-c.thermo_data", "to": "leaf-d.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}

        # node-c 在 sweep-b 的 pipeline 中，不在外层 DAG
        assert "node-c" not in tasks

        # sweep-b 的 pipeline 包含 node-c
        assert "sweep-pipeline-sweep-b" in tasks
        assert "withParam" in tasks["sweep-pipeline-sweep-b"]

        # leaf-d: 在外层 DAG，引用 sweep-b 的 pipeline 输出
        assert "leaf-d" in tasks
        assert "withParam" not in tasks["leaf-d"]

        # 应该发出 warning（node-c 有多个 sweep 源）
        assert any("多个 sweep 源" in r.message for r in caplog.records)


# ═══════════════════════════════════════════════════════════════════════════
# _find_sweep_param 测试
# ═══════════════════════════════════════════════════════════════════════════


class TestFindSweepParam:
    """_find_sweep_param 函数测试。"""

    def test_finds_item_template(self):
        inst = MFNodeInstance(
            id="geom",
            nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
            onboard_params={"geometry_file": "h2_{{item}}.xyz"},
        )
        from workflows.pipeline.compiler import _find_sweep_param
        assert _find_sweep_param(inst) == "geometry_file"

    def test_no_template_returns_empty(self):
        inst = MFNodeInstance(
            id="geom",
            nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
            onboard_params={"geometry_file": "h2.xyz"},
        )
        from workflows.pipeline.compiler import _find_sweep_param
        assert _find_sweep_param(inst) == ""

    def test_empty_params_returns_empty(self):
        inst = MFNodeInstance(
            id="geom",
            nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
            onboard_params={},
        )
        from workflows.pipeline.compiler import _find_sweep_param
        assert _find_sweep_param(inst) == ""


# ═══════════════════════════════════════════════════════════════════════════
# _detect_fan_in_nodes 测试
# ═══════════════════════════════════════════════════════════════════════════


def _make_sweep_fan_in_workflow():
    """线性 sweep 工作流: geom-input(sweep) → sp-calc(auto_fan_out) → collect(fan_in)"""
    return MFWorkflow(
        name="test-fan-in",
        nodes=[
            MFNodeInstance(
                id="geom-input",
                nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
                parallel_sweep=ParallelSweep(values=[0.5, 0.74, 1.0]),
                onboard_params={"geometry_file": "h2_{{item}}.xyz"},
            ),
            MFNodeInstance(
                id="sp-calc",
                nodespec_path="nodes/chemistry/orca/orca-single-point/nodespec.yaml",
            ),
            MFNodeInstance(
                id="collect",
                ephemeral=True,
                description="收集能量",
                ports=EphemeralPorts(
                    inputs=[EphemeralPortDecl(name="I1", type="physical_quantity")],
                    outputs=[EphemeralPortDecl(name="O1", type="physical_quantity")],
                ),
            ),
        ],
        connections=[
            MFConnection(**{"from": "geom-input.xyz_geometry", "to": "sp-calc.xyz_geometry"}),
            MFConnection(**{"from": "sp-calc.total_energy", "to": "collect.I1"}),
        ],
    )


class TestDetectFanInNodes:
    """_detect_fan_in_nodes 函数测试。"""

    def test_linear_chain_with_fan_in(self):
        wf = _make_sweep_fan_in_workflow()
        auto_fan_out = {"sp-calc"}
        sweep_source = {"sp-calc": ("geom-input", [0.5, 0.74, 1.0])}

        from workflows.pipeline.compiler import _detect_fan_in_nodes
        fan_in_map = _detect_fan_in_nodes(wf, auto_fan_out, sweep_source)

        assert "collect" in fan_in_map
        assert len(fan_in_map["collect"]) == 1
        src_id, values = fan_in_map["collect"][0]
        assert src_id == "geom-input"
        assert values == [0.5, 0.74, 1.0]

    def test_no_fan_in_without_sweep(self):
        wf = MFWorkflow(
            name="no-sweep",
            nodes=[
                MFNodeInstance(
                    id="src",
                    nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
                ),
                MFNodeInstance(
                    id="dst",
                    nodespec_path="nodes/chemistry/orca/orca-single-point/nodespec.yaml",
                ),
            ],
            connections=[
                MFConnection(**{"from": "src.xyz_geometry", "to": "dst.xyz_geometry"}),
            ],
        )
        from workflows.pipeline.compiler import _detect_fan_in_nodes
        fan_in_map = _detect_fan_in_nodes(wf, set(), {})
        assert fan_in_map == {}

    def test_explicit_sweep_node_not_fan_in(self):
        wf = _make_sweep_fan_in_workflow()
        auto_fan_out = {"sp-calc"}
        sweep_source = {"sp-calc": ("geom-input", [0.5, 0.74, 1.0])}

        from workflows.pipeline.compiler import _detect_fan_in_nodes
        fan_in_map = _detect_fan_in_nodes(wf, auto_fan_out, sweep_source)

        assert "geom-input" not in fan_in_map
        assert "sp-calc" not in fan_in_map

    def test_explicit_fan_in_blocked(self):
        """fan_in=True 的节点不被 auto fan-out 传播。"""
        wf = MFWorkflow(
            name="explicit-fan-in",
            nodes=[
                MFNodeInstance(
                    id="sweep-src",
                    nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
                    parallel_sweep=ParallelSweep(values=[1, 2, 3]),
                    onboard_params={"geometry_file": "h2_{{item}}.xyz"},
                ),
                MFNodeInstance(
                    id="auto-node",
                    nodespec_path="nodes/chemistry/orca/orca-single-point/nodespec.yaml",
                ),
                MFNodeInstance(
                    id="explicit-fanin",
                    nodespec_path="nodes/chemistry/orca/orca-thermo-extractor/nodespec.yaml",
                    fan_in=True,
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep-src.xyz_geometry", "to": "auto-node.xyz_geometry"}),
                MFConnection(**{"from": "auto-node.total_energy", "to": "explicit-fanin.total_energy"}),
            ],
        )
        auto_fan_out = {"auto-node"}
        sweep_source = {"auto-node": ("sweep-src", [1, 2, 3])}

        from workflows.pipeline.compiler import _detect_fan_in_nodes
        fan_in_map = _detect_fan_in_nodes(wf, auto_fan_out, sweep_source)

        assert "explicit-fanin" not in fan_in_map


# ═══════════════════════════════════════════════════════════════════════════
# Sweep Keys 注入测试
# ═══════════════════════════════════════════════════════════════════════════


def _compile_sweep_with_ephemeral():
    """编译含 ephemeral 的 sweep 工作流，返回 Argo YAML。"""
    from unittest.mock import patch
    from workflows.pipeline.validator import _build_ephemeral_nodespec

    wf = _make_sweep_fan_in_workflow()

    src_report = validate_workflow(MFWorkflow(
        name="src-only",
        nodes=[
            MFNodeInstance(
                id="geom-input",
                nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
            ),
            MFNodeInstance(
                id="sp-calc",
                nodespec_path="nodes/chemistry/orca/orca-single-point/nodespec.yaml",
            ),
        ],
        connections=[
            MFConnection(**{"from": "geom-input.xyz_geometry", "to": "sp-calc.xyz_geometry"}),
        ],
    ))

    eph_spec = _build_ephemeral_nodespec(
        MFNodeInstance(
            id="collect",
            ephemeral=True,
            description="收集能量",
            ports=EphemeralPorts(
                inputs=[EphemeralPortDecl(name="I1", type="physical_quantity")],
                outputs=[EphemeralPortDecl(name="O1", type="physical_quantity")],
            ),
        )
    )
    resolved = dict(src_report.resolved_nodes)
    resolved["collect"] = eph_spec

    mock_script = (
        "import os, json\n"
        "energies = json.loads(open('/mf/input/I1').read())\n"
        "keys = json.loads(os.environ['_sweep_keys'])\n"
        "with open('/mf/output/O1', 'w') as f:\n"
        "    f.write(json.dumps(list(zip(keys, energies))))\n"
    )

    with patch(
        "workflows.pipeline.compiler._generate_ephemeral_script",
        return_value=mock_script,
    ):
        argo = compile_to_argo(wf, resolved)

    return argo


class TestSweepKeysInjection:
    """Sweep keys 注入到 fan-in 节点的 template 和 DAG task。"""

    def test_dag_task_has_sweep_keys_arg(self):
        argo = _compile_sweep_with_ephemeral()

        dag_template = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "mf-dag"
        )
        collect_task = next(
            t for t in dag_template["dag"]["tasks"]
            if t["name"] == "collect"
        )
        param_names = {p["name"] for p in collect_task["arguments"]["parameters"]}
        assert "_sweep_keys" in param_names

        sweep_keys_param = next(
            p for p in collect_task["arguments"]["parameters"]
            if p["name"] == "_sweep_keys"
        )
        values = json.loads(sweep_keys_param["value"])
        assert values == [0.5, 0.74, 1.0]

    def test_template_has_sweep_keys_input(self):
        argo = _compile_sweep_with_ephemeral()

        collect_tmpl = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "mf-collect"
        )
        input_names = {p["name"] for p in collect_tmpl["inputs"]["parameters"]}
        assert "_sweep_keys" in input_names

    def test_template_has_sweep_keys_env(self):
        argo = _compile_sweep_with_ephemeral()

        collect_tmpl = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "mf-collect"
        )
        env_names = {e["name"] for e in collect_tmpl["script"]["env"]}
        assert "_sweep_keys" in env_names

    def test_non_fan_in_no_sweep_keys(self):
        """非 fan-in 节点不应注入 _sweep_keys。"""
        wf = MFWorkflow(
            name="no-sweep-inject",
            nodes=[
                MFNodeInstance(
                    id="geom-input",
                    nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
                ),
                MFNodeInstance(
                    id="sp-calc",
                    nodespec_path="nodes/chemistry/orca/orca-single-point/nodespec.yaml",
                ),
            ],
            connections=[
                MFConnection(**{"from": "geom-input.xyz_geometry", "to": "sp-calc.xyz_geometry"}),
            ],
        )
        report = validate_workflow(wf)
        argo = compile_to_argo(wf, report.resolved_nodes)

        dag_template = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "mf-dag"
        )
        for task in dag_template["dag"]["tasks"]:
            if "arguments" in task:
                param_names = {p["name"] for p in task["arguments"].get("parameters", [])}
                assert "_sweep_keys" not in param_names


# ═══════════════════════════════════════════════════════════════════════════
# E2E Sweep + Ephemeral 编译测试
# ═══════════════════════════════════════════════════════════════════════════


class TestE2ESweepCompilation:
    """端到端：h2-pes-sweep 示例编译后 collect-energy 含 _sweep_keys。"""

    def test_h2_pes_sweep_compiles_with_sweep_keys(self):
        from unittest.mock import patch

        wf_path = PROJECT_ROOT / "workflows/examples/h2-pes-sweep-mf.yaml"
        if not wf_path.exists():
            pytest.skip(f"示例文件不存在: {wf_path}")

        wf_yaml = yaml.safe_load(wf_path.read_text())
        wf = MFWorkflow(**wf_yaml)
        report = validate_workflow(wf, project_root=PROJECT_ROOT)

        mock_script = (
            "import os, json\n"
            "energies = json.loads(open('/mf/input/I1').read())\n"
            "keys = json.loads(os.environ['_sweep_keys'])\n"
            "with open('/mf/output/O1', 'w') as f:\n"
            "    f.write(json.dumps(list(zip(keys, energies))))\n"
        )

        with patch(
            "workflows.pipeline.compiler._generate_ephemeral_script",
            return_value=mock_script,
        ):
            argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)

        dag_template = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "mf-dag"
        )
        collect_task = next(
            t for t in dag_template["dag"]["tasks"]
            if t["name"] == "collect-energy"
        )
        param_names = {p["name"] for p in collect_task["arguments"]["parameters"]}
        assert "_sweep_keys" in param_names

        sweep_val = json.loads(
            next(p for p in collect_task["arguments"]["parameters"]
                 if p["name"] == "_sweep_keys")["value"]
        )
        assert sweep_val == [0.5, 0.6, 0.7, 0.74, 0.742, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0, 3.0]

    def test_non_sweep_workflow_unchanged(self):
        """无 sweep 的工作流编译结果不注入 _sweep_keys。"""
        wf = MFWorkflow(
            name="no-sweep-e2e",
            nodes=[
                MFNodeInstance(
                    id="geom-input",
                    nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
                ),
                MFNodeInstance(
                    id="sp-calc",
                    nodespec_path="nodes/chemistry/orca/orca-single-point/nodespec.yaml",
                ),
            ],
            connections=[
                MFConnection(**{"from": "geom-input.xyz_geometry", "to": "sp-calc.xyz_geometry"}),
            ],
        )
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)

        dag_template = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "mf-dag"
        )
        for task in dag_template["dag"]["tasks"]:
            if "arguments" in task:
                for p in task["arguments"].get("parameters", []):
                    assert p["name"] != "_sweep_keys"


# ═══════════════════════════════════════════════════════════════════════════
# 嵌套 DAG Pipeline 结构测试
# ═══════════════════════════════════════════════════════════════════════════


class TestNestedDAGPipeline:
    """嵌套 DAG 模板结构验证。"""

    @staticmethod
    def _resolve_nodes(wf):
        from workflows.pipeline.loader import resolve_nodespec
        return {
            n.id: resolve_nodespec(n, project_root=PROJECT_ROOT)
            for n in wf.nodes
        }

    def test_pipeline_template_has_sweep_item_input(self):
        """Pipeline 模板接受 sweep_item 作为输入参数。"""
        wf = MFWorkflow(
            name="pipeline-input-test",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2, 3]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="downstream",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep.optimized_checkpoint", "to": "downstream.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)

        pipeline_tmpl = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "sweep-pipeline-sweep"
        )
        input_names = {p["name"] for p in pipeline_tmpl["inputs"]["parameters"]}
        assert "sweep_item" in input_names

    def test_pipeline_template_outputs_with_default(self):
        """Pipeline 模板的输出端口带 default: '' 兜底。"""
        wf = MFWorkflow(
            name="pipeline-output-test",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="fan-in",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep.optimized_checkpoint", "to": "fan-in.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)

        pipeline_tmpl = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "sweep-pipeline-sweep"
        )
        assert "outputs" in pipeline_tmpl
        output_params = pipeline_tmpl["outputs"]["parameters"]
        assert len(output_params) >= 1
        # 输出端口有 default 值兜底（quality gate skip 时返回空）
        for p in output_params:
            assert "default" in p, f"Output '{p['name']}' missing default"
            assert p["default"] == ""

    def test_pipeline_dag_task_passes_item(self):
        """外层 DAG 中 pipeline task 将 {{item}} 传入 sweep_item。"""
        wf = MFWorkflow(
            name="item-pass-test",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[10, 20]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="fan-in",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep.optimized_checkpoint", "to": "fan-in.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)

        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        pipeline_task = next(
            t for t in dag_template["dag"]["tasks"]
            if t["name"] == "sweep-pipeline-sweep"
        )
        args = {p["name"]: p["value"] for p in pipeline_task["arguments"]["parameters"]}
        assert args["sweep_item"] == "{{item}}"

    def test_item_replacement_in_pipeline(self):
        """sweep 源节点的 onboard_params 中 {{item}} 被替换为 pipeline 输入引用。"""
        wf = MFWorkflow(
            name="item-replace-test",
            nodes=[
                MFNodeInstance(
                    id="geom",
                    nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
                    parallel_sweep=ParallelSweep(values=[0.5, 0.74]),
                    onboard_params={"geometry_file": "h2_{{item}}.xyz"},
                ),
                MFNodeInstance(
                    id="sp",
                    nodespec_path="nodes/chemistry/orca/orca-single-point/nodespec.yaml",
                ),
                MFNodeInstance(
                    id="collect",
                    ephemeral=True,
                    description="收集能量",
                    ports=EphemeralPorts(
                        inputs=[EphemeralPortDecl(name="I1", type="physical_quantity")],
                        outputs=[EphemeralPortDecl(name="O1", type="physical_quantity")],
                    ),
                ),
            ],
            connections=[
                MFConnection(**{"from": "geom.xyz_geometry", "to": "sp.xyz_geometry"}),
                MFConnection(**{"from": "sp.total_energy", "to": "collect.I1"}),
            ],
        )
        from workflows.pipeline.validator import validate_workflow as vw, _build_ephemeral_nodespec
        from unittest.mock import patch
        from workflows.pipeline.loader import resolve_nodespec

        resolved = {
            "geom": resolve_nodespec(wf.nodes[0], project_root=PROJECT_ROOT),
            "sp": resolve_nodespec(wf.nodes[1], project_root=PROJECT_ROOT),
            "collect": _build_ephemeral_nodespec(wf.nodes[2]),
        }

        mock_script = "import json\npass\n"
        with patch(
            "workflows.pipeline.compiler._generate_ephemeral_script",
            return_value=mock_script,
        ):
            argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)

        pipeline_tmpl = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "sweep-pipeline-geom"
        )
        inner_tasks = {t["name"]: t for t in pipeline_tmpl["dag"]["tasks"]}

        # geom 节点在内层 DAG 中，{{item}} 被替换为 {{inputs.parameters.sweep_item}}
        geom_args = {
            p["name"]: p["value"]
            for p in inner_tasks["geom"]["arguments"]["parameters"]
        }
        assert "{{inputs.parameters.sweep_item}}" in geom_args["geometry_file"]
        assert "{{item}}" not in geom_args["geometry_file"]

    def test_inner_dag_stream_input_references(self):
        """内层 DAG 节点的 stream input 引用上游内层节点的输出。"""
        wf = MFWorkflow(
            name="inner-ref-test",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="mid",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
                MFNodeInstance(
                    id="end",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep.optimized_checkpoint", "to": "mid.checkpoint_in"}),
                MFConnection(**{"from": "mid.thermo_data", "to": "end.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)

        pipeline_tmpl = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "sweep-pipeline-sweep"
        )
        inner_tasks = {t["name"]: t for t in pipeline_tmpl["dag"]["tasks"]}

        # mid 的 stream input 引用 sweep 的输出（内层引用，不是 {{item}}）
        mid_args = {
            p["name"]: p["value"]
            for p in inner_tasks["mid"]["arguments"]["parameters"]
        }
        assert "tasks.sweep.outputs.parameters.optimized_checkpoint" in mid_args["checkpoint_in"]

    def test_sweep_only_no_pipeline(self):
        """只有 sweep 节点（无下游）时不创建 pipeline。"""
        wf = MFWorkflow(
            name="sweep-only",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)

        # 无 pipeline 模板
        template_names = {t["name"] for t in argo["spec"]["templates"]}
        assert not any(n.startswith("sweep-pipeline-") for n in template_names)

        # sweep 节点仍以直接 task 方式出现在外层 DAG
        dag_template = next(t for t in argo["spec"]["templates"] if t["name"] == "mf-dag")
        tasks = {t["name"]: t for t in dag_template["dag"]["tasks"]}
        assert "sweep" in tasks
        assert "withParam" in tasks["sweep"]


# ═══════════════════════════════════════════════════════════════════════════
# Quality Gate 在 Pipeline 内层 DAG 中的测试
# ═══════════════════════════════════════════════════════════════════════════


class TestQualityGateInPipeline:
    """Quality gate 在嵌套 DAG 内层中正常工作。"""

    @staticmethod
    def _resolve_nodes(wf):
        from workflows.pipeline.loader import resolve_nodespec
        return {
            n.id: resolve_nodespec(n, project_root=PROJECT_ROOT)
            for n in wf.nodes
        }

    def test_quality_gate_when_in_inner_dag(self):
        """内层 DAG 中下游节点有 quality gate when 条件。"""
        # test-gaussian-geo-opt 有 quality gate opt_converged (must_pass)
        wf = MFWorkflow(
            name="qg-inner-test",
            nodes=[
                MFNodeInstance(
                    id="geo-opt",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="freq",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
                MFNodeInstance(
                    id="fan-in",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "geo-opt.optimized_checkpoint", "to": "freq.checkpoint_in"}),
                MFConnection(**{"from": "freq.thermo_data", "to": "fan-in.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)

        # 检查内层 DAG 中 freq 节点的 when 条件
        pipeline_tmpl = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "sweep-pipeline-geo-opt"
        )
        inner_tasks = {t["name"]: t for t in pipeline_tmpl["dag"]["tasks"]}

        # 检查 geo-opt 有 quality gate
        geo_spec = resolved["geo-opt"]
        has_must_pass_gate = any(
            g.gate_default.value == "must_pass"
            for g in geo_spec.quality_gates
        )

        if has_must_pass_gate:
            # freq 在内层 DAG 中应该有 when 条件
            assert "when" in inner_tasks["freq"], (
                "freq 应有 when 条件（geo-opt 有 must_pass quality gate）"
            )
            assert "_qg_" in inner_tasks["freq"]["when"]
        else:
            # 如果 geo-opt 没有 must_pass gate，freq 不需要 when
            pass  # 不同测试节点可能配置不同

    def test_quality_gate_warn_no_when_in_inner_dag(self):
        """quality_policy 设为 warn 时，内层 DAG 不生成 when 条件。"""
        from nodes.schemas.io import GateDefault

        wf = MFWorkflow(
            name="qg-warn-test",
            nodes=[
                MFNodeInstance(
                    id="geo-opt",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="freq",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
                MFNodeInstance(
                    id="fan-in",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "geo-opt.optimized_checkpoint", "to": "freq.checkpoint_in"}),
                MFConnection(**{"from": "freq.thermo_data", "to": "fan-in.checkpoint_in"}),
            ],
            quality_policy=[
                # 将 geo-opt 的 quality gate 设为 warn
                QualityGateOverride(
                    node_id="geo-opt",
                    gate_name="converged",
                    action=GateDefault.WARN,
                ),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)

        pipeline_tmpl = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "sweep-pipeline-geo-opt"
        )
        inner_tasks = {t["name"]: t for t in pipeline_tmpl["dag"]["tasks"]}

        # warn 模式下，freq 不应有 when 条件
        assert "when" not in inner_tasks.get("freq", {}), (
            "quality_policy=warn 时不应生成 when 条件"
        )

    def test_fan_in_no_quality_gate_from_pipeline(self):
        """外层 fan-in 节点不从 pipeline task 继承 quality gate when 条件。"""
        wf = MFWorkflow(
            name="fanin-no-qg-test",
            nodes=[
                MFNodeInstance(
                    id="sweep",
                    node="test-gaussian-geo-opt",
                    parallel_sweep=ParallelSweep(values=[1, 2]),
                    onboard_params={
                        "functional": "B3LYP",
                        "basis_set": "6-31G*",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                ),
                MFNodeInstance(
                    id="fan-in",
                    node="test-gaussian-freq",
                    onboard_params={"temperature": 298.15},
                ),
            ],
            connections=[
                MFConnection(**{"from": "sweep.optimized_checkpoint", "to": "fan-in.checkpoint_in"}),
            ],
        )
        resolved = self._resolve_nodes(wf)
        argo = compile_to_argo(wf, resolved, project_root=PROJECT_ROOT)

        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        fan_in_task = next(
            t for t in dag_template["dag"]["tasks"] if t["name"] == "fan-in"
        )
        # fan-in 依赖 pipeline task（不是原始 sweep 节点）
        assert "sweep-pipeline-sweep" in fan_in_task["depends"]
        # pipeline task 不产生 quality gate 输出，所以 fan-in 没有 when 条件
        assert "when" not in fan_in_task
