<script>
/**
 * 把图元几何数组 draw 渲染成 SVG。工具箱预览和画布节点共用同一渲染逻辑。
 * 用 render 函数（h）创建子元素，确保 SVG 命名空间正确（动态 :is 在 SVG 下不可靠）。
 */
import { h } from 'vue'

const FILL_ELEMENTS = new Set(['rect', 'circle', 'ellipse', 'polygon', 'path'])

function buildAttrs(item) {
  const { el, sw, fill, stroke, text, anchor, size, ...rest } = item
  const attrs = { ...rest }
  attrs.stroke = stroke ?? '#2a2a2a'
  attrs['stroke-width'] = sw ?? (FILL_ELEMENTS.has(el) ? 1.5 : 1)
  if (el === 'text') {
    attrs.fill = fill ?? '#2a2a2a'
    attrs.stroke = 'none'
    if (anchor) attrs['text-anchor'] = anchor
    if (size) attrs['font-size'] = size
  } else if (FILL_ELEMENTS.has(el)) {
    attrs.fill = fill ?? '#fff'
  } else {
    attrs.fill = fill ?? 'none'
  }
  return attrs
}

export default {
  name: 'SymbolGlyph',
  props: {
    viewBox: { type: String, required: true },
    draw: { type: Array, default: () => [] },
    preserveAspectRatio: { type: String, default: 'xMidYMid meet' },
  },
  setup(props) {
    return () =>
      h(
        'svg',
        {
          viewBox: props.viewBox,
          preserveAspectRatio: props.preserveAspectRatio,
          class: 'symbol-glyph',
        },
        props.draw.map((item) => h(item.el, buildAttrs(item), item.text ?? null)),
      )
  },
}
</script>

<style scoped>
.symbol-glyph {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
