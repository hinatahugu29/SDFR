# SDF.R V16.0.7 UI / Command Inventory

対象: **Rust-GPU-SDF / SDF.R V16.0.7** \| 作成日: 2026-07-19 \| 用途: UIボタン・主要コントロールの棚卸し資料


**再計算の読み方:** Mesh再計算 はSDFを再評価して結果メッシュを作り直す操作、 軽量更新 は既存メッシュ属性や表示だけを更新する操作、 表示/管理 は主にUI・選択・表示・管理の操作です。



**色まわりの重要整理:** `Apply Color All` は全体一色化なので軽量更新できます。一方、Stack上の色チップや個別 `Color` はカラーブレンディングに関わるため、正しい境界色を保つにはMesh再計算が必要です。


## 1. Header / Status

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Live Update | トグル | パラメータ変更やTransform変更を結果メッシュへ自動反映する。 | 表示/管理 | ON時は多くの編集操作で自動的にMesh再計算が走る。重い作業では一時OFFも有効。 |
| Mesh icon | トグル | 結果メッシュ `SDF_Result` の表示/生成系ワークフローを切り替える。 | 表示/管理 | OFF時はGhost Preview中心の軽量編集に向く。 |
| Wire/BBox icon | トグル | SDFプリミティブの表示をWireまたはBounds系表示へ切り替える。 | 表示/管理 | ソースオブジェクトの見え方だけを変える。 |
| Ghost icon | トグル | GPU Ghost Previewの表示を切り替える。 | 表示/管理 | メッシュ化前のリアルタイムプレビュー用。 |
| GPU: Ready / Updating | 状態表示 | Rust/GPUエンジンの状態を表示する。 | 表示/管理 | Updating中はメッシュ生成処理が進行中。 |
| New SDF Workspace | ボタン `sdf.make_output` | 新しい `SDF_Collection` と `SDF_Result` を作成する。既存作業があれば履歴側へ退避する。 | Mesh再計算 | ワークスペース開始ボタン。初回はここから。 |

## 2. Engine Diagnostics

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Engine Diagnostics | 展開トグル | エンジン状態、ログパス、直近メッシュ診断、Backend、Resolutionを表示する。 | 表示/管理 | 問題調査時の最初の確認場所。 |
| Perf | 診断トグル | パフォーマンスログを出力する。 | 表示/管理 | `SDF_PERF_LOG.ON` を使う診断系。 |
| Mesh | 診断トグル | メッシュ生成デバッグログを出力する。 | 表示/管理 | Rust Debugログ確認に使う。 |
| Layout | 診断トグル | Layout展開やCollection Divider関連のログを出す。 | 表示/管理 | Mirror/Radial/Grid/Layer Boundary調査向け。 |

## 3. Output & Quality

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Low / High | ボタン `sdf.set_resolution_preset` | Resolutionを低/高プリセットへ切り替える。 | Mesh再計算 | High切替時、設定によりLive Normalsを自動ON。 |
| L-Val / H-Val | 数値 | Low/Highボタンで使うResolution値を設定する。 | 表示/管理 | 値の保存のみ。実際の切替はLow/Highボタン。 |
| Res | 数値 | SDFグリッド解像度を設定する。 | Mesh再計算 | 品質と処理負荷の中心パラメータ。 |
| Domain | 数値 | SDF計算領域の大きさを設定する。 | Mesh再計算 | 形が欠ける場合は広げる。Auto Domain ONなら自動調整される。 |
| Auto Domain | トグル | スタック内の形状に合わせて計算領域を自動拡張する。 | Mesh再計算 | 通常ON推奨。 |
| Preview Quality | 選択 | Ghost Previewの品質を Low / Mid / High から選ぶ。 | 表示/管理 | メッシュ品質ではなくPreview側の負荷と見た目。 |
| Symmetry X/Y/Z | トグル | 指定軸でSDF計算を対称化する。 | Mesh再計算 | Mirror Layoutとは別の計算対称。 |
| Marching Cubes | ボタン `sdf.switch_algo` | メッシュ生成方式をMCに切り替える。 | Mesh再計算 | 滑らか・有機的な形状向け。 |
| Dual Contouring | ボタン `sdf.switch_algo` | メッシュ生成方式をDCに切り替える。 | Mesh再計算 | 硬いエッジ向け。初回はDCパイプラインのコンパイルが走る場合がある。 |
| Backend | 選択 | 通常/Chunked系などメッシュ生成バックエンドを選ぶ。 | Mesh再計算 | 高解像度・大規模メッシュ時の安定性に関わる。 |
| Chunk / Seam / From | 数値 | Chunked生成の分割サイズ、継ぎ目Weld、開始解像度を調整する。 | Mesh再計算 | 高解像度時の救済・安定化用。 |
| Weld (Merge) | トグル | 生成メッシュの近接頂点を統合する。 | Mesh再計算 | 頂点整理・継ぎ目軽減向け。美観専用の曲率判断Weldではない。 |
| Scale | 数値 | Weld距離スケールを調整する。 | Mesh再計算 | 上げすぎると形状が潰れる可能性がある。 |
| Live Normals (Heavy) | トグル | 生成時に高品質な法線を計算し、滑らかな表示にする。 | Mesh再計算 | 重いが見た目の確認に有効。 |
| Auto-enable Live Normals on High | トグル | Highプリセット切替時にLive Normalsを自動ONにする。 | 表示/管理 | 仕上げ確認向けの自動化。 |
| Protect Partial Mesh | トグル | 容量不足や空結果などの危険な結果を適用しないよう保護する。 | Mesh再計算 | 診断表示時に出る保護系設定。 |
| Auto Safe Retry | トグル | 問題発生時、低解像度で自動再試行する。 | Mesh再計算 | 安全側のフォールバック。 |
| Chunked CPU/GPU Fallback | トグル | 通常生成が厳しい場合にChunked生成へ逃がす。 | Mesh再計算 | 大規模シーン向け。 |

## 4. Post-Process (Smoothing)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Setup Post Process | ボタン `sdf.setup_post_process` | `GeoRemesh_R` Geometry Nodesモディファイアを結果メッシュへ追加する。 | 表示/管理 | SDFメッシュ生成後の後段スムージング・整形用。 |
| GeoRemesh_R入力 | GNパラメータ | 追加済みGNノードグループの入力値をUIに展開する。 | 表示/管理 | Blenderのモディファイア評価として反映。SDF計算自体とは別。 |

## 5. The Stack

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| 色チップ | カラー | プリミティブ個別のColorを変更する。 | Mesh再計算 | カラーブレンディング保持のため再計算が必要。 |
| 行クリック / Object名 | ボタン `sdf.select_stack_obj` | 対応するSDFオブジェクトを選択する。 | 表示/管理 | StackとViewport選択を同期する。 |
| Operationアイコン | 選択 | Union / Subtract / Intersect を切り替える。 | Mesh再計算 | 形状評価の根幹。Layer Boundary内ではローカル層へ作用。 |
| Enabledチェック | トグル | Stack項目を有効/無効にする。 | Mesh再計算 | 無効項目はSDF評価から外れる。 |
| Collection行名 | ボタン `sdf.select_stack_obj` | Collection DividerのEmptyを選択する。 | 表示/管理 | Group Settingsを出す入口。 |
| Duplicate | ボタン `sdf.duplicate_collection` | Collection Dividerとその対象グループを複製する。 | Mesh再計算 | 複製後は新しいEmptyが選択される。 |
| Layer Boundary icon | トグル | そのDivider以下をローカルLayerとして評価し、結果を全体へUnionする。 | Mesh再計算 | Math FieldのIntersect範囲制御に重要。 |
| Break Parent icon | トグル | 親子関係のグルーピングを区切る。 | Mesh再計算 | Collection Dividerによる階層・移動単位の調整。 |
| Up / Down | ボタン `sdf.stack_move` | Stack項目の評価順を上下へ移動する。 | Mesh再計算 | SDFは順序依存。見た目が大きく変わる。 |
| Solo | トグル | 選択中Stack項目を単独確認する。 | Mesh再計算 | 複雑なStackの確認用。 |
| X | ボタン `sdf.stack_remove` | 選択中Stack項目を削除する。 | Mesh再計算 | Collectionの場合はEmptyと子の扱いに注意。 |
| Add Collection Divider | ボタン `sdf.add_collection_divider` | Stack内にグループ区切り用のEmpty/Dividerを追加する。 | Mesh再計算 | 追加後、そのEmptyが選択される。 |

## 6. Material

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Setup Nodes | ボタン `sdf.setup_material` | `Color` / `Metallic` / `Roughness` 属性を読む標準マテリアルノードを作成する。 | 表示/管理 | シェーダーノード構築のみ。 |
| Reset | ボタン `sdf.reset_material` | 標準マテリアルノード構成へ戻す。 | 表示/管理 | 共有Metallic/Roughnessも初期値へ戻る。 |
| Base Color + Apply Color All | カラー + ボタン `sdf.apply_color_all` | 全プリミティブへ同じColorを適用する。 | 軽量更新 | 全体一色化なので既存メッシュのColor属性更新で対応。 |
| Metallic / Roughness + Apply Material All | 数値 + ボタン `sdf.apply_material_all` | 全プリミティブへ同じMetallic/Roughnessを適用する。 | 軽量更新 | 既存メッシュ属性を更新し、SDF再評価は避ける。 |

## 7. Finalize / Output

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Fix Normals | ボタン `sdf.update_normals` | 高品質法線を再計算して適用する。 | Mesh再計算 | 見た目の仕上げ確認向け。 |
| Force Update | ボタン `sdf.generate_mesh` | 手動でSDF結果メッシュを再生成する。 | Mesh再計算 | Live Update OFF後の反映や確認に使う。 |
| Snapshot Mesh | ボタン `sdf.bake_mesh` | 現在のSDF結果から静的メッシュコピーを作る。Live SDFワークスペースは維持する。 | 表示/管理 | 作成されたSnapshotだけが選択状態になる。 |
| Finalize (Bake) | ボタン `sdf.finalize` | SDF結果を通常メッシュとして確定し、使用プリミティブを履歴へ退避する。 | Mesh再計算/確定 | Live編集を終える操作。戻すなら履歴や前バージョンを使う。 |

## 8. Group Settings: Collection Divider

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Name | テキスト | Stack上のCollection Divider表示名を変える。 | Mesh再計算 | 名前自体は形状に影響しないが、現状は通常更新経路。 |
| Layer Boundary | トグル | Divider以下をローカルLayerとして評価する。 | Mesh再計算 | `Base ∪ (Layer内評価結果)` のイメージ。 |
| Break Parent (Start New Group) | トグル | 親子/グループのつながりを区切る。 | Mesh再計算 | グループ単位での移動・複製整理に使う。 |
| Group Layout: Mirror / Radial / Spiral / Grid / Jitter | トグル群 | Group全体へ配置展開をかける。 | Mesh再計算 | プリミティブ単体のLayoutと同様の考え方。 |
| Mirror X/Y/Z / Offset | トグル/数値 | Groupを指定軸でミラー複製する。 | Mesh再計算 | 左右対称配置など。 |
| Radial Count / Radius / Axis | 数値/選択 | Groupを円周上に複製する。 | Mesh再計算 | 放射配置。 |
| Spiral Count / Radius / Pitch / Axis | 数値/選択 | Groupを螺旋状に複製する。 | Mesh再計算 | Radialの高さ方向拡張。 |
| Grid Count X/Y/Z / Spacing X/Y/Z | 数値 | Groupを格子状に複製する。 | Mesh再計算 | 規則的な反復構造向け。 |
| Rotation (Indiv & Accum) | 角度 | 各インスタンスの個別回転と累積回転を設定する。 | Mesh再計算 | Radial/Spiralで特に効く。 |
| Jitter Seed / Strength | 数値 | 配置にランダム揺らぎを加える。 | Mesh再計算 | 手作り感・自然さを足す。 |

## 9. Primitive Settings

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Shape | 選択 | 選択プリミティブの形状タイプを変更する。 | Mesh再計算 | Sphere / Box / Math Fieldなど。 |
| Union / Subtract / Intersect | ボタン/選択 | 選択プリミティブのブーリアン演算を指定する。 | Mesh再計算 | Stack上のOperationアイコンと同じ。 |
| Blend Profile | 選択 | ブレンド形状の質感をRound/Sharp/Soft/Tight/Chamferから選ぶ。 | Mesh再計算 | Smoothnessと組み合わせて接続感を作る。 |
| Chamfer Factor | 数値 | Blend ProfileがChamferの場合の係数。 | Mesh再計算 | 平面的な接続表現。 |
| Smoothness | 数値 | ブレンド幅・接続の滑らかさを調整する。 | Mesh再計算 | 作品全体の統一感に強く関わる。 |
| Noise / Scale | 数値 | SDF表面にノイズ変形を加える。 | Mesh再計算 | 表情付け・荒れ表現。 |
| Color | カラー | 個別プリミティブ色を変更する。 | Mesh再計算 | カラーブレンディングを正しく再評価するため再計算が必要。 |
| Color Mode | 選択 | 新規プリミティブ追加時の色割当方式を選ぶ。 | 表示/管理 | Fixed Palette / Auto Hue / Single Color。 |
| Auto Hue: Saturation / Value / Hue Step / Hue Offset | 数値 | Auto Hue時の自動色割当を調整する。 | 表示/管理 | 次に追加するプリミティブへ効く。 |
| Single Color: Base Color | カラー | Single Color時に新規プリミティブへ使う色。 | 表示/管理 | 既存プリミティブの色は自動変更しない。 |
| Metallic / Roughness | 数値 | 個別プリミティブのマテリアル属性を設定する。 | Mesh再計算 | 個別値はSDF結果属性へ反映するため通常更新。 |
| Shape Parameters | 数値 | 形状ごとの半径・高さ・角度・辺数などを調整する。 | Mesh再計算 | 詳細は下のPrimitive一覧参照。 |
| Edge | 選択 | プリミティブのエッジ処理をRound/Sharp/Soft/Tight/Chamferから選ぶ。 | Mesh再計算 | Math Fieldでは非表示。 |
| Edge Size | 数値 | エッジ処理のサイズを調整する。 | Mesh再計算 | R-BoxやCylinder系の面取り感に関わる。 |
| Edge Chamfer Smoothness | 数値 | EdgeがChamferの場合の滑らかさ。 | Mesh再計算 | 尖りと丸みの調整。 |
| Shell (Hollow) | 数値 | 形状を中空化する。 | Mesh再計算 | `abs(d) - shell_thickness` 系のSDF処理。 |

## 10. Math Field 専用コマンド

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Formula | 選択 | Gyroid / Schwarz P / Schwarz D を選ぶ。 | Mesh再計算 | TPMS系の数理フィールド式。 |
| Preset | 選択 | Fine / Medium / Coarse / Thick / Shellなどの初期設定を適用する。 | Mesh再計算 | Scale/Thickness/Extent等をまとめて設定。 |
| Mask | 選択 | Box / Sphere / Cylinder系の境界形状を選ぶ。 | Mesh再計算 | Math Fieldを有限範囲へ切る。 |
| Boundary | 選択 | Fade / Open / Box Clip系の境界挙動を選ぶ。 | Mesh再計算 | 端部の見え方に影響。 |
| Use Previous as Mask | ボタン `sdf.use_previous_as_mask` | 直前のプリミティブを外形マスクとして、Math FieldをIntersect設定にする。 | Mesh再計算 | 旧ラベル上はGyroid由来だが、V16.0.7ではMath Field向け。 |
| Phase | 数値 | フィールド周期を位相シフトする。 | Mesh再計算 | 穴や稜線の位置調整。 |
| Axis X/Y/Z | 数値 | 各軸方向のフィールド密度を調整する。 | Mesh再計算 | 非均一スケール時の見た目調整に重要。 |
| Auto Match Scale | ボタン `sdf.match_math_field_axis_to_scale` | Object Scaleの絶対値をAxis X/Y/Zへ反映する。 | Mesh再計算 | 伸縮後もワールド密度を揃えたい時に使う。値は0.05から8.0にClamp。 |
| Scale / Thickness / Bias / Extent | 数値 | Math Fieldのセル密度、厚み、オフセット、範囲を設定する。 | Mesh再計算 | Formula共通の基本パラメータ。 |

## 11. Layout (Instancing)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Mirror | トグル | 選択プリミティブをミラー複製する。 | Mesh再計算 | X/Y/Z軸指定とOffsetを使う。 |
| Radial | トグル | 円周上に複製する。 | Mesh再計算 | Count/Radius/Axisを設定。 |
| Spiral | トグル | 螺旋状に複製する。 | Mesh再計算 | Pitchで高さ方向を制御。 |
| Grid | トグル | 格子状に複製する。 | Mesh再計算 | Count X/Y/ZとSpacing X/Y/Zを設定。 |
| Jitter | トグル | 配置にランダム揺らぎを加える。 | Mesh再計算 | Seed/Strengthを設定。 |
| Rotation (Indiv & Accum) | 角度 | 個別回転と累積回転を設定する。 | Mesh再計算 | Radial/Spiral/Grid配置の方向付けに使う。 |

## 12. Deform (Stack)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| \+ | ボタン `sdf.deform_add` | Deform Stackに変形を追加する。 | Mesh再計算 | 最大2つまで。 |
| \- | ボタン `sdf.deform_remove` | 選択中の変形を削除する。 | Mesh再計算 | 変形順序も結果に影響。 |
| Up / Down | ボタン `sdf.deform_move` | 変形の順番を入れ替える。 | Mesh再計算 | 例: Bend後TwistとTwist後Bendは違う。 |
| Enabled | トグル | 選択中変形の有効/無効を切り替える。 | Mesh再計算 | 一時比較に便利。 |
| Type | 選択 | Elongate / Bend / Twist / Taperを選ぶ。 | Mesh再計算 | SDF空間変形。 |
| Axis | 選択 | 変形軸を選ぶ。 | Mesh再計算 | X/Y/Z。 |
| Angle / Factor | 数値 | Bend/Twist角度、Taper係数などを調整する。 | Mesh再計算 | Typeにより意味が変わる。 |
| Origin Offset | 数値 | 変形中心をずらす。 | Mesh再計算 | 選択軸に応じて表示成分が変わる。 |
| Elongate X/Y/Z | 数値 | 空間を各軸方向へ伸長する。 | Mesh再計算 | Elongate専用。 |

## 13. Add New Primitives

| ボタン | shape_type | 主なパラメータ | 再計算 | 用途 |
|----|----|----|----|----|
| Sphere | `sphere` | Radius | Mesh再計算 | 基本球。 |
| Box | `box` | Object Scale | Mesh再計算 | 基本箱。 |
| R-Box | `rounded_box` | Roundness | Mesh再計算 | 角丸箱。 |
| Torus | `torus` | Main Radius / Pipe Radius | Mesh再計算 | 輪形状。 |
| Cylinder | `cylinder` | Radius / Height (Half) | Mesh再計算 | 円柱。 |
| Capsule | `capsule` | Radius / Height (Half) | Mesh再計算 | カプセル形状。 |
| Hex | `hex_prism` | Radius / Height (Half) | Mesh再計算 | 六角柱。 |
| Pyramid | `pyramid` | Base Size / Height | Mesh再計算 | 四角錐。 |
| Taper | `capped_cone` | Bottom Radius / Top Radius / Height | Mesh再計算 | テーパー円柱。 |
| N-gon | `ngon_prism` | Radius / Sides / Height | Mesh再計算 | 多角柱。 |
| Ellipsoid | `ellipsoid` | Radius X/Y/Z | Mesh再計算 | 楕円体。 |
| R-Cylinder | `rounded_cylinder` | Radius / Edge Radius / Height | Mesh再計算 | 丸め円柱。 |
| C-Torus | `capped_torus` | Main Radius / Pipe Radius / Angle | Mesh再計算 | 部分トーラス。 |
| Octahedron | `octahedron` | Size | Mesh再計算 | 八面体。 |
| Cut Sphere | `cut_sphere` | Cut Height | Mesh再計算 | 切断球。 |
| Math Field | `math_field` | Scale / Thickness / Bias / Extent | Mesh再計算 | Gyroid / Schwarz P / Schwarz Dなどの数理フィールド。 |

## 14. Object Utilities / Cleanup

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|----|----|----|----|----|
| Wire/Solid | ボタン `sdf.toggle_display` | 選択オブジェクトの表示をWire/Textured系で切り替える。 | 表示/管理 | 見え方だけの変更。 |
| Move to SDF | ボタン `sdf.move_to_sdf_collection` | 選択オブジェクトをSDF_Collectionへ移し、SDF Primitiveとして扱う。 | 表示/管理 | 既存Blenderオブジェクトの取り込み用。形状推定は名前ベース。 |
| Include Baked Results | トグル | All Clearで確定済み結果も削除対象に含める。 | 表示/管理 | ONは強い掃除。履歴を残したい場合はOFF。 |
| All Clear | ボタン `sdf.all_clear` | SDF関連オブジェクト/コレクションを削除する。 | 削除 | 作業空間を掃除する操作。Include Baked Resultsの状態に注意。 |

## 15. Operator ID一覧

| Operator ID | ラベル | 概要 |
|----|----|----|
| `sdf.add_primitive` | Add SDF Primitive | プリミティブを追加する。 |
| `sdf.toggle_display` | Toggle Wire/Solid | 表示モードを切り替える。 |
| `sdf.move_to_sdf_collection` | Move to SDF Collection | 選択オブジェクトをSDF_Collectionへ移す。 |
| `sdf.duplicate_collection` | Duplicate Collection | Collection Dividerグループを複製する。 |
| `sdf.bake_mesh` | Snapshot Mesh | 静的メッシュコピーを作る。 |
| `sdf.setup_material` | Setup Color Material | 標準マテリアルノードを作る。 |
| `sdf.reset_material` | Reset Shader Nodes | 標準ノード構成へ戻す。 |
| `sdf.apply_color_all` | Apply Color To All | 全体色を一括適用する。 |
| `sdf.apply_material_all` | Apply Material To All | Metallic/Roughnessを一括適用する。 |
| `sdf.update_normals` | Update Normals | 法線を更新する。 |
| `sdf.generate_mesh` | Generate SDF Mesh | 結果メッシュを強制更新する。 |
| `sdf.add_selected` | Add Selected to SDF | 選択オブジェクトをSDF Stackへ追加する。 |
| `sdf.make_output` | New SDF Workspace | 新規SDFワークスペースを作る。 |
| `sdf.stack_move` | Move Stack Item | Stack項目を移動する。 |
| `sdf.stack_remove` | Remove Stack Item | Stack項目を削除する。 |
| `sdf.select_stack_obj` | Select SDF Object | Stack対応オブジェクトを選択する。 |
| `sdf.use_previous_as_mask` | Use Previous as Mask | Math Fieldを直前プリミティブでIntersectする設定にする。 |
| `sdf.match_math_field_axis_to_scale` | Auto Match Scale | Math Field Axis値をObject Scaleに合わせる。 |
| `sdf.setup_post_process` | Setup Post Process (GN) | GeoRemesh_Rを追加する。 |
| `sdf.finalize` | Finalize (Bake All) | SDF結果を確定メッシュ化する。 |
| `sdf.set_resolution_preset` | Set Resolution Preset | Low/Highプリセットへ切り替える。 |
| `sdf.all_clear` | All Clear | SDF関連データを削除する。 |
| `sdf.deform_add` | Add Deform | Deform Stackへ追加する。 |
| `sdf.deform_remove` | Remove Deform | Deform Stackから削除する。 |
| `sdf.deform_move` | Move Deform | Deform順序を移動する。 |
| `sdf.switch_algo` | Switch Algorithm | MC/DCを切り替える。 |
| `sdf.add_collection_divider` | Add Collection Divider | Collection Dividerを追加する。 |

Source basis: `rust_gpu_sdf_addon/ui.py`, `operators.py`, `properties.py`, `constants.py` in Rust-GPU-SDF-V16.0.7.
