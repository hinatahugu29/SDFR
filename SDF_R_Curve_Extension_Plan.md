# SDF.R V16拡張計画: カーブ・押し出し・回転体の実装構想

将来的なメジャーアップデート（V16等）に向けた、SDFの表現力を劇的に拡張する新機能の実装計画書です。
※本計画は構想および設計のPoC（概念実証）であり、直ちには実装されません。

## 1. 概要 (Goal Description)

海外からの要望にもあった「押し出し（Extrude）」「回転体（Lathe）」「カーブ（Curves）」を、現在のSDF.Rのアーキテクチャ（WGSL + Rustコア）の枠組み内で効率的に実装するための道筋を定義します。
今回は「レベル1：数学的な基本カーブ」および「シンプルな2D形状の3D化」にスコープを絞り、既存の固定サイズデータ構造（`GpuPrimitive`）を維持したまま最小限の変更で最大の効果を得るアプローチをとります。

> [!NOTE]
> 任意のBlenderカーブオブジェクトをそのままSDF化する機能（レベル2）は、可変長配列を扱うSSBO（Shader Storage Buffer Object）の増設など抜本的なアーキテクチャ改修が必要になるため、本計画の次のフェーズとします。

## 2. 提案する変更内容 (Proposed Changes)

### 2.1 WGSL層 (Shader / GPU 計算)

GPUでの並列計算において、数学的に軽量な関数を追加します。

*   **[NEW] 2D SDF関数の基盤追加**
    *   `sdBox2D`, `sdCircle2D`, `sdHexagon2D`, `sdStar2D` など、XY平面上で評価される2D距離関数群を新設します。
*   **[NEW] 押し出し (Extrude) 演算子**
    *   2DのSDF距離 $d_{2d}$ と、Z軸方向の厚み $h$ を受け取り、3Dの距離を返す関数 `opExtrude` を実装します。
    *   数式: `vec2 w = vec2(d_2d, abs(p.z) - h); return min(max(w.x, w.y), 0.0) + length(max(w, 0.0));`
*   **[NEW] 回転体 (Lathe / Revolution) 演算子**
    *   Y軸を中心に、2Dプロファイルを回転させて立体化する関数 `opLathe` を実装します。
    *   数式: `vec2 q = vec2(length(p.xz) - offset, p.y); return d_2d(q);`
*   **[NEW] 数学的基本カーブ (Quadratic Bezier)**
    *   3つの制御点（始点A、中間点B、終点C）で定義される2次ベジェ曲線のパイプ化関数 `sdBezier` を実装します。

### 2.2 Rust層 (Core Engine)

WGSLにデータを渡すためのシリアライズ層の拡張を行います。

*   **[MODIFY] `shape_type` IDの拡張**
    *   `src/primitive.rs` および `sdf.rs` の列挙型に、新しい形状IDを割り当てます。
    *   例: `ExtrudedShape = 15`, `LathedShape = 16`, `BezierCurve = 17`
*   **[MODIFY] パラメータパッキング (`GpuPrimitive`)**
    *   現在の `extra_params[4]` (f32が4つ) に収めるための工夫を行います。
    *   **Bezierの場合**: 3点×3D座標＝9個のf32が必要ですが、A点をローカル原点(0,0,0)に固定し、厚み(1)、B点(3)、C点(3)とすれば計7個。`size`ベクトル(3)と`extra_params`(4)を流用して格納する等のパッキング設計を適用します。
    *   **Extrude/Latheの場合**: ベースとなる2D形状のIDや、厚み・オフセットなどを `extra_params` に格納します。

### 2.3 Python層 (UI & Data Management)

ユーザーがBlender上で操作するためのUIとバウンディングボックス計算を追加します。

*   **[MODIFY] `properties.py`**
    *   `shape_type` (Enum) に新機能を追加。
    *   `bezier_point_b`, `bezier_point_c`, `extrude_depth`, `lathe_offset` などの専用プロパティを新設。
*   **[MODIFY] `ui.py`**
    *   選択された `shape_type` に応じて、Extrude/Lathe用の2D形状選択リストや、Bezierのコントロールポイント入力フィールド（X/Y/Z）を表示するレイアウトを追加。
*   **[MODIFY] `engine.py` / `handlers.py`**
    *   ドメイン自動拡張のためのAABB（バウンディングボックス）最大半径計算に、新形状の計算ロジックを追加。
    *   ベジェ曲線の場合は、3点が含まれるAABBの計算式を適用。

---

## 3. 実装の利点と今後の展望

**圧倒的な表現力の向上**
単純な球や立方体の組み合わせから、花瓶のような回転体、ロゴマークのような押し出し、チューブ状のベジェ曲線が加わることで、機械的・有機的問わず作れるものの幅が格段に広がります。

**パフォーマンスへの影響**
今回のアプローチは、すべて数学的（Analytical）なSDF関数で解決するため、既存のパフォーマンス（超高速レイマーチングおよびメッシュ生成）を一切犠牲にしません。

この計画書をベースとしておくことで、将来的なタイミングでいつでも実装フェーズ（Execution）へ移行することが可能です。
