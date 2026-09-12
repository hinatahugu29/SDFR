# Mirror Blend のプレビューを、外形寸法ではなく「くびれの形」と「法線の連続性」で見る。
#
# 既存の test_mirror_blend_preview_fix / _gap / _axes はバウンディングボックスの幅しか
# 測っていない。継ぎ目が埋まるのは2つのコピーの「間」なので、外形寸法は変わらない。
# Radius 1.0 / Offset 1.24 では Blend 0 から 1.23 まで幅が 1ミリも動かず、
# ユーザーが実際に見ている「くっつくかどうか」をテストが一切見ていなかった。
#
# ここでは
#   1. ミラー軸に沿って等値面の半径を刻み、最終メッシュの厳密式と突き合わせる（形）
#   2. |c| = Blend/2 の前後で法線の角度差を測る（陰影）
# を見る。2 は V16.2.2 で実際に出ていた欠陥で、k*h*(1-h) の clamp 境界で
# 微分が -1 から 0 へ飛び、最大84度の折り目になっていた。
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

R, OFF = 1.0, 1.24
NORMAL_TOL_DEG = 2.0      # 折り目とみなす閾値。修正前は 52-84 度あった。
NECK_TOL = 0.12           # くびれ形状の許容誤差。修正前は 0.10-0.29 で、これを超えていた。

ok = True
def check(label, cond, detail=""):
    global ok
    if not cond: ok = False
    print("  [%s] %s%s" % ("OK" if cond else "NG", label, ("  -> " + detail) if detail else ""))

def smin0(a, b, k):
    """common.wgsl の apply_profile_union / profile 0（最終メッシュ側）。"""
    h = min(max(0.5 + 0.5 * (b - a) / k, 0.0), 1.0)
    return (b + (a - b) * h) - k * h * (1.0 - h)

def d_mesh(x, y, z, k):
    d1 = math.sqrt((x - OFF) ** 2 + y * y + z * z) - R
    d2 = math.sqrt((x + OFF) ** 2 + y * y + z * z) - R
    return smin0(d1, d2, k)

def seam_cut(c, k):
    """shader.py の sdf_mirror_seam_cut と同じ式にすること。"""
    u = min(abs(c) / (k * 0.5), 1.0)
    w = 1.0 - u
    return k * 0.25 * w * w

def d_prev(x, y, z, k):
    lx = abs(x) - OFF
    return math.sqrt(lx * lx + y * y + z * z) - R - seam_cut(x, k)

def radius_at(f, x, k):
    lo, hi = 0.0, 6.0
    if f(x, 0.0, lo, k) > 0.0:
        return 0.0
    for _ in range(60):
        m = (lo + hi) * 0.5
        if f(x, 0.0, m, k) <= 0.0: lo = m
        else: hi = m
    return lo

def grad(f, x, y, z, k, e=1e-6):
    return ((f(x+e,y,z,k)-f(x-e,y,z,k))/(2*e),
            (f(x,y+e,z,k)-f(x,y-e,z,k))/(2*e),
            (f(x,y,z+e,k)-f(x,y,z-e,k))/(2*e))

def angle(a, b):
    na = math.sqrt(sum(t*t for t in a)); nb = math.sqrt(sum(t*t for t in b))
    d = sum(p*q for p, q in zip(a, b)) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))

BLENDS = (0.5, 1.0, 1.23, 1.59, 2.0)

print("=== 継ぎ目中心は厳密解と一致するか ===")
for k in BLENDS:
    m = d_mesh(0.0, 0.0, 0.0, k); p = d_prev(0.0, 0.0, 0.0, k)
    check("blend=%.2f の x=0" % k, abs(m - p) < 1e-9, "mesh=%+.6f preview=%+.6f" % (m, p))

print("=== くびれの形（等値面半径の最大誤差）===")
for k in BLENDS:
    worst = 0.0
    for i in range(61):
        x = 3.5 * i / 60
        worst = max(worst, abs(radius_at(d_prev, x, k) - radius_at(d_mesh, x, k)))
    check("blend=%.2f" % k, worst <= NECK_TOL, "最大誤差 %.4f (許容 %.2f)" % (worst, NECK_TOL))

print("=== 法線が |c| = Blend/2 で飛ばないか（折り目）===")
for k in BLENDS:
    x = k * 0.5
    lx = abs(x) - OFF
    inner = R * R - lx * lx
    if inner <= 0.0:
        check("blend=%.2f" % k, True, "その位置に表面が無い")
        continue
    z = math.sqrt(inner)
    a = angle(grad(d_prev, x - 1e-3, 0.0, z, k), grad(d_prev, x + 1e-3, 0.0, z, k))
    check("blend=%.2f" % k, a <= NORMAL_TOL_DEG, "角度差 %.1f 度 (許容 %.1f)" % (a, NORMAL_TOL_DEG))

print("RESULT: %s" % ("ALL PASS" if ok else "FAILED"))
sys.exit(0 if ok else 1)
