import math, json, bisect
import numpy as np
import skia

W, H = 1920, 1080
OUT = (40, 22, 20)      # warm ink outline
LW = 5.0

# ---------------------------------------------------------------- rhythm
_B = json.load(open('/tmp/ph/beats.json'))['beats']
_spb = float(np.median(np.diff(_B)))
# extend detected beats both ways so every time has a beat index
BEATS = [ _B[0] - _spb * k for k in range(30, 0, -1) ] + _B + [ _B[-1] + _spb * k for k in range(1, 30) ]
BEAT0 = 30  # index of first detected beat in BEATS
SPB = _spb
_env = json.load(open('/tmp/ph/beats.json'))
_ENV_T = np.array(_env['env_t']); _LOW = np.array(_env['low']); _RMS = np.array(_env['rms'])


def beat_pos(t):
    """continuous beat index (0 = first detected beat)."""
    i = bisect.bisect_right(BEATS, t) - 1
    i = max(0, min(i, len(BEATS) - 2))
    a, b = BEATS[i], BEATS[i + 1]
    return (i - BEAT0) + (t - a) / (b - a)


def beat_time(n):
    i = int(math.floor(n)) + BEAT0
    i = max(0, min(i, len(BEATS) - 2))
    f = n - math.floor(n)
    return BEATS[i] + f * (BEATS[i + 1] - BEATS[i])


def snap_beat(t):
    return beat_time(round(beat_pos(t)))


def kick(t, decay=7.0):
    return math.exp(-(beat_pos(t) % 1.0) * decay)


def bar_kick(t, decay=4.0):
    return math.exp(-(beat_pos(t) % 4.0) * decay)


def low(t):
    return float(np.interp(t, _ENV_T, _LOW))


def loud(t):
    return float(np.interp(t, _ENV_T, _RMS))


# ---------------------------------------------------------------- math
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_back(x, s=2.2):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out_cubic(x):
    x = clamp(x); return 1 - (1 - x) ** 3


def ease_out_expo(x):
    x = clamp(x); return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def ease_in_out(x):
    x = clamp(x); return x * x * (3 - 2 * x)


def ease_in_cubic(x):
    x = clamp(x); return x ** 3


def ease_out_elastic(x):
    x = clamp(x)
    if x in (0, 1): return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi / 3)) + 1


def noise(t, seed=0.0):
    return (math.sin(t * 1.7 + seed) * 0.5 + math.sin(t * 3.1 + seed * 2.3) * 0.3 + math.sin(t * 7.3 + seed * 4.1) * 0.2)


def hash01(i):
    x = math.sin(i * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


def mix_pose(a, b, p):
    out = {}
    for k, va in a.items():
        vb = b.get(k, va)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool):
            out[k] = va + (vb - va) * p
        elif isinstance(va, tuple) and isinstance(vb, tuple):
            out[k] = tuple(x + (y - x) * p for x, y in zip(va, vb))
        else:
            out[k] = vb if p > 0.5 else va
    for k, vb in b.items():
        if k not in out: out[k] = vb
    return out


def keyed(t, keys, snap=0.16, ease=ease_out_back):
    """keys: sorted [(time, pose)]. Snappy hit into each pose (whip accents)."""
    if t <= keys[0][0]: return dict(keys[0][1])
    i = bisect.bisect_right([k[0] for k in keys], t) - 1
    if i == 0: prev = keys[0][1]
    else: prev = keys[i - 1][1]
    t0, cur = keys[i]
    if i == 0: return dict(cur)
    p = ease((t - t0) / snap)
    return mix_pose(prev, cur, p)


def smooth_keys(t, keys):
    """camera-style eased interpolation between [(time, tuple)]."""
    if t <= keys[0][0]: return keys[0][1]
    for i in range(len(keys) - 1):
        t0, a = keys[i][0], keys[i][1]; t1, b = keys[i + 1][0], keys[i + 1][1]
        if t < t1:
            mode = keys[i + 1][2] if len(keys[i + 1]) > 2 else 'io'
            x = (t - t0) / max(1e-6, t1 - t0)
            e = {'io': ease_in_out, 'snap': ease_out_expo, 'back': ease_out_back, 'lin': lambda v: v, 'out': ease_out_cubic, 'in': ease_in_cubic}[mode](x)
            return tuple(lerp(u, v, e) for u, v in zip(a, b))
    return keys[-1][1]


# ---------------------------------------------------------------- paint helpers
def C(c, a=255):
    if isinstance(c, str):
        c = c.lstrip('#'); c = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    if len(c) == 4: return skia.Color(*c)
    return skia.Color(int(c[0]), int(c[1]), int(c[2]), int(a))


def shade(c, f):
    if isinstance(c, str):
        c = c.lstrip('#'); c = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    if f >= 1: return tuple(min(255, int(v + (255 - v) * (f - 1))) for v in c[:3])
    return tuple(int(v * f) for v in c[:3])


def P(color=None, a=255, stroke=0, shader=None, blur=0, blend=None, cap='round'):
    p = skia.Paint(AntiAlias=True)
    if color is not None: p.setColor(C(color, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == 'round' else skia.Paint.kButt_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if shader is not None: p.setShader(shader)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend == 'add': p.setBlendMode(skia.BlendMode.kPlus)
    elif blend == 'screen': p.setBlendMode(skia.BlendMode.kScreen)
    elif blend == 'mult': p.setBlendMode(skia.BlendMode.kMultiply)
    if a != 255 and color is None: p.setAlphaf(a / 255)
    return p


def lgrad(p0, p1, cols, pos=None):
    return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], [C(c) for c in cols], pos)


def rgrad(c, r, cols, pos=None):
    return skia.GradientShader.MakeRadial(skia.Point(*c), max(1e-3, r), [C(c2) for c2 in cols], pos)


def shape(c, path, fill, ow=LW, grad=None, outline=OUT):
    if grad is not None: c.drawPath(path, P(shader=grad))
    else: c.drawPath(path, P(fill))
    if ow: c.drawPath(path, P(outline, stroke=ow))


def ellipse_path(cx, cy, rx, ry):
    p = skia.Path(); p.addOval(skia.Rect(cx - rx, cy - ry, cx + rx, cy + ry)); return p


def rrect_path(x0, y0, x1, y1, r):
    p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect(x0, y0, x1, y1), r, r)); return p


def poly_path(pts, close=True):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    if close: p.close()
    return p


def smooth_path(pts, close=False):
    """Catmull-Rom through points -> cubic path."""
    p = skia.Path(); n = len(pts)
    p.moveTo(*pts[0])
    rng = range(n) if close else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if (close or i > 0) else pts[i]
        p1 = pts[i % n]; p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (close or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        p.cubicTo(*c1, *c2, *p2)
    if close: p.close()
    return p


def union(*paths):
    r = paths[0]
    for q in paths[1:]: r = skia.Op(r, q, skia.PathOp.kUnion_PathOp) or r
    return r


def diff(a, b):
    return skia.Op(a, b, skia.PathOp.kDifference_PathOp) or a


def limb(c, pts, w, color, ow=LW):
    path = skia.Path(); path.moveTo(*pts[0])
    if len(pts) == 3:
        # rounded elbow
        path.quadTo(*pts[1], *pts[2]) if False else None
        path.lineTo(*pts[1]); path.lineTo(*pts[2])
    else:
        for q in pts[1:]: path.lineTo(*q)
    if ow: c.drawPath(path, P(OUT, stroke=w + 2 * ow))
    c.drawPath(path, P(color, stroke=w))
    return path


def ik(root, target, l1, l2, bend=1):
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = math.hypot(dx, dy)
    d = clamp(d, abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3)
    a = math.atan2(dy, dx)
    cosb = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    b = math.acos(clamp(cosb, -1, 1))
    ang = a - bend * b
    j = (root[0] + l1 * math.cos(ang), root[1] + l1 * math.sin(ang))
    # end clamped to reach
    e = (root[0] + d * math.cos(a), root[1] + d * math.sin(a))
    return j, e


def soft_shadow(c, x, y, rx, ry, a=90):
    c.drawOval(skia.Rect(x - rx, y - ry, x + rx, y + ry), P((10, 5, 15), a, blur=ry * 0.6 + 4))


# ---------------------------------------------------------------- fonts
FONT_BLACK = skia.Typeface.MakeFromFile('/usr/share/fonts/opentype/montserrat/Montserrat-Black.otf')
FONT_XB = skia.Typeface.MakeFromFile('/usr/share/fonts/opentype/montserrat/Montserrat-ExtraBold.otf')
_fcache = {}


def font(size, face=None):
    key = (int(size), id(face))
    if key not in _fcache:
        f = skia.Font(face or FONT_BLACK, int(size)); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True)
        _fcache[key] = f
    return _fcache[key]


def text_width(s, f):
    return f.measureText(s)


def draw_text(c, s, x, y, size, fill, stroke_col=OUT, stroke=0, align='c', face=None, a=255, shadow=0):
    f = font(size, face)
    w = f.measureText(s)
    ox = -w / 2 if align == 'c' else (-w if align == 'r' else 0)
    if shadow:
        c.drawString(s, x + ox + shadow * 0.6, y + shadow, f, P((0, 0, 0), int(a * 0.45), blur=shadow * 0.5))
    if stroke:
        c.drawString(s, x + ox, y, f, P(stroke_col, a, stroke=stroke))
    c.drawString(s, x + ox, y, f, P(fill, a))
    return w


def ik_out(root, target, l1, l2, side):
    """2-bone IK choosing the solution whose middle joint points away from the body."""
    j1, e = ik(root, target, l1, l2, 1)
    j2, _ = ik(root, target, l1, l2, -1)
    return (j1 if (j1[0] - root[0]) * side >= (j2[0] - root[0]) * side else j2), e
