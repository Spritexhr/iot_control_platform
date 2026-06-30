/**
 * 构建 Vue Flow 的 nodeTypes 映射（type -> 节点组件）。
 * 编辑态(DiagramEditor) 与运行态(DiagramRuntime) 共用，保证两边图元一致。
 *
 * - instrument：专用组件（传感器绑定 + 实时取值）
 * - device_indicator：专用组件（设备绑定 + 状态变量）
 * - control_indicator：专用组件（脚本规则 / PI / PID 运行态）
 * - 其余所有图元：统一走通用 SymbolNode，按 type 从 symbols 注册表查几何
 *
 * 新增图元只需在 symbols.js 里加一条，这里会自动注册，无需改动。
 */
import { markRaw } from 'vue'

import InstrumentNode from './nodes/InstrumentNode.vue'
import DeviceIndicatorNode from './nodes/DeviceIndicatorNode.vue'
import ControlIndicatorNode from './nodes/ControlIndicatorNode.vue'
import SymbolNode from './nodes/SymbolNode.vue'
import { SIMPLE_SYMBOLS } from './symbols'

export function buildNodeTypes() {
  const types = {
    instrument: markRaw(InstrumentNode),
    device_indicator: markRaw(DeviceIndicatorNode),
    control_indicator: markRaw(ControlIndicatorNode),
  }
  for (const type of Object.keys(SIMPLE_SYMBOLS)) {
    types[type] = markRaw(SymbolNode)
  }
  return types
}
