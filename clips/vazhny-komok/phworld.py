from phcast import *
from ink3d import _TIME, _PL, NEAR

# ====================================================================== generic 3D helpers
def box(c, cam, x0, x1, y0, y1, z0, z1, front='w', top='l', side_='m', w=5.0, deco=None):
    """axis aligned box; y0 top (more negative), y1 bottom. draws visible faces."""
    faces = []
    C_ = cam.C
    if C_[2] < z0: faces.append(('front', Plane(c, cam, (x0, y0, z0), (1, 0, 0), (0, 1, 0), (0, 0, x1 - x0, y1 - y0)), front, (x1 - x0, y1 - y0)))
    if C_[1] < y0: faces.append(('top', Plane(c, cam, (x0, y0, z0), (1, 0, 0), (0, 0, 1), (0, 0, x1 - x0, z1 - z0)), top, (x1 - x0, z1 - z0)))
    if C_[0] < x0: faces.append(('left', Plane(c, cam, (x0, y0, z0), (0, 0, 1), (0, 1, 0), (0, 0, z1 - z0, y1 - y0)), side_, (z1 - z0, y1 - y0)))
    if C_[0] > x1: faces.append(('right', Plane(c, cam, (x1, y0, z0), (0, 0, 1), (0, 1, 0), (0, 0, z1 - z0, y1 - y0)), side_, (z1 - z0, y1 - y0)))
    for name, pl, tone, (ww, hh) in faces:
        with pl as ok:
            if ok:
                r = rrect_path(0, 0, ww, hh, 2)
                ink(c, r, tone, w, None)
                if deco: deco(c, name, ww, hh)


def far_sky(c, cam, z=9000, moon=(1200, -2600), moon_r=900, sun_col=RED, night=True):
    with wall(c, cam, z, (-30000, -20000, 30000, 6000)) as pl:
        if not pl: return
        if night:
            prect(c, (-30000, -20000, 30000, 6000), P(INK))
            for i in range(160):
                x = -16000 + hash01(i * 3) * 32000; y = -12000 + hash01(i * 7) * 10000
                tw = 0.5 + 0.5 * math.sin(_TIME[0] * (1 + 2 * hash01(i)) + i)
                c.drawCircle(x, y, 10 + 18 * hash01(i * 11), P(WHITE, int(80 + 170 * tw)))
        else:
            prect(c, (-30000, -20000, 30000, 6000), P(PAPER))
            prect(c, (-30000, -20000, 30000, 6000), P(shader=tone_shader(2.6, INK, 6)))
        mx, my = moon
        c.drawCircle(mx, my, moon_r, P(sun_col))
        for k in range(5):  # phonk sun stripes
            yy = my + moon_r * 0.25 + k * moon_r * 0.15
            c.drawRect(skia.Rect(mx - moon_r, yy, mx + moon_r, yy + moon_r * 0.03 * (k + 1)), P(INK if night else PAPER))


def _bldg_img(seed, w, h, lit=0.3):
    def fn(cc):
        cc.drawRect(skia.Rect(0, 0, w, h), P(INK))
        cols = int(w / 110); rows = int(h / 140)
        for r in range(rows):
            for k in range(cols):
                hv = hash01(seed * 31 + r * 17 + k * 7)
                x = 30 + k * 110; y = 40 + r * 140
                if hv < lit:
                    cc.drawRect(skia.Rect(x, y, x + 64, y + 84), P(PAPER if hv > lit * 0.25 else RED))
                    cc.drawLine(x + 32, y, x + 32, y + 84, P(INK, stroke=5))
                else:
                    cc.drawRect(skia.Rect(x, y, x + 64, y + 84), P((40, 36, 40)))
        cc.drawRect(skia.Rect(0, 0, w, 24), P((60, 56, 60)))
    return fn


_IMG = {}


def plane_img(c, key, w, h, fn, res=0.5):
    if key not in _IMG:
        s = skia.Surface(max(1, int(w * res)), max(1, int(h * res))); cc = s.getCanvas(); cc.clear(skia.ColorTRANSPARENT)
        cc.scale(res, res); fn(cc); _IMG[key] = s.makeImageSnapshot()
    m = c.getTotalMatrix()
    # draw through a near-clipped path (plane-local coords are offset by the caller's translate)
    tx, ty = _OFF[-1] if _OFF else (0, 0)
    if _PL:
        a, b, cc = _PL[-1].A[2]
        if min(a * x + b * y + cc for x in (tx, tx + w) for y in (ty, ty + h)) > NEAR:
            c.drawImageRect(_IMG[key], skia.Rect(0, 0, w, h), skia.SamplingOptions(skia.FilterMode.kLinear)); return
    c.save(); c.translate(-tx, -ty)
    pimg(c, _IMG[key], (tx, ty, tx + w, ty + h))
    c.restore()


_OFF = []


def at(c, x, y):
    class _A:
        def __enter__(s_): c.save(); c.translate(x, y); _OFF.append((x, y)); return s_
        def __exit__(s_, *a): _OFF.pop(); c.restore()
    return _A()


def city(c, cam, rows=((6000, 0.25), (3500, 0.3), (2200, 0.35)), base_y=600, night=True):
    for zi, (z, lit) in enumerate(rows):
        with wall(c, cam, z, (-20000, -9000, 20000, 4000)) as pl:
            if not pl: continue
            x = -14000; i = 0
            while x < 14000:
                w = 900 + hash01(i + zi * 50) * 1300; h = 1800 + hash01(i * 5 + zi * 9) * 3800 * (1 + zi * 0.2)
                with at(c, x, base_y - h):
                    plane_img(c, ('b', zi, i), w, h, _bldg_img(i + zi * 100, w, h, lit), 0.25)
                x += w + 60 + hash01(i * 3) * 200; i += 1
            prect(c, (-20000, base_y, 20000, 4000), P(INK))


# ====================================================================== apartment
ROOM = dict(back=1300, left=-1900, right=1900, ceil=-1750, win=(-560, 560, -1380, -560))


def _wallpaper(c, x0, y0, x1, y1, seed=0):
    c.drawRect(skia.Rect(x0, y0, x1, y1), P(PAPER))
    c.drawRect(skia.Rect(x0, y0, x1, y1), P(shader=tone_shader(2.4, INK, 1.4)))
    x = x0 + 60
    while x < x1:
        c.drawLine(x, y0, x, y1, P(INK, 70, stroke=4)); x += 160
    gy = y0 + 100
    while gy < y1 - 200:  # little diamond motif
        gx = x0 + 140 + (80 if int((gy - y0) / 220) % 2 else 0)
        while gx < x1:
            c.drawPath(poly_path([(gx, gy - 18), (gx + 14, gy), (gx, gy + 18), (gx - 14, gy)]), P(INK, 120)); gx += 160
        gy += 220
    c.drawRect(skia.Rect(x0, y1 - 90, x1, y1), P(INK))


def _tiles(c, x0, y0, x1, y1, seed=0):
    c.drawRect(skia.Rect(x0, y0, x1, y1), P(PAPER))
    c.drawRect(skia.Rect(x0, y0, x1, y1), P(shader=tone_shader(2.0, INK, 1.4)))
    for gy in range(int(y1) - 1500, int(y1) - 700, 100):
        for gx in range(int(x0), int(x1), 100):
            c.drawRect(skia.Rect(gx + 4, gy + 4, gx + 96, gy + 96), P(WHITE if (gx // 100 + gy // 100) % 2 else PAPER_D))
            if (gx // 100 + gy // 100) % 7 == 0: c.drawRect(skia.Rect(gx + 4, gy + 4, gx + 96, gy + 96), P(RED))
    c.drawRect(skia.Rect(x0, y1 - 90, x1, y1), P(INK))


def _floorimg(c, w, h, kitchen):
    c.drawRect(skia.Rect(0, 0, w, h), P(PAPER_D))
    if kitchen:
        for gy in range(0, int(h), 200):
            for gx in range(0, int(w), 200):
                if (gx // 200 + gy // 200) % 2: c.drawRect(skia.Rect(gx, gy, gx + 200, gy + 200), P(INK))
        return
    x = 0; k = 0
    while x < w:
        if k % 2: c.drawRect(skia.Rect(x, 0, x + 160, h), P(shader=tone_shader(2.6, INK, 2.0)))
        c.drawLine(x, 0, x, h, P(INK, 150, stroke=5))
        y = (k * 370) % 900
        while y < h: c.drawLine(x, y, x + 160, y, P(INK, 150, stroke=4)); y += 900
        x += 160; k += 1


def apartment(c, cam, st=None):
    st = st or {}
    R = ROOM
    night = st.get('night', True)
    far_sky(c, cam, 9000, moon=st.get('moon', (900, -3300)), moon_r=st.get('moon_r', 1100))
    city(c, cam)
    wx0, wx1, wy0, wy1 = R['win']
    # back wall with window hole
    with wall(c, cam, R['back'], (-4000, -3000, 4000, 400)) as pl:
        if pl:
            wallp = diff(rrect_path(-4000, -3000, 4000, 0, 0), rrect_path(wx0, wy0, wx1, wy1, 0))
            c.save(); c.clipPath(wallp, skia.ClipOp.kIntersect, True)
            with at(c, -4000, -3000): plane_img(c, ('wp', st.get('wall', 'room')), 8000, 3000, lambda cc: (cc.translate(4000, 3000), (_tiles if st.get('wall') == 'kitchen' else _wallpaper)(cc, -4000, -3000, 4000, 0)), 0.5)
            if st.get('shadow_cat', 0) > 0:  # giant cat shadow on wall
                a = int(200 * st['shadow_cat'])
                c.save(); c.translate(st.get('shadow_x', 0), -40); c.scale(2.6, 2.6)
                c.drawPath(union(ellipse_path(0, -180, 170, 160), ellipse_path(0, -380, 120, 95), poly_path([(-110, -420), (-80, -520), (-40, -450)]), poly_path([(110, -420), (80, -520), (40, -450)])), P(INK, a))
                c.restore()
            c.restore()
            fr = rrect_path(wx0, wy0, wx1, wy1, 0)
            c.drawPath(fr, inkp(28, WHITE, dev=0)); c.drawPath(fr, inkp(6))
            c.drawLine((wx0 + wx1) / 2, wy0, (wx0 + wx1) / 2, wy1, inkp(22, WHITE, dev=0)); c.drawLine((wx0 + wx1) / 2, wy0, (wx0 + wx1) / 2, wy1, inkp(5))
            c.drawLine(wx0, wy0 + 260, wx1, wy0 + 260, inkp(18, WHITE, dev=0)); c.drawLine(wx0, wy0 + 260, wx1, wy0 + 260, inkp(5))
            # radiator
            ink(c, rrect_path(-420, -440, 420, -150, 10), 'w', 5, 'l', 0, 14)
            for k in range(12): c.drawLine(-380 + k * 70, -420, -380 + k * 70, -170, inkp(4))
    # windowsill box
    box(c, cam, wx0 - 120, wx1 + 120, wy1 - 30, wy1 + 30, R['back'] - 220, R['back'], 'w', 'w', 'l', 5)
    # curtains (planes at back - 40)
    sw = st.get('csway', 0.0)
    for s_, x in ((-1, wx0 - 60), (1, wx1 + 60)):
        with wall(c, cam, R['back'] - 60) as pl:
            if pl:
                pts = [(x - s_ * 0, wy0 - 160), (x + s_ * 260, wy0 - 160)]
                for k in range(7):
                    u = k / 6
                    pts.append((x + s_ * 260 - s_ * 260 * u + sw * u * s_ + 18 * math.sin(_TIME[0] * 1.5 + k), -40))
                cur = poly_path(pts)
                ink(c, cur, 'r', 5, 'rd', 24 * s_, 0)
                for k in range(4): c.drawLine(x + s_ * (40 + k * 60), wy0 - 150, x + s_ * (40 + k * 60) + sw * 0.5 * s_, -50, inkp(3, RED_D))
        c.drawLine(0, 0, 0, 0, P(INK))
    with wall(c, cam, R['back'] - 60) as pl:
        if pl: c.drawLine(wx0 - 360, wy0 - 170, wx1 + 360, wy0 - 170, inkp(14))
    # side walls
    with side(c, cam, R['left'], (-2000, -3000, R['back'], 0)) as pl:
        if pl:
            with at(c, -2000, -3000): plane_img(c, ('wpl', st.get('wall', 'room')), R['back'] + 2000, 3000, lambda cc: (cc.translate(2000, 3000), (_tiles if st.get('wall') == 'kitchen' else _wallpaper)(cc, -2000, -3000, R['back'], 0)), 0.5)
            ink(c, rrect_path(-200, -1500, 500, 0, 0), 'k', 6)  # doorway to dark hall
            c.drawRect(skia.Rect(-200, -1500, 500, 0), P(shader=tone_shader(5.6, (60, 56, 60), 1.0)))
    with side(c, cam, R['right'], (-2000, -3000, R['back'], 0)) as pl:
        if pl:
            with at(c, -2000, -3000): plane_img(c, ('wpr', st.get('wall', 'room')), R['back'] + 2000, 3000, lambda cc: (cc.translate(2000, 3000), (_tiles if st.get('wall') == 'kitchen' else _wallpaper)(cc, -2000, -3000, R['back'], 0)), 0.5)
            ink(c, rrect_path(-200, -1300, 500, -700, 4), 'w', 6, 'l', 0, 0)  # picture of a fish
            ink(c, smooth_path([(-60, -1000), (150, -1090), (330, -1000), (150, -910)], close=True), 'r', 5)
            ink(c, poly_path([(320, -1000), (420, -1070), (420, -930)]), 'r', 5)
    # floor
    with floor(c, cam, 0, (R['left'], -3000, R['right'], R['back'])) as pl:
        if pl:
            with at(c, R['left'], -3000): plane_img(c, ('floor', st.get('wall', 'room')), R['right'] - R['left'], R['back'] + 3000, lambda cc: _floorimg(cc, R['right'] - R['left'], R['back'] + 3000, st.get('wall') == 'kitchen'), 0.4)
            rug = fluffy(0, 300, 900, 520, 30, 0.02, 7)
            if st.get('rug', 1):
                ppath(c, rug, P(RED)); ppath(c, fluffy(0, 300, 560, 300, 30, 0.02, 11), P(shader=tone_shader(4.0, RED_D, 3)))
                b = st.get('rug_bump', 0)
                if b: c.drawOval(skia.Rect(-120, 220, 160, 380), P(INK, int(70 * b), blur=20))
            for (fx, fz, a) in st.get('prints', []):
                c.save(); c.translate(fx, fz)
                c.drawCircle(0, 0, 34, P(RED, a)); [c.drawCircle(math.cos(q) * 46, math.sin(q) * 46 - 20, 15, P(RED, a)) for q in (-2.4, -1.9, -1.2, -0.7)]
                c.restore()
    # ceiling (only when the camera is below it)
    if cam.C[1] > R['ceil'] + 20:
        with Plane(c, cam, (0, R['ceil'], 0), (1, 0, 0), (0, 0, 1), (R['left'], -3000, R['right'], R['back'])) as pl:
            if pl:
                prect(c, (R['left'], -3000, R['right'], R['back']), P(PAPER))
                prect(c, (R['left'], -3000, R['right'], R['back']), P(shader=tone_shader(4.0, INK, 2.0)))


def lamp(c, cam, x, z, sw=0.0, on=1.0):
    with board(c, cam, (x, ROOM['ceil'], z)) as b:
        if b:
            c.save(); c.rotate(sw)
            c.drawLine(0, 0, 0, 520, inkp(5))
            sh = smooth_path([(-130, 680), (-90, 540), (90, 540), (130, 680)], close=True)
            ink(c, sh, 'r', 6, 'rd', 10, 0)
            c.drawCircle(0, 690, 34, P(WHITE)); c.drawCircle(0, 690, 34, inkp(4))
            c.restore()


def armchair(c, cam, x, z, s=1.0):
    with board(c, cam, (x, 0, z), s) as b:
        if b:
            ink(c, rrect_path(-300, -780, 300, -340, 80), 'm', 6, 'd', 14, 12)
            ink(c, rrect_path(-340, -420, 340, -140, 60), 'l', 6, 'm', 0, 14)
            for sx in (-1, 1): ink(c, rrect_path(sx * 300 - 80, -560, sx * 300 + 80, -120, 60), 'm', 6, 'd', 10, 10)
            for sx in (-260, 220): c.drawRect(skia.Rect(sx, -120, sx + 40, 0), P(INK))


def wardrobe(c, cam, x0, x1, z0, z1, h=2100):
    def deco(cc, name, ww, hh):
        if name == 'front':
            cc.drawLine(ww / 2, 40, ww / 2, hh - 40, inkp(5))
            for xx in (ww / 2 - 40, ww / 2 + 40): cc.drawCircle(xx, hh / 2, 14, P(INK))
            hatch(cc, rrect_path(30, 30, ww - 30, hh - 30, 4), 80, 26, 2.0, 140)
    box(c, cam, x0, x1, -h, 0, z0, z1, 'l', 'l', 'm', 6, deco)


def table(c, cam, x0, x1, z0, z1, h=760, cloth=True):
    def deco(cc, name, ww, hh):
        if name == 'top' and cloth:
            k = 0; x = 0
            while x < ww:
                cc.drawRect(skia.Rect(x, 0, x + 80, hh), P(RED, 255 if k % 2 else 0)); x += 80; k += 1
    box(c, cam, x0, x1, -h, -h + 40, z0, z1, 'w', 'w', 'l', 5, deco)
    for lx in (x0 + 30, x1 - 70):
        for lz in (z0 + 30, z1 - 60):
            box(c, cam, lx, lx + 40, -h + 40, 0, lz, lz + 30, 'k', 'k', 'k', 3)


# ====================================================================== chorus void stage
def void(c, cam, st=None):
    st = st or {}
    k = kick(_TIME[0], 5)
    with wall(c, cam, 8000, (-30000, -20000, 30000, 6000)) as pl:
        if pl:
            prect(c, (-30000, -20000, 30000, 6000), P(INK))
            sx, sy, sr = st.get('sun', (0, -2400, 2600))
            sr *= 1 + 0.03 * k
            c.drawCircle(sx, sy, sr, P(RED))
            for j in range(7):
                yy = sy + sr * 0.15 + j * sr * 0.12
                c.drawRect(skia.Rect(sx - sr, yy, sx + sr, yy + sr * 0.018 * (j + 1)), P(INK))
            # radiating print lines
            n = 48
            for i in range(n):
                a = i / n * math.tau + _TIME[0] * 0.05
                pline(c, sx + math.cos(a) * sr * 1.15, sy + math.sin(a) * sr * 1.15, sx + math.cos(a) * sr * 6, sy + math.sin(a) * sr * 6, P(WHITE, 40, stroke=30))
    with floor(c, cam, 0, (-12000, -12000, 12000, 8000)) as pl:
        if pl:
            prect(c, (-12000, -12000, 12000, 8000), P(INK))
            for x in range(-12000, 12001, 600): pline(c, x, -12000, x, 8000, P(WHITE, 90, stroke=8))
            off = (_TIME[0] * st.get('scroll', 0)) % 600
            for z in range(-12000, 8001, 600): pline(c, -12000, z - off, 12000, z - off, P(WHITE, 90, stroke=8))
            for (cx, cz, r, a) in st.get('drift', []):
                ppath(c, diff(ellipse_path(cx, cz, r + 17, r + 17), ellipse_path(cx, cz, r - 17, r - 17)), P(WHITE, a))


def smoke(c, cam, puffs):
    """puffs: list of (x,z,r,alpha) billboards on floor."""
    for (x, z, r, a) in sorted(puffs, key=lambda p: -depth_of(cam, (p[0], 0, p[1]))):
        with board(c, cam, (x, -r * 0.6, z)) as b:
            if b:
                pth = fluffy(0, 0, r, r * 0.8, 12, 0.14, int(x) % 13)
                c.drawPath(pth, P(WHITE, a)); c.drawPath(pth, inkp(4, a=a))
