from core import *

# ====================================================================== palette (manga print)
PAPER = (241, 235, 221)
PAPER_D = (214, 205, 188)
INK = (16, 13, 16)
RED = (226, 32, 44)
RED_D = (150, 16, 28)
WHITE = (255, 252, 244)
BOIL_FPS = 12


# ====================================================================== halftone tones
def _dot_tile(r, n=14, col=INK):
    a = np.zeros((n, n, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.sqrt((xx - n / 2 + 0.5) ** 2 + (yy - n / 2 + 0.5) ** 2)
    m = np.clip(r - d + 0.5, 0, 1)
    a[..., 0] = col[0]; a[..., 1] = col[1]; a[..., 2] = col[2]; a[..., 3] = (m * 255).astype(np.uint8)
    return skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType)


_TONE_IMG = {}
_TONE = {}


def tone_shader(r, col=INK, scale=1.0):
    key = (r, col, round(scale, 2))
    if key not in _TONE:
        if (r, col) not in _TONE_IMG: _TONE_IMG[(r, col)] = _dot_tile(r, 14, col)
        m = skia.Matrix(); m.setRotate(45); m.preScale(0.7 * scale, 0.7 * scale)
        _TONE[key] = _TONE_IMG[(r, col)].makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(skia.FilterMode.kLinear), m)
    return _TONE[key]


TONES = {'l': 2.6, 'm': 4.0, 'd': 5.6, 'x': 6.8}


def fill_tone(c, path, tone, base=PAPER, ts=1.0):
    """tone: 'w' white paper, 'l','m','d' halftone grey, 'k' ink, 'r' red, 'rl' red+tone, 'p' paper-dark."""
    if tone == 'k': c.drawPath(path, P(INK)); return
    if tone == 'r': c.drawPath(path, P(RED)); return
    if tone == 'w': c.drawPath(path, P(WHITE)); return
    if tone == 'p': c.drawPath(path, P(PAPER_D)); return
    if tone.startswith('r'):
        c.drawPath(path, P(RED))
        c.drawPath(path, P(shader=tone_shader(TONES.get(tone[1:], 4.0), RED_D, ts)))
        return
    c.drawPath(path, P(base))
    c.drawPath(path, P(shader=tone_shader(TONES[tone], INK, ts)))


# ====================================================================== boiled ink lines
_PE = {}
_TIME = [0.0]


def set_time(t): _TIME[0] = t


def boil_pe(dev=1.4, seg=9.0):
    seed = int(_TIME[0] * BOIL_FPS) % 6
    key = (seed, dev, seg)
    if key not in _PE:
        _PE[key] = skia.PathEffect.MakeCompose(skia.DiscretePathEffect.Make(seg, dev, seed * 7 + 1), skia.CornerPathEffect.Make(2.0))
    return _PE[key]


def inkp(w=5.0, col=INK, a=255, dev=1.4):
    p = P(col, a, stroke=w)
    if dev > 0: p.setPathEffect(boil_pe(dev))
    return p


def ink(c, path, tone='w', w=5.0, shadow=None, sdx=10, sdy=8, ts=1.0, dev=1.4, line=INK):
    """flat fill + halftone shadow cut + boiled outline."""
    fill_tone(c, path, tone, ts=ts)
    if shadow:
        c.save(); c.clipPath(path, skia.ClipOp.kIntersect, True)
        q = skia.Path(path); q.offset(sdx, sdy)
        inv = skia.Op(path, q, skia.PathOp.kDifference_PathOp)
        if inv is not None: fill_tone(c, inv, shadow, ts=ts)
        c.restore()
    if w: c.drawPath(path, inkp(w, line, dev=dev))


def hatch(c, path, ang=45, gap=9, w=2.0, a=255, col=INK):
    b = path.getBounds()
    c.save(); c.clipPath(path, skia.ClipOp.kIntersect, True)
    cx, cy = b.centerX(), b.centerY(); R = math.hypot(b.width(), b.height()) / 2 + 10
    c.translate(cx, cy); c.rotate(ang)
    p = inkp(w, col, a, dev=0.8)
    y = -R
    while y < R:
        c.drawLine(-R, y, R, y, p); y += gap
    c.restore()


def speed_lines(c, cx, cy, r0, r1, n=60, seed=0, a=255, col=INK, w=3.0):
    s = int(_TIME[0] * BOIL_FPS)
    for i in range(n):
        ang = hash01(i * 7 + seed + s * 13) * math.tau
        ra = r0 * (0.8 + 0.5 * hash01(i * 3 + s))
        ww = w * (0.5 + 1.5 * hash01(i * 11 + s))
        path = poly_path([(cx + math.cos(ang) * ra, cy + math.sin(ang) * ra), (cx + math.cos(ang + 0.012) * r1, cy + math.sin(ang + 0.012) * r1),
                          (cx + math.cos(ang - 0.012) * r1, cy + math.sin(ang - 0.012) * r1)])
        c.drawPath(path, P(col, a))
        if ww > 2.5: c.drawLine(cx + math.cos(ang) * ra, cy + math.sin(ang) * ra, cx + math.cos(ang) * r1, cy + math.sin(ang) * r1, P(col, a, stroke=ww * 0.4))


def lines_h(c, x0, x1, y0, y1, n=30, seed=0, col=INK, a=200):
    s = int(_TIME[0] * BOIL_FPS)
    for i in range(n):
        y = y0 + hash01(i * 5 + seed + s * 3) * (y1 - y0)
        l0 = x0 + hash01(i * 9 + s) * (x1 - x0) * 0.4
        c.drawLine(l0, y, x1 - hash01(i * 13 + s) * (x1 - x0) * 0.3, y, P(col, a, stroke=1 + 4 * hash01(i + s)))


# ====================================================================== 3D camera
class Cam3:
    def __init__(self, x=0.0, y=-500.0, z=-1400.0, yaw=0.0, pitch=0.0, roll=0.0, f=1300.0):
        self.x, self.y, self.z, self.yaw, self.pitch, self.roll, self.f = x, y, z, yaw, pitch, roll, f
        cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        cp_, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
        cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        Ry = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
        Rx = np.array([[1, 0, 0], [0, cp_, sp], [0, -sp, cp_]])
        Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
        self.R = Rz @ Rx @ Ry
        self.C = np.array([x, y, z], dtype=float)
        self.K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1.0]])

    def to_cam(self, p):
        return self.R @ (np.asarray(p, dtype=float) - self.C)

    def project(self, p):
        q = self.to_cam(p)
        if q[2] < 1: return None
        return (self.f * q[0] / q[2] + W / 2, self.f * q[1] / q[2] + H / 2, q[2])

    def right(self): return self.R[0]

    def down(self): return self.R[1]

    def fwd(self): return self.R[2]


NEAR = 40.0
_PL = []


def _front(r):
    """rect (l,t,r,b) intersected with the visible half-plane of the current plane -> path"""
    if not _PL: return rrect_path(r[0], r[1], r[2], r[3], 0)
    pl = _PL[-1]; a, b, cc = pl.A[2]
    poly = _clip_poly([(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])], a, b, cc, NEAR)
    return poly_path(poly) if len(poly) >= 3 else None


def prect(c, r, paint):
    p = _front(r)
    if p is not None: c.drawPath(p, paint)


def pline(c, x0, y0, x1, y1, paint):
    if _PL:
        a, b, cc = _PL[-1].A[2]
        d0 = a * x0 + b * y0 + cc - NEAR; d1 = a * x1 + b * y1 + cc - NEAR
        if d0 < 0 and d1 < 0: return
        if d0 < 0: s = d0 / (d0 - d1); x0, y0 = x0 + (x1 - x0) * s, y0 + (y1 - y0) * s
        elif d1 < 0: s = d0 / (d0 - d1); x1, y1 = x0 + (x1 - x0) * s, y0 + (y1 - y0) * s
    c.drawLine(x0, y0, x1, y1, paint)


def pimg(c, img, r):
    p = _front(r)
    if p is None: return
    m = skia.Matrix(); m.setRectToRect(skia.Rect(0, 0, img.width(), img.height()), skia.Rect(*r), skia.Matrix.kFill_ScaleToFit)
    c.drawPath(p, P(shader=img.makeShader(skia.TileMode.kClamp, skia.TileMode.kClamp, skia.SamplingOptions(skia.FilterMode.kLinear), m)))


def ppath(c, path, paint):
    p = _front(tuple(path.getBounds()))
    if p is None: return
    q = skia.Op(path, p, skia.PathOp.kIntersect_PathOp)
    if q is not None: c.drawPath(q, paint)


def _clip_poly(poly, a, b, cc, near):
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        dp = a * p[0] + b * p[1] + cc - near; dq = a * q[0] + b * q[1] + cc - near
        if dp >= 0: out.append(p)
        if (dp >= 0) != (dq >= 0):
            s = dp / (dp - dq); out.append((p[0] + (q[0] - p[0]) * s, p[1] + (q[1] - p[1]) * s))
    return out


class Plane:
    """context manager: draw in plane-local coordinates (u,v) -> world O + u*U + v*V."""

    def __init__(self, c, cam, O, U, V, ext=(-6000, -6000, 6000, 6000), clip=True):
        self.c, self.cam = c, cam
        A = cam.R @ np.column_stack([np.asarray(U, float), np.asarray(V, float), np.asarray(O, float) - cam.C])
        self.A = A
        Hm = cam.K @ A
        self.Hm = Hm
        self.depth = float(A[2, 2])
        a, b, cc = A[2]
        x0, y0, x1, y1 = ext
        self.poly = _clip_poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], a, b, cc, NEAR)
        self.ok = len(self.poly) >= 3
        self.clip = clip

    def __enter__(self):
        c = self.c; c.save()
        if not self.ok: return None
        m = skia.Matrix.MakeAll(*[float(v) for v in self.Hm.flatten()])
        c.concat(m)
        self.pp = poly_path(self.poly)
        if self.clip: c.clipPath(self.pp, skia.ClipOp.kIntersect, True)
        _PL.append(self)
        return self

    def __exit__(self, *a):
        if _PL and _PL[-1] is self: _PL.pop()
        self.c.restore()

    def local_scale(self):
        return self.cam.f / max(1.0, self.depth)


def wall(c, cam, z, ext=(-6000, -6000, 6000, 6000), x=0.0, y=0.0):
    return Plane(c, cam, (x, y, z), (1, 0, 0), (0, 1, 0), ext)


def floor(c, cam, y=0.0, ext=(-6000, -6000, 6000, 6000)):
    return Plane(c, cam, (0, y, 0), (1, 0, 0), (0, 0, 1), ext)


def side(c, cam, x, ext=(-6000, -6000, 6000, 6000)):
    """wall at world x; local u = world z, v = world y."""
    return Plane(c, cam, (x, 0, 0), (0, 0, 1), (0, 1, 0), ext)


def board(c, cam, pos, s=1.0, face_cam=True, yaw=0.0):
    """billboard standing at pos (feet). local y up = negative."""
    if face_cam:
        r = cam.right(); d = np.array([0.0, 1.0, 0.0])
        r = np.array([r[0], 0.0, r[2]]); r /= (np.linalg.norm(r) or 1)
        if yaw:
            ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            r = np.array([r[0] * ca - r[2] * sa, 0, r[0] * sa + r[2] * ca])
    else:
        ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        r = np.array([ca, 0, sa]); d = np.array([0.0, 1.0, 0.0])
    return Plane(c, cam, pos, r * s, d * s, clip=False)


def depth_of(cam, pos):
    return float(cam.to_cam(pos)[2])


def shadow_blob(c, cam, x, z, rx, a=120, y=0.0):
    with floor(c, cam, y) as pl:
        if pl: ppath(c, ellipse_path(x, z, rx, rx * 0.45), P(INK, a, blur=10))


def topdown(cam):
    return cam.pitch < -60
