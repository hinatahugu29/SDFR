# SDF.R - Blender Add-on
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Copyright (c) 2026 hinata_hugu
# All Rights Reserved.

"""
V17.0.0: Phase G0/G2 (gizmo roadmap) prototypes.

パネルの数値入力を置き換えるのではなく、ビューポート上から同じプロパティを
直接ドラッグできる入口を足すだけ。別経路のデータは持たず、ギズモが書き戻すのは
既存の `SDF_ObjectProperties` のプロパティそのもの。対象プロパティ・対象シェイプの
選定理由は GIZMO_ROADMAP.md の「Boxケーススタディ」節を参照。

ドラッグ中〜確定後の再計算は、既存の `update_sdf_callback`
(`properties.py` の各 FloatProperty に付与済み) にそのまま乗る。
Phase G1 で予定している「ドラッグ中は軽量プレビュー」のスロットリングは、
このギズモ自体には手を入れず `update_sdf_callback` 側の工夫として扱う想定。
"""

import math

import bpy
from mathutils import Matrix, Vector

# edge_profile_size が見た目の違いとして現れるシェイプだけに絞る。
# properties.py の shape_type EnumProperty のキーと対応させる。
# Sphere/Torus/Capsule/Ellipsoidのように元から角が無いシェイプでは、値を変えても
# メッシュに見た目の変化が出ず「ギズモが連動していないように見える」ため除外。
# Math Field / Extrude / Lathe / Bezier Curve は edge_profile(あるいは
# edge_profile_size 自体)を別の意味に流用している(engine.py 参照)ため除外。
_EDGE_ROUNDABLE_SHAPES = {
    'box', 'rounded_box', 'cylinder', 'hex_prism', 'pyramid',
    'capped_cone', 'ngon_prism', 'rounded_cylinder', 'capped_torus',
    'octahedron', 'cut_sphere',
}

# shell_thickness は「閉じた立体を中空にする」値で、角の有無に関係なく
# Sphere/Torus/Capsule等の滑らかな形状にも見た目の効果が出る
# (engine.py 側でもシェイプ別の再割り当ては行われていない、通常の意味のまま使われる)。
# Math Field / Extrude / Lathe / Bezier Curve は2Dプロファイル由来の特殊な形状で
# shell_thicknessとの組み合わせを未検証のため、edge_profile_sizeと同様に除外しておく。
_SHELL_CAPABLE_SHAPES = {
    'sphere', 'box', 'rounded_box', 'torus', 'cylinder', 'capsule',
    'hex_prism', 'pyramid', 'capped_cone', 'ngon_prism', 'ellipsoid',
    'rounded_cylinder', 'capped_torus', 'octahedron', 'cut_sphere',
}

# smoothness(他プリミティブとブーリアンでブレンドするときの滑らかさ)は engine.py で
# シェイプ別の再割り当てが一切無く(どのshape_typeでも同じ意味で使われる)、全シェイプで安全。
# ただし効果が「このプリミティブが他と重なって混ざる場所」にしか出ないため、単独1個だけでは
# 値を変えても見た目が変化しない(edge_profile_sizeでSphereを対象にした時と同種の落とし穴)。
# 対象シェイプそのものは制限不要だが、検証は2プリミティブ以上が重なった状態で行うこと。
_ALL_PRIMITIVE_SHAPES = {
    'sphere', 'box', 'rounded_box', 'torus', 'cylinder', 'capsule',
    'hex_prism', 'pyramid', 'capped_cone', 'ngon_prism', 'ellipsoid',
    'rounded_cylinder', 'capped_torus', 'octahedron', 'cut_sphere',
    'math_field', 'extrude', 'lathe', 'bezier_curve',
}

_DOWN_ROTATION = Matrix.Rotation(math.pi, 4, 'X')
_SIDE_ROTATION = Matrix.Rotation(math.pi / 2.0, 4, 'Y')          # +X
_NEG_SIDE_ROTATION = Matrix.Rotation(-math.pi / 2.0, 4, 'Y')     # -X
_POS_Y_ROTATION = Matrix.Rotation(-math.pi / 2.0, 4, 'X')        # +Y
_NEG_Y_ROTATION = Matrix.Rotation(math.pi / 2.0, 4, 'X')         # -Y

# Torus固有パラメータ(p1/p2)専用。p1/p2 は SDF_ObjectProperties の汎用スロットで、
# 意味はシェイプごとに違う(Cylinderならp1=Radius/p2=Height(Half)など)ため、
# 「p1用の汎用ギズモ」は作れず、shape_type == 'torus' に限定した専用ギズモにする。
_TORUS_SHAPES = {'torus'}

# Cylinder固有パラメータ(p1/p2)専用。Torusと同じ理由でshape_type限定にする。
_CYLINDER_SHAPES = {'cylinder'}

# Capped Cone固有パラメータ(p1/p2/p3)専用。
_CAPPED_CONE_SHAPES = {'capped_cone'}

# Ellipsoid固有パラメータ(p1/p2/p3 = Radius X/Y/Z)専用。
_ELLIPSOID_SHAPES = {'ellipsoid'}


def _active_primitive_for(context, allowed_shapes):
    """ギズモの対象にしてよいアクティブオブジェクトを返す。対象外なら None。"""
    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return None
    props = getattr(obj, "sdf_props", None)
    if props is None or not props.is_primitive:
        return None
    if props.shape_type not in allowed_shapes:
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
        return _active_primitive_for(context, _EDGE_ROUNDABLE_SHAPES) is not None

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
        obj = _active_primitive_for(context, _EDGE_ROUNDABLE_SHAPES)
        if obj is None:
            return
        gz = self.edge_gizmo
        # ローカル+Z上に立てる。原点はオブジェクト原点のまま、回転・位置だけ追従させる。
        gz.matrix_basis = obj.matrix_world.normalized()
        gz.target_set_prop("offset", obj.sdf_props, "edge_profile_size")


class SDF_GGT_shell_thickness(bpy.types.GizmoGroup):
    """アクティブなSDFプリミティブの shell_thickness をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_shell_thickness"
    bl_label = "SDF Shell Thickness Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _SHELL_CAPABLE_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        # edge_profile_size のオレンジ矢印(+Z, 上向き)と見分けがつくよう、
        # 色と向きの両方を変える(シアン, -Z=下向き)。
        gz.color = 0.1, 0.6, 0.8
        gz.color_highlight = 0.2, 0.8, 1.0
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.shell_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _SHELL_CAPABLE_SHAPES)
        if obj is None:
            return
        gz = self.shell_gizmo
        # ローカル-Zへ向ける(内向きオフセットの比喩)。原点はオブジェクト原点のまま。
        gz.matrix_basis = obj.matrix_world.normalized() @ _DOWN_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "shell_thickness")


class SDF_GGT_smoothness(bpy.types.GizmoGroup):
    """アクティブなSDFプリミティブの smoothness をビューポートでドラッグする。

    効果は他プリミティブとのブーリアンブレンド箇所にしか出ないため、単独表示では
    見た目の変化が無いことがある(値自体は正しく書き換わる)。
    """
    bl_idname = "SDF_GGT_smoothness"
    bl_label = "SDF Smoothness Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _ALL_PRIMITIVE_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        # edge_profile_size(+Z, オレンジ) / shell_thickness(-Z, シアン)と見分けがつくよう、
        # 3本目は+X・マゼンタにする。
        gz.color = 0.8, 0.2, 0.7
        gz.color_highlight = 1.0, 0.3, 0.9
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.smoothness_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _ALL_PRIMITIVE_SHAPES)
        if obj is None:
            return
        gz = self.smoothness_gizmo
        # ローカル+Xへ向ける。原点はオブジェクト原点のまま。
        gz.matrix_basis = obj.matrix_world.normalized() @ _SIDE_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "smoothness")


class SDF_OT_gizmo_set_operation(bpy.types.Operator):
    """ビューポートのボタン型ギズモから sdf_props.operation を設定する。

    ドラッグ系ギズモ(target_set_prop)と違い、列挙値の切り替えは
    target_set_operator 経由でオペレーターを1回実行する形になる。
    """
    bl_idname = "sdf.gizmo_set_operation"
    bl_label = "Set SDF Operation"
    bl_description = "Switch this primitive's boolean operation (Union / Subtract / Intersect)"
    bl_options = {'REGISTER', 'UNDO'}

    value: bpy.props.EnumProperty(
        items=[('0', "Union", ""), ('1', "Subtract", ""), ('2', "Intersect", "")],
        name="Operation",
    )

    def execute(self, context):
        obj = context.active_object
        if obj is None or not getattr(obj, "sdf_props", None):
            return {'CANCELLED'}
        obj.sdf_props.operation = self.value
        return {'FINISHED'}


# ボタン1個につき (enum値, 色, ローカル座標でのオフセット) を割り当てる。
# +Xに沿って3個並べる。選択中の値は refresh() で明るい色にする。
_OPERATION_BUTTONS = (
    ('0', (0.2, 0.6, 0.9), (0.9, 1.2, 0.0)),   # Union: 青系
    ('1', (0.9, 0.3, 0.2), (0.9, 1.5, 0.0)),   # Subtract: 赤系
    ('2', (0.3, 0.8, 0.3), (0.9, 1.8, 0.0)),   # Intersect: 緑系
)


class SDF_GGT_operation_switch(bpy.types.GizmoGroup):
    """アクティブなSDFプリミティブの operation をビューポートのボタンで切り替える。

    スイッチ的操作の最初のプロトタイプ。ドラッグ系ギズモ(矢印)とは別の仕組みで、
    GIZMO_GT_button_2d + target_set_operator を使う。見た目は「選択肢の数だけ
    ボタンを並べる」方式(ユーザー確認済み)。
    """
    bl_idname = "SDF_GGT_operation_switch"
    bl_label = "SDF Operation Switch Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _ALL_PRIMITIVE_SHAPES) is not None

    def setup(self, context):
        self.buttons = []
        for value, color, offset in _OPERATION_BUTTONS:
            gz = self.gizmos.new("GIZMO_GT_button_2d")
            gz.icon = 'NONE'
            gz.draw_options = {'BACKDROP', 'OUTLINE'}
            gz.color = color
            gz.color_highlight = tuple(min(1.0, c + 0.2) for c in color)
            gz.alpha = 0.6
            gz.alpha_highlight = 1.0
            gz.scale_basis = 0.12
            props = gz.target_set_operator(SDF_OT_gizmo_set_operation.bl_idname)
            props.value = value
            self.buttons.append((gz, value, Vector(offset)))

    def refresh(self, context):
        obj = _active_primitive_for(context, _ALL_PRIMITIVE_SHAPES)
        if obj is None:
            return
        current = obj.sdf_props.operation
        base = obj.matrix_world.normalized()
        for gz, value, offset in self.buttons:
            m = base.copy()
            m.translation = base @ offset
            gz.matrix_basis = m
            # 選択中の値だけ不透明度を上げて、今どれが効いているか分かるようにする。
            gz.alpha = 1.0 if value == current else 0.45


class SDF_OT_gizmo_set_edge_profile(bpy.types.Operator):
    """ビューポートのボタン型ギズモから sdf_props.edge_profile を設定する。"""
    bl_idname = "sdf.gizmo_set_edge_profile"
    bl_label = "Set SDF Edge Profile"
    bl_description = "Switch this primitive's edge/corner profile (Round / Sharp / Soft / Tight / Chamfer)"
    bl_options = {'REGISTER', 'UNDO'}

    value: bpy.props.EnumProperty(
        items=[
            ('0', "Round", ""), ('1', "Sharp", ""), ('2', "Soft", ""),
            ('3', "Tight", ""), ('4', "Chamfer", ""),
        ],
        name="Edge Profile",
    )

    def execute(self, context):
        obj = context.active_object
        if obj is None or not getattr(obj, "sdf_props", None):
            return {'CANCELLED'}
        obj.sdf_props.edge_profile = self.value
        return {'FINISHED'}


# operation(3択)は+X側に1段で並べたので、edge_profile(5択)は反対の-X側に2段で並べ、
# 見た目でも重ならないようにする。上段3個・下段2個、上段の隙間の下に下段が来るよう
# Yをずらして互い違いに配置する。
# (enum値, 色, ローカル座標でのオフセット)
_EDGE_PROFILE_BUTTONS = (
    ('0', (0.75, 0.75, 0.75), (-0.9, 1.2, 0.25)),   # Round:  グレー / 上段
    ('1', (0.95, 0.85, 0.2), (-0.9, 1.5, 0.25)),    # Sharp:  黄系   / 上段
    ('2', (0.5, 0.75, 0.95), (-0.9, 1.8, 0.25)),    # Soft:   水色   / 上段
    ('3', (0.9, 0.55, 0.15), (-0.9, 1.35, -0.25)),  # Tight:  橙系   / 下段
    ('4', (0.65, 0.35, 0.85), (-0.9, 1.65, -0.25)), # Chamfer: 紫系  / 下段
)


class SDF_GGT_edge_profile_switch(bpy.types.GizmoGroup):
    """アクティブなSDFプリミティブの edge_profile を、2段に並べたボタンで切り替える。

    operation(3択・1段)と同じ仕組みだが、5択を1段に並べると窮屈になるため
    上段3個・下段2個の2段レイアウトにしている。対象シェイプは edge_profile_size と
    同じ許可リスト(角を持つプリミティブのみ)を使う — edge_profile自体が
    Math Field 等では別目的に流用されているため。
    """
    bl_idname = "SDF_GGT_edge_profile_switch"
    bl_label = "SDF Edge Profile Switch Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _EDGE_ROUNDABLE_SHAPES) is not None

    def setup(self, context):
        self.buttons = []
        for value, color, offset in _EDGE_PROFILE_BUTTONS:
            gz = self.gizmos.new("GIZMO_GT_button_2d")
            gz.icon = 'NONE'
            gz.draw_options = {'BACKDROP', 'OUTLINE'}
            gz.color = color
            gz.color_highlight = tuple(min(1.0, c + 0.2) for c in color)
            gz.alpha = 0.6
            gz.alpha_highlight = 1.0
            gz.scale_basis = 0.1
            props = gz.target_set_operator(SDF_OT_gizmo_set_edge_profile.bl_idname)
            props.value = value
            self.buttons.append((gz, value, Vector(offset)))

    def refresh(self, context):
        obj = _active_primitive_for(context, _EDGE_ROUNDABLE_SHAPES)
        if obj is None:
            return
        current = obj.sdf_props.edge_profile
        base = obj.matrix_world.normalized()
        for gz, value, offset in self.buttons:
            m = base.copy()
            m.translation = base @ offset
            gz.matrix_basis = m
            gz.alpha = 1.0 if value == current else 0.45


class SDF_GGT_torus_main_radius(bpy.types.GizmoGroup):
    """Torusの p1(Main Radius: 輪の大きさ)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_torus_main_radius"
    bl_label = "SDF Torus Main Radius Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _TORUS_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        # 既存の+Z(edge_profile_size)/-Z(shell_thickness)/+X(smoothness)とは別の
        # 軸・色にする(+Y・黄色)。これらは同時に出うる組み合わせのため衝突を避ける。
        gz.color = 0.85, 0.8, 0.15
        gz.color_highlight = 1.0, 0.95, 0.2
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.main_radius_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _TORUS_SHAPES)
        if obj is None:
            return
        gz = self.main_radius_gizmo
        gz.matrix_basis = obj.matrix_world.normalized() @ _POS_Y_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "p1")


class SDF_GGT_torus_pipe_radius(bpy.types.GizmoGroup):
    """Torusの p2(Pipe Radius: 管の太さ)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_torus_pipe_radius"
    bl_label = "SDF Torus Pipe Radius Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _TORUS_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        # Main Radius(+Y・黄色)と対になる-Y・ティール系にする。
        gz.color = 0.15, 0.8, 0.55
        gz.color_highlight = 0.2, 1.0, 0.7
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.pipe_radius_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _TORUS_SHAPES)
        if obj is None:
            return
        gz = self.pipe_radius_gizmo
        gz.matrix_basis = obj.matrix_world.normalized() @ _NEG_Y_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "p2")


class SDF_GGT_cylinder_radius(bpy.types.GizmoGroup):
    """Cylinderの p1(Radius)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_cylinder_radius"
    bl_label = "SDF Cylinder Radius Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _CYLINDER_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        # Torusの+Y(黄)/-Y(ティール)とは別の色にする(Cylinderは同じ+Y/-Y軸を使うが
        # 同時に表示されることはない=shape_typeが排他なので、軸の使い回し自体は問題ない)。
        gz.color = 0.3, 0.35, 0.95
        gz.color_highlight = 0.4, 0.45, 1.0
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.radius_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _CYLINDER_SHAPES)
        if obj is None:
            return
        gz = self.radius_gizmo
        gz.matrix_basis = obj.matrix_world.normalized() @ _POS_Y_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "p1")


class SDF_GGT_cylinder_height(bpy.types.GizmoGroup):
    """Cylinderの p2(Height / Half)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_cylinder_height"
    bl_label = "SDF Cylinder Height Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _CYLINDER_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        gz.color = 0.55, 0.9, 0.2
        gz.color_highlight = 0.65, 1.0, 0.3
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.height_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _CYLINDER_SHAPES)
        if obj is None:
            return
        gz = self.height_gizmo
        gz.matrix_basis = obj.matrix_world.normalized() @ _NEG_Y_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "p2")


class SDF_GGT_capped_cone_bottom_radius(bpy.types.GizmoGroup):
    """Capped Coneの p1(Bottom Radius)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_capped_cone_bottom_radius"
    bl_label = "SDF Capped Cone Bottom Radius Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _CAPPED_CONE_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        # Bottom/Topを同系色の濃淡で区別する(濃い方=Bottom)。+Y/-Y/-Xは
        # Torus/Cylinder/Ellipsoidが使う軸だが、shape_typeが排他なので衝突しない。
        gz.color = 0.7, 0.5, 0.3
        gz.color_highlight = 0.85, 0.65, 0.4
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.bottom_radius_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _CAPPED_CONE_SHAPES)
        if obj is None:
            return
        gz = self.bottom_radius_gizmo
        gz.matrix_basis = obj.matrix_world.normalized() @ _POS_Y_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "p1")


class SDF_GGT_capped_cone_top_radius(bpy.types.GizmoGroup):
    """Capped Coneの p2(Top Radius)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_capped_cone_top_radius"
    bl_label = "SDF Capped Cone Top Radius Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _CAPPED_CONE_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        gz.color = 0.9, 0.78, 0.6   # Bottomより明るい色=Top
        gz.color_highlight = 1.0, 0.9, 0.75
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.top_radius_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _CAPPED_CONE_SHAPES)
        if obj is None:
            return
        gz = self.top_radius_gizmo
        gz.matrix_basis = obj.matrix_world.normalized() @ _NEG_Y_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "p2")


class SDF_GGT_capped_cone_height(bpy.types.GizmoGroup):
    """Capped Coneの p3(Height)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_capped_cone_height"
    bl_label = "SDF Capped Cone Height Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _CAPPED_CONE_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        # +Xはsmoothness(全シェイプ共通)が使っているため、3本目は-Xにする。
        gz.color = 0.4, 0.55, 0.65
        gz.color_highlight = 0.5, 0.68, 0.8
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.height_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _CAPPED_CONE_SHAPES)
        if obj is None:
            return
        gz = self.height_gizmo
        gz.matrix_basis = obj.matrix_world.normalized() @ _NEG_SIDE_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "p3")


class SDF_GGT_ellipsoid_radius_x(bpy.types.GizmoGroup):
    """Ellipsoidの p1(Radius X)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_ellipsoid_radius_x"
    bl_label = "SDF Ellipsoid Radius X Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _ELLIPSOID_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        # Blenderの軸配色(X=赤/Y=緑/Z=青)に合わせる。ローカル軸そのものに
        # 対応する3値なので、他のギズモの配色慣習より軸の色分けを優先する。
        # +Xはsmoothnessが占有しているため-X側に出す(値はp1のまま、符号の
        # 向きが変わるだけ)。
        gz.color = 0.85, 0.2, 0.2
        gz.color_highlight = 1.0, 0.3, 0.3
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.radius_x_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _ELLIPSOID_SHAPES)
        if obj is None:
            return
        gz = self.radius_x_gizmo
        gz.matrix_basis = obj.matrix_world.normalized() @ _NEG_SIDE_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "p1")


class SDF_GGT_ellipsoid_radius_y(bpy.types.GizmoGroup):
    """Ellipsoidの p2(Radius Y)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_ellipsoid_radius_y"
    bl_label = "SDF Ellipsoid Radius Y Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _ELLIPSOID_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        gz.color = 0.25, 0.8, 0.25
        gz.color_highlight = 0.35, 1.0, 0.35
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.radius_y_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _ELLIPSOID_SHAPES)
        if obj is None:
            return
        gz = self.radius_y_gizmo
        gz.matrix_basis = obj.matrix_world.normalized() @ _POS_Y_ROTATION
        gz.target_set_prop("offset", obj.sdf_props, "p2")


class SDF_GGT_ellipsoid_radius_z(bpy.types.GizmoGroup):
    """Ellipsoidの p3(Radius Z)をビューポートでドラッグする。"""
    bl_idname = "SDF_GGT_ellipsoid_radius_z"
    bl_label = "SDF Ellipsoid Radius Z Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return _active_primitive_for(context, _ELLIPSOID_SHAPES) is not None

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.draw_style = 'BOX'
        gz.color = 0.25, 0.45, 0.9
        gz.color_highlight = 0.35, 0.55, 1.0
        gz.alpha = 0.8
        gz.alpha_highlight = 1.0
        gz.length = 1.5
        gz.use_draw_modal = True
        self.radius_z_gizmo = gz

    def refresh(self, context):
        obj = _active_primitive_for(context, _ELLIPSOID_SHAPES)
        if obj is None:
            return
        gz = self.radius_z_gizmo
        # +Zはedge_profile_sizeが使う軸だが、Ellipsoidはそもそも対象外シェイプなので
        # 同時表示されず衝突しない。ellipsoidはshell_thicknessで-Zを使っているため、
        # Radius Zは+Z側(通常のedge_profile_size方向=角丸めの意味は無い)に出す。
        gz.matrix_basis = obj.matrix_world.normalized()
        gz.target_set_prop("offset", obj.sdf_props, "p3")


classes = (
    SDF_GGT_edge_profile_size,
    SDF_GGT_shell_thickness,
    SDF_GGT_smoothness,
    SDF_OT_gizmo_set_operation,
    SDF_GGT_operation_switch,
    SDF_OT_gizmo_set_edge_profile,
    SDF_GGT_edge_profile_switch,
    SDF_GGT_torus_main_radius,
    SDF_GGT_torus_pipe_radius,
    SDF_GGT_cylinder_radius,
    SDF_GGT_cylinder_height,
    SDF_GGT_capped_cone_bottom_radius,
    SDF_GGT_capped_cone_top_radius,
    SDF_GGT_capped_cone_height,
    SDF_GGT_ellipsoid_radius_x,
    SDF_GGT_ellipsoid_radius_y,
    SDF_GGT_ellipsoid_radius_z,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
