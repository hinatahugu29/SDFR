// V15.5 Dual Contouring Main Pass (Bitmask Culling)

// V15.9.9.1: 元は vertex_pass 内でローカル `let edges = array<vec2<u32>,12>(...)` として
// 宣言し動的インデックス(edges[i])していたが、この「関数ローカル配列リテラルへの動的アクセス」
// パターンが特定のNVIDIAドライバでシェーダーコンパイラのクラッシュ(EXCEPTION_ACCESS_VIOLATION in
// nvoglv64.dll)を引き起こすことを確認したため、既に正常動作している CORNERS (common.wgsl) と
// 同じ「モジュールスコープの const」の形へ変更した。
const DC_EDGES = array<vec2<u32>, 12>(
    vec2<u32>(0,1), vec2<u32>(1,2), vec2<u32>(2,3), vec2<u32>(3,0),
    vec2<u32>(4,5), vec2<u32>(5,6), vec2<u32>(6,7), vec2<u32>(7,4),
    vec2<u32>(0,4), vec2<u32>(1,5), vec2<u32>(2,6), vec2<u32>(3,7)
);

// V15.9.9.1: 座標 -> b_ptr の対応付けを、旧来のオープンアドレス法ハッシュ
// (atomicCompareExchangeWeak ベース) から「密なグリッドマップ」へ置き換えた。
//
// 旧ハッシュは、WGSLに強いCASが無く atomicCompareExchangeWeak (弱いCAS) しか
// 使えないところ、この NVIDIA/Vulkan/naga 環境では弱いCASの擬似失敗率が異常に高く、
// ブロック挿入の約72%が get_block_ptr で引けなくなり、DCメッシュの頂点/面が
// 非決定的に大量欠落する原因になっていた (実機計測で確認)。
//
// ブロックグリッド座標は小さい (各軸 = ceil(res/8)、res<=512 で最大64) ため、
// flat index = x + y*BD + z*BD*BD が衝突なく一意に定まり、hash_values バッファ
// (要素数 hash_table_size = 2,097,152) に十分収まる (64^3 = 262,144)。
// 各ブロック座標は detect_pass の1ワークグループからのみ書かれるので原子操作も不要。
// 空きを表すセンチネルは 0xFFFFFFFF (clear_values_buffer によるクリア値と一致)。

fn block_grid_dim() -> u32 {
    return (config.res + 7u) / 8u;
}

fn block_flat_index(p: vec3<i32>) -> u32 {
    let bd = block_grid_dim();
    return u32(p.x) + u32(p.y) * bd + u32(p.z) * bd * bd;
}

fn get_block_ptr(p: vec3<i32>) -> i32 {
    let idx = block_flat_index(p);
    if (idx >= config.hash_table_size) { return -1; }
    let v = atomicLoad(&hash_values[idx]);
    if (v == 0xFFFFFFFFu) { return -1; }
    return i32(v);
}

fn insert_block_ptr(p: vec3<i32>, b_ptr: i32) {
    let idx = block_flat_index(p);
    if (idx >= config.hash_table_size) { return; }
    atomicStore(&hash_values[idx], u32(b_ptr));
}

// =============================================================================
// V15.9.9.1: 標準的なDCのQEFソルバー (SVD相当)
// 対称3x3 の A^T A をヤコビ回転で固有値分解し、小さい特異値を切り捨てた
// 擬似逆行列で最小二乗解を求める。mass point バイアス形式:
//   x = mass_point + pinv(ATA) * (ATb - ATA * mass_point)
// これは Ju et al. 2002 / Schaefer&Warren "Secret Sauce" / Gildea の
// GPU-DC 実装で用いられる標準手法で、球面など A^T A がランク落ちする状況でも
// 頂点がセル隅へ飛ばず滑らかに配置される (旧: 直接逆行列は near-singular で破綻)。
// CPU 側 (dc.rs) は既に nalgebra SVD で同等の処理を行っており、それに揃える。
// クラッシュ源となる「関数ローカル配列への動的インデックス」を避けるため、
// 行列要素はすべて名前付きスカラーで保持する。
// =============================================================================
fn qef_solve_svd(
    ata00: f32, ata01: f32, ata02: f32,
    ata11: f32, ata12: f32, ata22: f32,
    atb: vec3<f32>,
    mass_point: vec3<f32>
) -> vec3<f32> {
    // b' = ATb - ATA * mass_point (mass point を原点にとった相対系で解く)
    let ata_c = vec3<f32>(
        ata00 * mass_point.x + ata01 * mass_point.y + ata02 * mass_point.z,
        ata01 * mass_point.x + ata11 * mass_point.y + ata12 * mass_point.z,
        ata02 * mass_point.x + ata12 * mass_point.y + ata22 * mass_point.z
    );
    let b = atb - ata_c;

    // --- 対称3x3のヤコビ固有値分解 ---
    var m00 = ata00; var m01 = ata01; var m02 = ata02;
    var m11 = ata11; var m12 = ata12; var m22 = ata22;
    // 固有ベクトル行列 V (列が固有ベクトル)、初期は単位行列
    var v00 = 1.0; var v01 = 0.0; var v02 = 0.0;
    var v10 = 0.0; var v11 = 1.0; var v12 = 0.0;
    var v20 = 0.0; var v21 = 0.0; var v22 = 1.0;

    for (var sweep = 0u; sweep < 6u; sweep++) {
        // (0,1) を消す
        if (abs(m01) > 1e-12) {
            let phi = 0.5 * atan2(2.0 * m01, m11 - m00);
            let c = cos(phi); let s = sin(phi);
            let n00 = c*c*m00 - 2.0*s*c*m01 + s*s*m11;
            let n11 = s*s*m00 + 2.0*s*c*m01 + c*c*m11;
            let n02 = c*m02 - s*m12;
            let n12 = s*m02 + c*m12;
            m00 = n00; m11 = n11; m01 = 0.0; m02 = n02; m12 = n12;
            let a00 = c*v00 - s*v01; let a01 = s*v00 + c*v01;
            let a10 = c*v10 - s*v11; let a11 = s*v10 + c*v11;
            let a20 = c*v20 - s*v21; let a21 = s*v20 + c*v21;
            v00=a00; v01=a01; v10=a10; v11=a11; v20=a20; v21=a21;
        }
        // (0,2) を消す
        if (abs(m02) > 1e-12) {
            let phi = 0.5 * atan2(2.0 * m02, m22 - m00);
            let c = cos(phi); let s = sin(phi);
            let n00 = c*c*m00 - 2.0*s*c*m02 + s*s*m22;
            let n22 = s*s*m00 + 2.0*s*c*m02 + c*c*m22;
            let n01 = c*m01 - s*m12;
            let n12 = s*m01 + c*m12;
            m00 = n00; m22 = n22; m02 = 0.0; m01 = n01; m12 = n12;
            let a00 = c*v00 - s*v02; let a02 = s*v00 + c*v02;
            let a10 = c*v10 - s*v12; let a12 = s*v10 + c*v12;
            let a20 = c*v20 - s*v22; let a22 = s*v20 + c*v22;
            v00=a00; v02=a02; v10=a10; v12=a12; v20=a20; v22=a22;
        }
        // (1,2) を消す
        if (abs(m12) > 1e-12) {
            let phi = 0.5 * atan2(2.0 * m12, m22 - m11);
            let c = cos(phi); let s = sin(phi);
            let n11 = c*c*m11 - 2.0*s*c*m12 + s*s*m22;
            let n22 = s*s*m11 + 2.0*s*c*m12 + c*c*m22;
            let n01 = c*m01 - s*m02;
            let n02 = s*m01 + c*m02;
            m11 = n11; m22 = n22; m12 = 0.0; m01 = n01; m02 = n02;
            let a01 = c*v01 - s*v02; let a02 = s*v01 + c*v02;
            let a11 = c*v11 - s*v12; let a12 = s*v11 + c*v12;
            let a21 = c*v21 - s*v22; let a22 = s*v21 + c*v22;
            v01=a01; v02=a02; v11=a11; v12=a12; v21=a21; v22=a22;
        }
    }

    // 固有値 (対角) と固有ベクトル (V の列)
    let lam = vec3<f32>(m00, m11, m22);
    let e0 = vec3<f32>(v00, v10, v20);
    let e1 = vec3<f32>(v01, v11, v21);
    let e2 = vec3<f32>(v02, v12, v22);

    // V15.9.9.2: Tikhonov (Levenberg-Marquardt 相当) 正則化。
    // 旧来はハード特異値切り捨て (thresh = 0.01*max_lam) のみだったが、CPU 版 (dc.rs:57,
    // lambda=0.05) には対応する対角正則化があり GPU/CPU で頂点位置が食い違っていた。
    // 固有値に lambda を加えて解くことで、平面・円筒など ATA がランク落ちする領域でも
    // 擬似逆が well-conditioned になり、null 空間方向は自然に mass point へ引き込まれる
    // (小さい固有値成分は減衰するのでハード切り捨ては不要)。CPU と同じ lambda=0.05。
    // ATA は半正定値のため固有値は非負だが、fp 誤差で微小に負となる場合に備え max(.,0)。
    let lambda = 0.05;
    var x = vec3<f32>(0.0);
    x += (dot(e0, b) / (max(lam.x, 0.0) + lambda)) * e0;
    x += (dot(e1, b) / (max(lam.y, 0.0) + lambda)) * e1;
    x += (dot(e2, b) / (max(lam.z, 0.0) + lambda)) * e2;

    return mass_point + x;
}

var<workgroup> wg_b_ptr: i32;

@compute @workgroup_size(8, 8, 4)
fn vertex_pass(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    if (lid.x == 0u && lid.y == 0u && lid.z == 0u) {
        let block_list_idx = wid.y * 65535u + wid.x;
        let active_count = atomicLoad(&counters[3]);
        if (block_list_idx < active_count) {
            // V15.9.9.1: detect_pass は active_blocks[b_ptr] = packed を b_ptr の昇順で書いており、
            // vertex_pass の block_list_idx はまさにその b_ptr に一致する。よってハッシュ探索
            // (get_block_ptr) は不要かつ、ハッシュ挿入失敗時にブロックを丸ごと取りこぼす原因に
            // なっていた。block_list_idx を直接 b_ptr として用いることでハッシュ依存を排除する。
            wg_b_ptr = i32(block_list_idx);
        } else { wg_b_ptr = -1; }
    }
    workgroupBarrier();
    let b_ptr = wg_b_ptr; if (b_ptr < 0) { return; }
    let b_ptr_u = u32(b_ptr);

    let block_list_idx_sync = wid.y * 65535u + wid.x;
    let packed_val = active_blocks[block_list_idx_sync];
    let block_coord = vec3<i32>(i32(packed_val & 0x7FFu), i32((packed_val >> 11u) & 0x7FFu), i32((packed_val >> 22u) & 0x3FFu));
    let clear_base = u32(b_ptr) * 1024u; let tid = lid.x + lid.y * 8u + lid.z * 64u;
    block_data[clear_base + tid] = 0u; block_data[clear_base + tid + 256u] = 0u;
    block_data[clear_base + tid + 512u] = 0u; block_data[clear_base + tid + 768u] = 0u;
    storageBarrier();
    let res = config.res; let step = config.domain_size / f32(res);
    for (var z_off = 0u; z_off < 8u; z_off += 4u) {
        let local_id = vec3<u32>(lid.x, lid.y, lid.z + z_off);
        let id = vec3<u32>(block_coord * 8) + local_id;
        if (any(id >= vec3<u32>(res))) { continue; }
        let p_min = (vec3<f32>(id) - f32(res)/2.0) * step;
        var vals: array<f32, 8>; var cube_idx = 0u;
        for (var i = 0u; i < 8u; i++) {
            vals[i] = get_scene_dist_indexed(p_min + CORNERS[i] * step, b_ptr_u);
            if (vals[i] <= 0.0) { cube_idx |= (1u << i); }
        }
        if (cube_idx == 0u || cube_idx == 255u) { continue; }
        var ATA_0 = 0.0; var ATA_1 = 0.0; var ATA_2 = 0.0;
        var ATA_3 = 0.0; var ATA_4 = 0.0; var ATA_5 = 0.0;
        var ATB = vec3<f32>(0.0);
        var avg_p = vec3<f32>(0.0);
        var count = 0.0;

        for (var i = 0u; i < 12u; i++) {
            let v1 = DC_EDGES[i].x; let v2 = DC_EDGES[i].y;
            if ((vals[v1] <= 0.0) != (vals[v2] <= 0.0)) {
                let t = clamp(vals[v1] / (vals[v1] - vals[v2] + 1e-10), 0.0, 1.0);
                let p = p_min + mix(CORNERS[v1], CORNERS[v2], t) * step;
                // V15.9.9.2: エッジ交差点の法線 (Hermiteデータ) は 4タップ tetrahedron を使用。
                // QEF入力の法線はセル毎最大12回評価される最ホットパスで、6タップ中心差分だと
                // SDF評価回数(=全プリミティブループ)が膨大になる。Hermiteデータ用途では4タップで
                // 品質劣化はほぼ無く、SDF評価を1/3削減しSPIR-Vも縮小する(既存 get_scene_normal_fast)。
                let n = get_scene_normal_fast(p, b_ptr_u);

                ATA_0 += n.x * n.x; ATA_1 += n.x * n.y; ATA_2 += n.x * n.z;
                ATA_3 += n.y * n.y; ATA_4 += n.y * n.z; ATA_5 += n.z * n.z;
                let b = dot(n, p);
                ATB += n * b;
                avg_p += p; count += 1.0;
            }
        }

        if (count > 0.0) {
            let mass_point = avg_p / count;
            // 標準的なSVDベースQEFで頂点位置を求める (mass pointバイアス + 特異値切り捨て)
            var pos = qef_solve_svd(ATA_0, ATA_1, ATA_2, ATA_3, ATA_4, ATA_5, ATB, mass_point);
            // 数値的な暴れ対策としてセル内にクランプ (標準の安全策)
            pos = clamp(pos, p_min, p_min + step);

            // Surface snap iteration (Safe)
            // V15.9.9.2: snap 用の法線も 4タップに変更 (方向のみ使用するため品質影響なし)。
            let n_snap = get_scene_normal_fast(pos, b_ptr_u);
            let d_snap = get_scene_dist_indexed(pos, b_ptr_u);
            pos -= n_snap * d_snap * 0.5; // 0.9 -> 0.5 (More stable)
            let v_idx = atomicAdd(&counters[0], 1u);
            let b_idx = local_id.x | (local_id.y << 3u) | (local_id.z << 6u);
            block_data[u32(b_ptr) * 1024u + b_idx] = v_idx + 1u;
            // 出力法線も6タップで再評価して品質を確保
            let res_v = get_scene_sdf_indexed(pos, b_ptr_u); let normal = get_scene_normal(pos, b_ptr_u);
            let base = v_idx * 11u;
            vertices[base+0]=pos.x; vertices[base+1]=pos.y; vertices[base+2]=pos.z;
            vertices[base+3]=res_v.color.x; vertices[base+4]=res_v.color.y; vertices[base+5]=res_v.color.z;
            vertices[base+6]=res_v.metallic; vertices[base+7]=res_v.roughness;
            vertices[base+8]=normal.x; vertices[base+9]=normal.y; vertices[base+10]=normal.z;
        }
    }
}

@compute @workgroup_size(8, 8, 4)
fn face_pass(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    let block_list_idx = wid.y * 65535u + wid.x;
    let active_count = atomicLoad(&counters[3]);
    if (block_list_idx >= active_count) { return; }
    let packed = active_blocks[block_list_idx];
    let block_coord = vec3<i32>(i32(packed & 0x7FFu), i32((packed >> 11u) & 0x7FFu), i32((packed >> 22u) & 0x3FFu));
    // V15.9.9.1: 自ブロックの b_ptr は block_list_idx に等しい (vertex_pass と同様)。
    // 隣接ブロックの参照(get_block_ptr)のみ密グリッドマップを用いる。
    let b_ptr_main = i32(block_list_idx);
    let b_ptr_u = u32(b_ptr_main);

    let res = config.res; let step = config.domain_size / f32(res);
    for (var z_off = 0u; z_off < 8u; z_off += 4u) {
        let local_id = vec3<u32>(lid.x, lid.y, lid.z + z_off);
        let id = vec3<u32>(block_coord * 8) + local_id;
        if (any(id >= vec3<u32>(res - 1u))) { continue; }
        for (var axis = 0u; axis < 3u; axis++) {
            let p1 = (vec3<f32>(id) - f32(res)/2.0) * step; var p2_off = vec3<f32>(0, 0, 0);
            if (axis == 0u) { p2_off.x = 1.0; } else if (axis == 1u) { p2_off.y = 1.0; } else { p2_off.z = 1.0; }
            // V15.9.9.2: p1 の距離符号は交差判定と巻き方向判定の両方で使うため、一度だけ評価して再利用する
            // (旧来は get_scene_dist_indexed(p1) を2回評価していた。1回は全プリミティブループ)。
            let d_p1_inside = get_scene_dist_indexed(p1, b_ptr_u) <= 0.0;
            if (d_p1_inside != (get_scene_dist_indexed(p1 + p2_off * step, b_ptr_u) <= 0.0)) {
                var v_indices: array<u32, 4>; var valid = true;
                for (var i = 0u; i < 4u; i++) {
                    var q = vec3<i32>(id);
                    // V15.9.9.1: 周囲4セルを集める順序は、2つの変化軸+エッジ軸が右手系に
                    // なるように揃える必要がある。元は axis==1 のみ (x,z) 順で左手系になっており、
                    // Y軸エッジの四角形(全体の約1/3)が裏向きに巻かれ、Blenderの法線計算を
                    // 破綻させて曲面に weave (畝) を生む原因になっていた。axis==1 を (z,x) 順に
                    // 修正して全軸の手系を統一する。
                    if (axis == 0u) { q.y -= i32(i & 1u); q.z -= i32((i >> 1u) & 1u); }
                    else if (axis == 1u) { q.z -= i32(i & 1u); q.x -= i32((i >> 1u) & 1u); }
                    else { q.x -= i32(i & 1u); q.y -= i32((i >> 1u) & 1u); }
                    if (any(q < vec3<i32>(0))) { valid = false; break; }
                    let b_ptr_q = get_block_ptr(q / 8);
                    if (b_ptr_q < 0) { valid = false; break; }
                    let v_val = block_data[u32(b_ptr_q) * 1024u + (u32(q.x % 8) | (u32(q.y % 8) << 3u) | (u32(q.z % 8) << 6u))];
                    if (v_val == 0u) { valid = false; break; }
                    v_indices[i] = v_val - 1u;
                }
                if (valid) {
                    let base = atomicAdd(&counters[1], 6u);
                    // V15.9.9.1: 四角形の分割対角線をセルのパリティで交互に入れ替える
                    // (チェッカーボード分割)。全て同じ向きの対角線で分割すると、曲面上に
                    // 方向性のある「畝織り(コーデュロイ)状」のシェーディングアーティファクトが
                    // 出るため、これを崩して目立たなくする標準的な手法。ジオメトリ精度には影響しない。
                    let flip_diag = ((id.x + id.y + id.z) & 1u) == 1u;
                    if (d_p1_inside) {
                        if (flip_diag) {
                            // 対角線 v0-v3
                            indices[base+0]=v_indices[0]; indices[base+1]=v_indices[1]; indices[base+2]=v_indices[3];
                            indices[base+3]=v_indices[0]; indices[base+4]=v_indices[3]; indices[base+5]=v_indices[2];
                        } else {
                            // 対角線 v1-v2
                            indices[base+0]=v_indices[0]; indices[base+1]=v_indices[1]; indices[base+2]=v_indices[2];
                            indices[base+3]=v_indices[1]; indices[base+4]=v_indices[3]; indices[base+5]=v_indices[2];
                        }
                    } else {
                        if (flip_diag) {
                            indices[base+0]=v_indices[0]; indices[base+1]=v_indices[3]; indices[base+2]=v_indices[1];
                            indices[base+3]=v_indices[0]; indices[base+4]=v_indices[2]; indices[base+5]=v_indices[3];
                        } else {
                            indices[base+0]=v_indices[0]; indices[base+1]=v_indices[2]; indices[base+2]=v_indices[1];
                            indices[base+3]=v_indices[1]; indices[base+4]=v_indices[2]; indices[base+5]=v_indices[3];
                        }
                    }
                }
            }
        }
    }
}
