/**
 * lib/node-utils.ts — 节点数据构建工具
 *
 * 从 API 返回的 NodeDetailResponse 构建 MFNodeData，
 * WorkflowCanvas 和 ChatPanel 共用。
 */

import type { NodeDetailResponse } from '../types/index-types'
import type { MFNodeData } from '../stores/workflow-store'

export function buildNodeData(detail: NodeDetailResponse): MFNodeData {
  return {
    name: detail.name,
    version: detail.version,
    display_name: detail.display_name,
    description: detail.description,
    node_type: detail.node_type,
    category: detail.category,
    software: detail.software,
    nodespec_path: detail.nodespec_path,
    stream_inputs: detail.stream_inputs.map((p) => ({
      name: p.name,
      display_name: p.display_name,
      category: p.category,
      detail: p.detail,
    })),
    stream_outputs: detail.stream_outputs.map((p) => ({
      name: p.name,
      display_name: p.display_name,
      category: p.category,
      detail: p.detail,
    })),
    onboard_inputs: detail.onboard_inputs.map((p) => ({
      name: p.name,
      display_name: p.display_name,
      type: p.kind,
      default: p.default,
      description: p.description,
      enum_values: p.allowed_values,
      min: p.min_value,
      max: p.max_value,
      unit: p.unit,
      multiple_input: p.multiple_input,
      resource_param: p.resource_param,
    })),
    onboard_outputs: (detail.onboard_outputs ?? []).map((o) => ({
      name: o.name,
      display_name: o.display_name,
      kind: o.kind,
      unit: o.unit,
      description: o.description,
      quality_gate: o.quality_gate,
      gate_default: o.gate_default,
      gate_description: o.gate_description,
    })),
    onboard_params: Object.fromEntries(
      detail.onboard_inputs
        .filter((p) => p.default !== undefined && p.default !== null)
        .map((p) => [p.name, p.default]),
    ),
    resources: {
      cpu: detail.resources_cpu ?? 0,
      mem_gb: detail.resources_mem_gb ?? 0,
      mem_overhead: Math.max(0, (detail.resources_memory_gb ?? 0) - (detail.resources_mem_gb ?? 0)),
      gpu: detail.resources_gpu ?? 0,
      estimated_walltime_hours: detail.resources_walltime_hours ?? 0,
      scratch_disk_gb: detail.resources_scratch_disk_gb ?? 0,
      parallel_tasks: detail.resources_parallel_tasks ?? 1,
    },
  }
}
