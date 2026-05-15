"""
P&ID 画板序列化器。

canvas JSON 仅做基本结构校验（顶层键、节点/边数量上限），
具体字段交给前端约定——保持后端对画布形状中立，未来扩展不动后端。
"""
from rest_framework import serializers

from .models import PlantDiagram

# 防止前端误传 / 攻击造成的过大画板。MVP 阶段足够宽松。
_MAX_NODES = 500
_MAX_EDGES = 1000
_ALLOWED_TOP_KEYS = {"version", "viewport", "nodes", "edges"}


def _validate_canvas(value):
    if not isinstance(value, dict):
        raise serializers.ValidationError("canvas 必须是对象")
    # 允许额外字段，但 nodes/edges 类型/数量要约束
    nodes = value.get("nodes", [])
    edges = value.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise serializers.ValidationError("canvas.nodes 和 canvas.edges 必须是数组")
    if len(nodes) > _MAX_NODES:
        raise serializers.ValidationError(f"节点数量不能超过 {_MAX_NODES}")
    if len(edges) > _MAX_EDGES:
        raise serializers.ValidationError(f"连线数量不能超过 {_MAX_EDGES}")
    return value


class PlantDiagramListSerializer(serializers.ModelSerializer):
    """列表/简要场景——不返 canvas，避免列表接口体积膨胀。"""

    node_count = serializers.SerializerMethodField()
    edge_count = serializers.SerializerMethodField()

    class Meta:
        model = PlantDiagram
        fields = [
            "id", "plant_code", "name", "description",
            "is_default", "sort_order",
            "node_count", "edge_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_node_count(self, obj):
        return len(obj.canvas.get("nodes", []) if isinstance(obj.canvas, dict) else [])

    def get_edge_count(self, obj):
        return len(obj.canvas.get("edges", []) if isinstance(obj.canvas, dict) else [])


class PlantDiagramDetailSerializer(serializers.ModelSerializer):
    """详情/创建/更新——含 canvas。"""

    canvas = serializers.JSONField(validators=[_validate_canvas])

    class Meta:
        model = PlantDiagram
        fields = [
            "id", "plant_code", "name", "description",
            "is_default", "sort_order", "canvas",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_plant_code(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("plant_code 不能为空")
        return value.strip().upper()
