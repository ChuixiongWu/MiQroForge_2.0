"""用量追踪 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TokenUsageSummary(BaseModel):
    period_days: int = 30
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    by_model: dict[str, dict] = Field(default_factory=dict)
    by_purpose: dict[str, dict] = Field(default_factory=dict)
    by_day: list[dict] = Field(default_factory=list)
    estimated_cost: float = 0.0


class ComputeUsageSummary(BaseModel):
    period_days: int = 30
    total_core_hours: float = 0.0
    total_gpu_hours: float = 0.0
    total_workflows: int = 0
    by_project: dict[str, dict] = Field(default_factory=dict)
    by_day: list[dict] = Field(default_factory=list)
    estimated_cost: float = 0.0


class BillingRates(BaseModel):
    llm_per_1k_input_tokens: dict[str, float] = Field(default_factory=dict)
    llm_per_1k_output_tokens: dict[str, float] = Field(default_factory=dict)
    compute_per_core_hour: float = 0.05
    compute_per_gpu_hour: float = 0.50
