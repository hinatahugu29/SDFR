# SDF.R - Blender Add-on
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Copyright (c) 2026 hinata_hugu
# All Rights Reserved.

"""
V17.0.0: Phase G0 (gizmo roadmap) prototype.

パネルの数値入力を置き換えるのではなく、ビューポート上から同じプロパティを
直接ドラッグできる入口を足すだけ。別経路のデータは持たず、ギズモが書き戻すのは
既存の `SDF_ObjectProperties.edge_profile_size` そのもの。

対象プロパティに `edge_profile_size`（フィレット/面取り量）を選んだ理由:
- Blender標準のS(スケール)操作とは独立した値のため、既存のトランスフォームギズモと
  衝突しない。
- これまでプロパティパネルでしか触れず、ビューポートでの直感的操作の恩恵が大きい。

対象シェイプは「角・エッジを持つプリミティブ」だけに絞る(`_EDGE_ROUNDABLE_SHAPES`)。
Sphere/Torus/Capsule/Ellipsoidのように元から角が無いシェイプでは、値を変えても
メッシュに見た目の変化が出ず「ギズモが連動していないように見える」ため除外した。
Math Field / Extrude / Lathe / Bezier Curve は `edge_profile`(あるいは
`edge_profile_size` 自体)を別の意味に流用している(`engine.py` 参照)ため、
誤操作防止のため除外する。

ドラッグ中〜確定後の再計算は、既存の `update_sdf_callback`
(`properties.py` の各 FloatProperty に付与済み) にそのまま乗る。
Phase G1 で予定している「ドラッグ中は軽量プレビュー」のスロットリングは、
このギズモ自体には手を入れず `update_sdf_callback` 側の工夫として扱う想定。
"""

import bpy

# edge_profile_size が見た目の違いとして現れるシェイプだけに絞る。
# properties.py の shape_type EnumProperty のキーと対応させる。
_EDGE_ROUNDABLE_SHAPES = {
    'box', 'rounded_box', 'cylinder', 'hex_prism', 'pyramid',
    'capped_cone', 'ngon_prism', 'rounded_cylinder', 'capped_torus',
    'octahedron', 'cut_sphere',
}


def _active_sdf_primitive(context):
    """ギズモの対象にしてよいアクティブオブジェクトを返す。対象外なら None。"""
    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return None
    props = getattr(obj, "sdf_props", None)
    if props is None or not props.is_primitive:
        return None
    if props.shape_type not in _EDGE_ROUNDABLE_SHAPES:
        return None
    return obj


class SDF_GGT_edge_profile_size(bpy.types.GizmoGroup):
    """アクティブなSDFプリミティブの edge_profile_size をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_edge_profile_size"
    bl_label = "SDF Edge Profile Size Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_sdf_primitive(context) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        gz.color = 0.8, 0.5, 0.1
        gz.color_highlight = 1.0, 0.7, 0.2
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.edge_gizmo = gz

    def refresh(self, context):
        obj = _active_sdf_primitive(context)
        if obj is None:
            return
        gz = self.edge_gizmo
        # ローカルZ上に立てる。原点はオブジェクト原点のまま、回転・位置だけ追従させる。
        gz.matrix_basis = obj.matrix_world.normalized()
        gz.target_set_prop("offset", obj.sdf_props, "edge_profile_size")


classes = (
    SDF_GGT_edge_profile_size,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
