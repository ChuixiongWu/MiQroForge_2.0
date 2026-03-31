"""MiQroForge 2.0 工作流提交管线。

数据流：
    MF Workflow YAML → Loader → Validator → Compiler → Argo YAML → Runner

Public API::

    from workflows.pipeline import (
        # Models
        MFWorkflow, MFNodeInstance, MFConnection,
        ValidationIssue, ValidationReport,
        # Functions
        load_workflow,
        validate_workflow,
        compile_to_argo,
    )
"""

from .models import MFConnection, MFNodeInstance, MFWorkflow
from .validator import ValidationIssue, ValidationReport, validate_workflow
from .loader import load_workflow
from .compiler import compile_to_argo

__all__ = [
    "MFWorkflow",
    "MFNodeInstance",
    "MFConnection",
    "ValidationIssue",
    "ValidationReport",
    "load_workflow",
    "validate_workflow",
    "compile_to_argo",
]
