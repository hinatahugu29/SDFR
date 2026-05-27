// V15.9.6.2 Robust Detect Pass (Shape-aware Bounds + overflow fallback)
// Headers provided by common.wgsl

var<workgroup> block_intersected: atomic<u32>;
var<workgroup> temp_prim_list: array<u32, 64>;
var<workgroup> temp_prim_count: atomic<u32>;
var<workgroup> scene_has_csg_flag: atomic<u32>;

@compute @workgroup_size(8, 8, 8)
fn detect_pass(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    if (all(lid == vec3<u32>(0u))) {
        atomicStore(&block_intersected, 0u);
        atomicStore(&temp_prim_count, 0u);
        atomicStore(&scene_has_csg_flag, 0u);
    }
    workgroupBarrier();

    let res = config.res;
    let step = config.domain_size / f32(res);

    var b_min = (vec3<f32>(wid * 8u) - f32(res) / 2.0) * step - vec3<f32>(step * 2.5 + 0.1);
    var b_max = b_min + vec3<f32>(step * 13.0 + 0.2);

    if ((config.symmetry & 1u) != 0u) {
        if (b_max.x < 0.0) {
            let tmp = b_min.x; b_min.x = -b_max.x; b_max.x = -tmp;
        } else if (b_min.x < 0.0) {
            let folded_max = max(abs(b_min.x), abs(b_max.x));
            b_min.x = 0.0;
            b_max.x = folded_max;
        }
    }
    if ((config.symmetry & 2u) != 0u) {
        if (b_max.y < 0.0) {
            let tmp = b_min.y; b_min.y = -b_max.y; b_max.y = -tmp;
        } else if (b_min.y < 0.0) {
            let folded_max = max(abs(b_min.y), abs(b_max.y));
            b_min.y = 0.0;
            b_max.y = folded_max;
        }
    }
    if ((config.symmetry & 4u) != 0u) {
        if (b_max.z < 0.0) {
            let tmp = b_min.z; b_min.z = -b_max.z; b_max.z = -tmp;
        } else if (b_min.z < 0.0) {
            let folded_max = max(abs(b_min.z), abs(b_max.z));
            b_min.z = 0.0;
            b_max.z = folded_max;
        }
    }

    if (all(lid == vec3<u32>(0u))) {
        let num_prims = config.num_primitives;
        let eps = 1e-4;
        for (var i = 0u; i < num_prims; i++) {
            let prim = primitives[i];
            let prim_op = u32(prim.size_and_op.w);
            if (prim_op != 0u) {
                atomicStore(&scene_has_csg_flag, 1u);
            }
            let center = prim.center_and_shape.xyz;
            let size = prim.size_and_op.xyz;
            let prim_max_s = max(size.x, max(size.y, size.z));
            let shape_id = u32(prim.center_and_shape.w);
            var local_ext = vec3<f32>(1.0, 1.0, 1.0);
            if (shape_id == 0u) {
                local_ext = vec3<f32>(prim.params.x);
            } else if (shape_id == 1u || shape_id == 4u) {
                local_ext = vec3<f32>(1.0, 1.0, 1.0);
            } else if (shape_id == 2u) {
                let r1 = prim.extra_params.x;
                let r2 = prim.extra_params.y;
                local_ext = vec3<f32>(r1 + r2, r1 + r2, r2);
            } else if (shape_id == 3u || shape_id == 6u) {
                let r = prim.extra_params.x;
                let h = prim.extra_params.y;
                local_ext = vec3<f32>(r, r, h);
            } else if (shape_id == 5u) {
                let r = prim.extra_params.x;
                let h = prim.extra_params.y;
                local_ext = vec3<f32>(r, r, h + r);
            } else if (shape_id == 7u) {
                let s_pyr = prim.extra_params.x;
                let h = prim.extra_params.y;
                local_ext = vec3<f32>(s_pyr, s_pyr, h);
            } else if (shape_id == 8u) {
                let r_max = max(prim.extra_params.x, prim.extra_params.y);
                let h = prim.extra_params.z;
                local_ext = vec3<f32>(r_max, r_max, h);
            } else if (shape_id == 9u) {
                let r = prim.extra_params.x;
                let h = prim.extra_params.z;
                local_ext = vec3<f32>(r, r, h);
            } else if (shape_id == 10u) {
                local_ext = vec3<f32>(prim.extra_params.x, prim.extra_params.y, prim.extra_params.z);
            } else if (shape_id == 11u) {
                let ra = prim.extra_params.x;
                let rb = prim.extra_params.y;
                let h = prim.extra_params.z;
                local_ext = vec3<f32>(ra, ra, h + rb);
            } else if (shape_id == 12u) {
                let r_max = prim.extra_params.x + prim.extra_params.y;
                local_ext = vec3<f32>(r_max, r_max, r_max);
            } else if (shape_id == 13u) {
                let s_oct = prim.extra_params.x;
                local_ext = vec3<f32>(s_oct, s_oct, s_oct);
            } else if (shape_id == 14u) {
                let r = prim.params.x;
                local_ext = vec3<f32>(r, r, r);
            }

            var bound_radius = length(local_ext * size);
            bound_radius += prim.params.y + abs(prim.noise_params.x) + prim.modifier_params.y + prim.modifier_params.w;

            let mode_flags = u32(prim.layout_data1.x);
            if ((mode_flags & 1u) != 0u) {
                bound_radius += abs(prim.layout_data1.y);
            }
            if ((mode_flags & 2u) != 0u || (mode_flags & 4u) != 0u) {
                bound_radius += abs(prim.layout_data1.z);
            }
            if ((mode_flags & 8u) != 0u) {
                let grid_packed = u32(prim.layout_data2.z);
                let gx = max(0.0, f32(grid_packed % 100u) - 1.0);
                let gy = max(0.0, f32((grid_packed / 100u) % 100u) - 1.0);
                let gz = max(0.0, f32(grid_packed / 10000u) - 1.0);
                bound_radius += length(vec3<f32>(gx * abs(prim.layout_data2.w), gy * abs(prim.layout_data3.x), gz * abs(prim.layout_data3.y))) * 0.5;
            }
            if ((mode_flags & 32u) != 0u) {
                bound_radius += abs(prim.layout_data2.y);
            }
            bound_radius += prim_max_s * (abs(prim.layout_data4.y) + abs(prim.layout_data4.z) + abs(prim.layout_data4.w)) * 0.5;
            if ((mode_flags & 0x2Fu) != 0u) {
                bound_radius += prim_max_s * 0.5 + 0.25;
            }

            let packed_meta = u32(prim.deform_data1.x);
            for (var si = 0u; si < 4u; si++) {
                let slot_info = (packed_meta >> (si * 6u)) & 0x3Fu;
                let dt = slot_info & 0xFu;
                if (dt == 0u) { continue; }

                var slot_factor = 0.0;
                if (si == 0u) { slot_factor = prim.deform_data1.y; }
                else if (si == 1u) { slot_factor = prim.deform_data2.y; }
                else if (si == 2u) { slot_factor = prim.deform_data3.y; }
                else { slot_factor = prim.deform_data4.y; }

                if (dt == 1u) {
                    if (si == 0u) { bound_radius += length(prim.deform_data1.yzw); }
                    else if (si == 1u) { bound_radius += length(prim.deform_data2.yzw); }
                    else if (si == 2u) { bound_radius += length(prim.deform_data3.yzw); }
                    else { bound_radius += length(prim.deform_data4.yzw); }
                } else if (dt == 2u) {
                    let bend_angle = abs(slot_factor);
                    bound_radius += prim_max_s * prim_max_s * bend_angle * 0.5 + prim_max_s * 0.3;
                } else if (dt == 3u) {
                    let twist_angle = abs(slot_factor);
                    bound_radius += prim_max_s * twist_angle * prim_max_s * 0.5;
                } else if (dt == 4u) {
                    let taper_factor = abs(slot_factor);
                    bound_radius += prim_max_s * taper_factor * prim_max_s;
                }
            }
            if (packed_meta != 0u) {
                bound_radius += prim_max_s * 0.75 + 0.25;
            }
            if (((mode_flags & 0x2Fu) != 0u) && packed_meta != 0u) {
                bound_radius += prim_max_s * 0.75 + abs(prim.params.y) + abs(prim.noise_params.x);
            }

            let safety = max(step * 12.0, 0.65);
            let p_min = center - (bound_radius + safety);
            let p_max = center + (bound_radius + safety);

            if (all(b_min < p_max + eps) && all(b_max > p_min - eps)) {
                let pos = atomicAdd(&temp_prim_count, 1u);
                if (pos < 64u) {
                    temp_prim_list[pos] = i;
                    atomicStore(&block_intersected, 1u);
                } else {
                    atomicStore(&block_intersected, 1u);
                    atomicAdd(&counters[4], 1u);
                }
            }
        }
    }
    workgroupBarrier();

    if (atomicLoad(&block_intersected) == 1u && all(lid == vec3<u32>(0u))) {
        let block_coord = vec3<i32>(wid);
        let packed_id = (u32(block_coord.x) & 0x7FFu) | ((u32(block_coord.y) & 0x7FFu) << 11u) | ((u32(block_coord.z) & 0x3FFu) << 22u);

        let raw_p_count = atomicLoad(&temp_prim_count);
        let active_cap = min(arrayLength(&active_blocks), arrayLength(&block_prim_info));
        if (active_cap == 0u) {
            atomicAdd(&counters[4], 1u);
            return;
        }
        let b_ptr = atomicAdd(&counters[3], 1u);
        if (b_ptr >= active_cap) {
            atomicAdd(&counters[4], 1u);
            return;
        }

        // Conservative safety mode:
        // if the scene includes any CSG op, avoid per-block primitive list culling.
        // This prioritizes topology stability over speed.
        if (atomicLoad(&scene_has_csg_flag) == 1u) {
            block_prim_info[b_ptr].offset = 0u;
            block_prim_info[b_ptr].count = ALL_PRIMS_SENTINEL;
            active_blocks[b_ptr] = packed_id;
            atomicAdd(&counters[4], 1u);
            return;
        }

        if (raw_p_count > 64u) {
            block_prim_info[b_ptr].offset = 0u;
            block_prim_info[b_ptr].count = ALL_PRIMS_SENTINEL;
            active_blocks[b_ptr] = packed_id;
            atomicAdd(&counters[4], 1u);
            return;
        }

        var p_count = raw_p_count;
        var has_csg_op = false;
        for (var pi = 0u; pi < p_count; pi++) {
            let prim_idx = temp_prim_list[pi];
            let op = u32(primitives[prim_idx].size_and_op.w);
            if (op != 0u) {
                has_csg_op = true;
                break;
            }
        }
        if (has_csg_op) {
            // For CSG-involved blocks, prefer correctness over local list culling.
            block_prim_info[b_ptr].offset = 0u;
            block_prim_info[b_ptr].count = ALL_PRIMS_SENTINEL;
            active_blocks[b_ptr] = packed_id;
            atomicAdd(&counters[4], 1u);
            return;
        }

        let prim_cap = arrayLength(&global_prim_indices);
        if (prim_cap < p_count) {
            block_prim_info[b_ptr].offset = 0u;
            block_prim_info[b_ptr].count = ALL_PRIMS_SENTINEL;
            active_blocks[b_ptr] = packed_id;
            atomicAdd(&counters[4], 1u);
            return;
        }

        let p_offset = atomicAdd(&global_counter[0], p_count);
        if (p_offset >= prim_cap || p_offset + p_count > prim_cap) {
            block_prim_info[b_ptr].offset = 0u;
            block_prim_info[b_ptr].count = ALL_PRIMS_SENTINEL;
            active_blocks[b_ptr] = packed_id;
            atomicAdd(&counters[4], 1u);
            return;
        }

        block_prim_info[b_ptr].offset = p_offset;
        block_prim_info[b_ptr].count = p_count;
        for (var pi = 0u; pi < p_count; pi++) {
            global_prim_indices[p_offset + pi] = temp_prim_list[pi];
        }
        active_blocks[b_ptr] = packed_id;
    }
}
