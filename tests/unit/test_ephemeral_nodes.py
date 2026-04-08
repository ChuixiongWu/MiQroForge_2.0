"""临时节点（Ephemeral Nodes）单元测试。

覆盖：
- MFNodeInstance ephemeral 模型校验
- EphemeralPorts / EphemeralPortDecl 校验
- Validator 虚拟 NodeSpec 构建
- Evaluator 临时节点检查
- Compiler 临时节点 template 生成
"""

from __future__ import annotations

import pytest
import yaml

from nodes.schemas import NodeSpec
from workflows.pipeline.models import (
    EphemeralOnboardInput,
    EphemeralPortDecl,
    EphemeralPorts,
    MFConnection,
    MFNodeInstance,
    MFWorkflow,
)
from workflows.pipeline.validator import validate_workflow, _build_ephemeral_nodespec
from workflows.pipeline.compiler import compile_to_argo, _build_ephemeral_template


# ═══════════════════════════════════════════════════════════════════════════
# 模型校验测试
# ═══════════════════════════════════════════════════════════════════════════


class TestEphemeralPortDecl:
    """EphemeralPortDecl 模型测试。"""

    def test_valid_port(self):
        p = EphemeralPortDecl(name="I1", type="physical_quantity")
        assert p.name == "I1"
        assert p.type == "physical_quantity"

    def test_invalid_name_lowercase(self):
        with pytest.raises(ValueError):
            EphemeralPortDecl(name="i1", type="physical_quantity")

    def test_invalid_type(self):
        with pytest.raises(ValueError, match="无效的端口类型"):
            EphemeralPortDecl(name="O1", type="unknown_type")

    def test_valid_categories(self):
        for cat in ("physical_quantity", "software_data_package",
                     "logic_value", "report_object"):
            p = EphemeralPortDecl(name="I1", type=cat)
            assert p.type == cat


class TestEphemeralPorts:
    """EphemeralPorts 模型测试。"""

    def test_empty_ports(self):
        p = EphemeralPorts()
        assert p.inputs == []
        assert p.outputs == []

    def test_with_ports(self):
        p = EphemeralPorts(
            inputs=[EphemeralPortDecl(name="I1", type="physical_quantity")],
            outputs=[EphemeralPortDecl(name="O1", type="software_data_package")],
        )
        assert len(p.inputs) == 1
        assert len(p.outputs) == 1


class TestMFNodeInstanceEphemeral:
    """MFNodeInstance 临时节点模式测试。"""

    def test_ephemeral_valid(self):
        inst = MFNodeInstance(
            id="extract-energy",
            ephemeral=True,
            description="提取能量",
            ports=EphemeralPorts(
                inputs=[EphemeralPortDecl(name="I1", type="software_data_package")],
                outputs=[EphemeralPortDecl(name="O1", type="physical_quantity")],
            ),
        )
        assert inst.ephemeral is True
        assert inst.description == "提取能量"

    def test_ephemeral_requires_ports(self):
        with pytest.raises(ValueError, match="必须提供 ports"):
            MFNodeInstance(
                id="test",
                ephemeral=True,
                description="test",
            )

    def test_ephemeral_forbids_node(self):
        with pytest.raises(ValueError, match="临时节点不得指定"):
            MFNodeInstance(
                id="test",
                ephemeral=True,
                node="some-node",
                ports=EphemeralPorts(
                    inputs=[EphemeralPortDecl(name="I1", type="physical_quantity")],
                ),
            )

    def test_ephemeral_forbids_nodespec_path(self):
        with pytest.raises(ValueError, match="临时节点不得指定"):
            MFNodeInstance(
                id="test",
                ephemeral=True,
                nodespec_path="nodes/test/nodespec.yaml",
                ports=EphemeralPorts(
                    inputs=[EphemeralPortDecl(name="I1", type="physical_quantity")],
                ),
            )

    def test_ephemeral_with_onboard_inputs(self):
        inst = MFNodeInstance(
            id="test",
            ephemeral=True,
            description="test",
            ports=EphemeralPorts(
                inputs=[EphemeralPortDecl(name="I1", type="physical_quantity")],
            ),
            onboard_inputs=[
                EphemeralOnboardInput(name="threshold", kind="number", default=0.001),
            ],
        )
        assert len(inst.onboard_inputs) == 1
        assert inst.onboard_inputs[0].name == "threshold"

    def test_non_ephemeral_still_requires_source(self):
        with pytest.raises(ValueError, match="必须提供"):
            MFNodeInstance(id="test", ephemeral=False)


# ═══════════════════════════════════════════════════════════════════════════
# Validator 测试
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildEphemeralNodespec:
    """_build_ephemeral_nodespec 函数测试。"""

    def test_builds_valid_nodespec(self):
        inst = MFNodeInstance(
            id="ext",
            ephemeral=True,
            description="提取能量",
            ports=EphemeralPorts(
                inputs=[EphemeralPortDecl(name="I1", type="software_data_package")],
                outputs=[EphemeralPortDecl(name="O1", type="physical_quantity")],
            ),
        )
        spec = _build_ephemeral_nodespec(inst)
        assert isinstance(spec, NodeSpec)
        assert spec.metadata.name == "ext"
        assert len(spec.stream_inputs) == 1
        assert len(spec.stream_outputs) == 1
        assert spec.stream_inputs[0].name == "I1"
        assert spec.stream_outputs[0].name == "O1"

    def test_nodespec_with_onboard_inputs(self):
        inst = MFNodeInstance(
            id="ext",
            ephemeral=True,
            description="test",
            ports=EphemeralPorts(
                outputs=[EphemeralPortDecl(name="O1", type="physical_quantity")],
            ),
            onboard_inputs=[
                EphemeralOnboardInput(name="unit", kind="string", default="Ha"),
            ],
        )
        spec = _build_ephemeral_nodespec(inst)
        assert len(spec.onboard_inputs) == 1
        assert spec.onboard_inputs[0].name == "unit"
        assert spec.onboard_inputs[0].default == "Ha"


class TestValidateWorkflowEphemeral:
    """validate_workflow 中临时节点相关测试。"""

    def test_validate_with_ephemeral(self):
        """含临时节点的完整工作流校验。"""
        wf = MFWorkflow(
            name="test-ephemeral",
            nodes=[
                MFNodeInstance(
                    id="geom-input",
                    nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
                ),
                MFNodeInstance(
                    id="extract-energy",
                    ephemeral=True,
                    description="提取总能量",
                    ports=EphemeralPorts(
                        inputs=[
                            EphemeralPortDecl(
                                name="I1", type="software_data_package"
                            ),
                        ],
                        outputs=[
                            EphemeralPortDecl(
                                name="O1", type="physical_quantity"
                            ),
                        ],
                    ),
                ),
            ],
            connections=[
                MFConnection(
                    **{"from": "geom-input.xyz_geometry", "to": "extract-energy.I1"}
                ),
            ],
        )
        report = validate_workflow(wf)
        # 临时节点应被解析为虚拟 NodeSpec
        assert "extract-energy" in report.resolved_nodes
        assert isinstance(report.resolved_nodes["extract-energy"], NodeSpec)

    def test_ephemeral_missing_connection_rejected(self):
        """临时节点的未连接必填输入应被拒绝。"""
        wf = MFWorkflow(
            name="test-missing-conn",
            nodes=[
                MFNodeInstance(
                    id="src",
                    nodespec_path="nodes/chemistry/preprocessing/geometry-file-input/nodespec.yaml",
                ),
                MFNodeInstance(
                    id="eph",
                    ephemeral=True,
                    description="需要输入",
                    ports=EphemeralPorts(
                        inputs=[
                            EphemeralPortDecl(
                                name="I1", type="software_data_package"
                            ),
                        ],
                        outputs=[
                            EphemeralPortDecl(
                                name="O1", type="physical_quantity"
                            ),
                        ],
                    ),
                ),
            ],
            connections=[],  # 没有连线
        )
        report = validate_workflow(wf)
        assert not report.valid
        errors_text = " ".join(e.message for e in report.errors)
        assert "I1" in errors_text


# ═══════════════════════════════════════════════════════════════════════════
# Evaluator 测试
# ═══════════════════════════════════════════════════════════════════════════


class TestEphemeralEvaluator:
    """临时节点 evaluator 程序化检查测试。"""

    def test_syntax_check_passes(self):
        from agents.node_generator.evaluator import _programmatic_check_ephemeral
        from agents.schemas import NodeGenRequest

        request = NodeGenRequest(
            semantic_type="ephemeral",
            description="test",
            node_mode="ephemeral",
            ports={
                "inputs": [{"name": "I1", "type": "physical_quantity"}],
                "outputs": [{"name": "O1", "type": "physical_quantity"}],
            },
        )
        state = {
            "request": request,
            "run_sh": "import os\ndata = open('/mf/input/I1').read()\nopen('/mf/output/O1', 'w').write(data)",
            "iteration": 0,
        }
        issues = _programmatic_check_ephemeral(state)
        assert issues == []

    def test_syntax_check_catches_error(self):
        from agents.node_generator.evaluator import _programmatic_check_ephemeral
        from agents.schemas import NodeGenRequest

        request = NodeGenRequest(
            semantic_type="ephemeral",
            description="test",
            node_mode="ephemeral",
        )
        state = {
            "request": request,
            "run_sh": "def foo(\n  broken syntax",
            "iteration": 0,
        }
        issues = _programmatic_check_ephemeral(state)
        assert any("语法错误" in i for i in issues)

    def test_empty_script_rejected(self):
        from agents.node_generator.evaluator import _programmatic_check_ephemeral

        state = {"run_sh": "", "request": None}
        issues = _programmatic_check_ephemeral(state)
        assert "生成的脚本内容为空" in issues

    def test_missing_output_path(self):
        from agents.node_generator.evaluator import _programmatic_check_ephemeral
        from agents.schemas import NodeGenRequest

        request = NodeGenRequest(
            semantic_type="ephemeral",
            description="test",
            node_mode="ephemeral",
            ports={
                "inputs": [],
                "outputs": [{"name": "O1", "type": "physical_quantity"}],
            },
        )
        state = {
            "request": request,
            "run_sh": "print('hello')",
            "iteration": 0,
        }
        issues = _programmatic_check_ephemeral(state)
        assert any("O1" in i for i in issues)


# ═══════════════════════════════════════════════════════════════════════════
# Compiler 测试
# ═══════════════════════════════════════════════════════════════════════════


class TestEphemeralCompiler:
    """临时节点编译测试。"""

    def test_build_ephemeral_template(self):
        spec = _build_ephemeral_nodespec(
            MFNodeInstance(
                id="ext",
                ephemeral=True,
                description="test",
                ports=EphemeralPorts(
                    inputs=[
                        EphemeralPortDecl(name="I1", type="physical_quantity")
                    ],
                    outputs=[
                        EphemeralPortDecl(name="O1", type="physical_quantity")
                    ],
                ),
            )
        )
        tmpl = _build_ephemeral_template(
            template_name="mf-ext",
            spec=spec,
            script_source="print('hello')",
            input_params=[{"name": "I1"}],
            output_params=[{
                "name": "O1",
                "valueFrom": {"path": "/mf/output/O1"},
            }],
        )
        assert tmpl["name"] == "mf-ext"
        assert tmpl["script"]["image"] == "python:3.11-slim"
        assert tmpl["script"]["source"] == "print('hello')"
        assert tmpl["script"]["command"] == ["python"]
        # 检查环境变量注入
        env_names = {e["name"] for e in tmpl["script"]["env"]}
        assert "MF_OUTPUT_DIR" in env_names
        assert "MF_WORKSPACE_DIR" in env_names
        assert "I1" in env_names
        # 检查 workspace volume
        vol_names = {v["name"] for v in tmpl["volumes"]}
        assert "workspace" in vol_names

    def test_build_ephemeral_template_with_mirror(self):
        spec = _build_ephemeral_nodespec(
            MFNodeInstance(
                id="ext",
                ephemeral=True,
                description="test",
                ports=EphemeralPorts(
                    outputs=[
                        EphemeralPortDecl(name="O1", type="physical_quantity")
                    ],
                ),
            )
        )
        tmpl = _build_ephemeral_template(
            template_name="mf-ext",
            spec=spec,
            script_source="x=1",
            docker_hub_mirror="docker.m.daocloud.io",
            input_params=[],
            output_params=[],
        )
        assert tmpl["script"]["image"] == "docker.m.daocloud.io/library/python:3.11-slim"

    def test_compile_ephemeral_end_to_end(self):
        """端到端编译含临时节点的工作流（需要 mock Agent 调用）。"""
        from unittest.mock import patch

        wf = MFWorkflow(
            name="test-compile",
            nodes=[
                MFNodeInstance(
                    id="geom-input",
                    nodespec_path=(
                        "nodes/chemistry/preprocessing/"
                        "geometry-file-input/nodespec.yaml"
                    ),
                ),
                MFNodeInstance(
                    id="extract",
                    ephemeral=True,
                    description="提取能量",
                    ports=EphemeralPorts(
                        inputs=[
                            EphemeralPortDecl(
                                name="I1", type="physical_quantity"
                            ),
                        ],
                        outputs=[
                            EphemeralPortDecl(
                                name="O1", type="physical_quantity"
                            ),
                        ],
                    ),
                ),
            ],
            connections=[
                MFConnection(
                    **{"from": "geom-input.xyz_geometry", "to": "extract.I1"}
                ),
            ],
        )

        # 构建 resolved_nodes 手动（跳过 validator 的严格连接校验），
        # 因为临时节点的端口类型是泛化的默认值，可能与源端口量纲不完全匹配。
        src_report = validate_workflow(MFWorkflow(
            name="src-only",
            nodes=[
                MFNodeInstance(
                    id="geom-input",
                    nodespec_path=(
                        "nodes/chemistry/preprocessing/"
                        "geometry-file-input/nodespec.yaml"
                    ),
                ),
            ],
        ))
        eph_spec = _build_ephemeral_nodespec(
            MFNodeInstance(
                id="extract",
                ephemeral=True,
                description="提取能量",
                ports=EphemeralPorts(
                    inputs=[
                        EphemeralPortDecl(name="I1", type="physical_quantity")
                    ],
                    outputs=[
                        EphemeralPortDecl(name="O1", type="physical_quantity")
                    ],
                ),
            )
        )
        resolved = dict(src_report.resolved_nodes)
        resolved["extract"] = eph_spec

        # Mock Agent 调用，返回一个简单的 Python 脚本
        mock_script = (
            "import os\n"
            "data = os.environ.get('I1', '')\n"
            "with open('/mf/output/O1', 'w') as f:\n"
            "    f.write(data)\n"
        )

        with patch(
            "workflows.pipeline.compiler._generate_ephemeral_script",
            return_value=mock_script,
        ):
            argo = compile_to_argo(wf, resolved)

        # 检查生成的 templates
        template_names = [t["name"] for t in argo["spec"]["templates"]]
        assert "mf-extract" in template_names

        # 找到临时节点的 template
        extract_tmpl = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "mf-extract"
        )
        assert "script" in extract_tmpl
        assert extract_tmpl["script"]["source"] == mock_script
        assert extract_tmpl["script"]["image"] == "python:3.11-slim"

        # 检查 DAG task
        dag_template = next(
            t for t in argo["spec"]["templates"]
            if t["name"] == "mf-dag"
        )
        dag_tasks = dag_template["dag"]["tasks"]
        extract_task = next(t for t in dag_tasks if t["name"] == "extract")
        assert extract_task["template"] == "mf-extract"
        # 应有依赖 geom-input
        assert "geom-input" in extract_task["depends"]

        # 检查输入参数传递
        params = extract_task["arguments"]["parameters"]
        param_names = {p["name"] for p in params}
        assert "I1" in param_names
