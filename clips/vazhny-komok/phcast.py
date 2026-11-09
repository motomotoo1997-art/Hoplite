from ink3d import *
from ink3d import _TIME


def blink(t, rate=0.29, ph=0.1):
    b = (t * rate + ph) % 1.0
    return 1.0 if b < 0.022 else 0.0


def ik_out(root, target, l1, l2, side):
    j1, e = ik(root, target, l1, l2, 1)
    j2, _ = ik(root, target, l1, l2, -1)
    return (j1 if (j1[0] - root[0]) * side >= (j2[0] - root[0]) * side else j2), e


def tube(pts, ws):
    n = len(pts); L = []; R = []; dirs = []
    for i in range(n):
        if i == 0: d = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        elif i == n - 1: d = (pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
        else: d = (pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1])
        l = math.hypot(*d) or 1; d = (d[0] / l, d[1] / l); dirs.append(d)
        nx, ny = -d[1], d[0]
        L.append((pts[i][0] + nx * ws[i] / 2, pts[i][1] + ny * ws[i] / 2)); R.append((pts[i][0] - nx * ws[i] / 2, pts[i][1] - ny * ws[i] / 2))
    tip = (pts[-1][0] + dirs[-1][0] * ws[-1] * 0.45, pts[-1][1] + dirs[-1][1] * ws[-1] * 0.45)
    st = (pts[0][0] - dirs[0][0] * ws[0] * 0.45, pts[0][1] - dirs[0][1] * ws[0] * 0.45)
    return smooth_path(L + [tip] + R[::-1] + [st], close=True)


def fluffy(cx, cy, rx, ry, n=22, amp=0.07, seed=0, t=0.0, wob=0.0):
    pts = []
    for i in range(n):
        a = i / n * math.tau
        k = 1 + amp * (0.6 + 0.4 * hash01(i + seed)) * (1 if i % 2 else -0.4) + wob * math.sin(a * 3 + t * 6)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    return smooth_path(pts, close=True)


# ====================================================================== КОМОК — the fat boss cat
KOM0 = dict(sq=1.0, lean=0.0, tilt=0.0, turn=0.0, eye=0.55, look=(0.0, 0.0), mouth='w', mo=0.0, brow=0.0,
            pl=(-70.0, -70.0), pr=(70.0, -70.0), tail=1.0, tailwag=0.4, ears=0.0, shades=0.0, chain=1.0, puff=0.0,
            blush=0.0, sweat=0.0, glare=0.0, legs=0.0, crown=0.0, cap=0.0, step=0.0, hold='', tlen=1.0)


def kom(**kw):
    d = dict(KOM0); d.update(kw); return d


def _kom_head(c, p, t, scale=1.0):
    fx = p['turn'] * 22
    for side in (-1, 1):
        c.save(); c.translate(side * 70 + fx * 0.2, -58); c.rotate(side * (14 + p['ears'] * 40))
        ear = smooth_path([(-30, 26), (-12, -18), (0 + side * 2, -58), (14, -18), (30, 26)], close=True)
        ink(c, ear, 'l', 5, 'm', side * 6, 6)
        c.drawPath(smooth_path([(-14, 18), (side * 2, -34), (14, 18)], close=True), P(RED, 200))
        for k in range(3): c.drawLine(-6 + k * 6, 14, -4 + k * 7 + side * 3, -10, inkp(2, dev=0.6))
        c.restore()
    head = fluffy(fx * 0.15, 0, 118, 92, 26, 0.06, 3, t)
    ink(c, head, 'l', 5.5, 'm', 12, 10)
    for k in (-1, 0, 1):  # tabby forehead marks
        c.drawPath(smooth_path([(fx + k * 22, -86), (fx + k * 18, -66), (fx + k * 20, -50)]), inkp(4, dev=0.8))
    muz = union(ellipse_path(fx - 26, 28, 36, 26), ellipse_path(fx + 26, 28, 36, 26), ellipse_path(fx, 48, 24, 18))
    ink(c, muz, 'w', 3.5)
    if p['blush'] > 0:
        for side in (-1, 1):
            r = skia.Rect(fx + side * 70 - 24, 10, fx + side * 70 + 24, 30)
            c.drawOval(r, P(RED, int(140 * p['blush'])))
            for k in range(4): c.drawLine(r.left() + 8 + k * 10, r.top() + 2, r.left() + 2 + k * 10, r.bottom() - 2, inkp(2, RED_D, dev=0.4))
    # eyes: smug half-lids, red slit irises
    b = blink(t, 0.27, 0.4)
    op = clamp(p['eye'] * (1 - b))
    for side in (-1, 1):
        ex, ey = fx + side * 44 * (1 - 0.15 * p['turn'] * side), -12
        rx, ry = 30 * (1 - 0.22 * p['turn'] * side), 26
        if op < 0.08:
            c.drawPath(smooth_path([(ex - rx, ey + 4), (ex, ey + 12), (ex + rx, ey + 4)]), inkp(6))
            continue
        shp = ellipse_path(ex, ey, rx, ry)
        c.drawPath(shp, P(WHITE))
        c.save(); c.clipPath(shp, skia.ClipOp.kIntersect, True)
        lx, ly = p['look']
        ix, iy = ex + lx * rx * 0.35, ey + 4 + ly * 7
        c.drawCircle(ix, iy, 20, P(RED))
        c.drawCircle(ix, iy, 20, P(shader=tone_shader(4.0, RED_D)))
        c.drawOval(skia.Rect(ix - 4, iy - 17, ix + 4, iy + 17), P(INK))
        c.drawCircle(ix - 8, iy - 8, 5, P(WHITE))
        lid = ey - ry + (1 - op) * (2 * ry) + 2
        tilt = -p['brow'] * 10
        yl = lid + (tilt if side > 0 else -tilt * 0.3); yr = lid + (-tilt * 0.3 if side > 0 else tilt)
        c.drawPath(poly_path([(ex - rx - 6, ey - ry - 40), (ex + rx + 6, ey - ry - 40), (ex + rx + 6, yr if side > 0 else yl), (ex - rx - 6, yl if side > 0 else yr)]), P(PAPER))
        c.drawPath(poly_path([(ex - rx - 6, ey - ry - 40), (ex + rx + 6, ey - ry - 40), (ex + rx + 6, yr if side > 0 else yl), (ex - rx - 6, yl if side > 0 else yr)]), P(shader=tone_shader(2.6)))
        c.restore()
        c.drawPath(shp, inkp(4.5))
        yl2 = ey - ry + (1 - op) * (2 * ry) + 2
        c.drawLine(ex - rx - 4, yl2 + (-p['brow'] * 10 if side < 0 else 0), ex + rx + 4, yl2 + (-p['brow'] * 10 if side > 0 else 0), inkp(8))
        if p['glare'] > 0:
            c.drawCircle(ex, ey, rx + 10, P(RED, int(160 * p['glare']), blur=10))
    # nose + mouth
    nose = smooth_path([(fx - 12, 10), (fx + 12, 10), (fx, 22)], close=True)
    c.drawPath(nose, P(INK))
    m, mo = p['mouth'], p['mo']
    if mo > 0.05 or m in ('open', 'o', 'roar'):
        o = max(mo, 0.4)
        wd, hh = (14, 14 + 16 * o) if m == 'o' else (28, 12 + 30 * o)
        mp = smooth_path([(fx - wd, 30), (fx, 34), (fx + wd, 30), (fx + wd * 0.6, 30 + hh), (fx - wd * 0.6, 30 + hh)], close=True)
        c.drawPath(mp, P(INK))
        c.save(); c.clipPath(mp, skia.ClipOp.kIntersect, True); c.drawOval(skia.Rect(fx - wd * 0.6, 30 + hh * 0.55, fx + wd * 0.6, 30 + hh * 1.5), P(RED)); c.restore()
        for side in (-1, 1): c.drawPath(poly_path([(fx + side * wd * 0.8, 29), (fx + side * wd * 0.45, 29), (fx + side * wd * 0.62, 44)]), P(WHITE))
    elif m == 'smirk':
        c.drawPath(smooth_path([(fx - 20, 34), (fx, 36), (fx + 24, 24)]), inkp(4.5))
    else:
        c.drawPath(smooth_path([(fx - 22, 30), (fx - 11, 38), (fx, 26)]), inkp(4.5))
        c.drawPath(smooth_path([(fx, 26), (fx + 11, 38), (fx + 22, 30)]), inkp(4.5))
    tw = kick(t, 10) * 4
    for side in (-1, 1):
        for k in range(3):
            y0 = 26 + k * 8
            c.drawPath(smooth_path([(fx + side * 40, y0), (fx + side * 90, y0 - 4 + k * 4 - tw), (fx + side * 140, y0 - 12 + k * 12 - tw * 1.5)]), inkp(2.4, dev=0.5))
    if p['shades'] > 0.01:
        c.save(); c.translate(fx, -12 - (1 - p['shades']) * 200)
        for side in (-1, 1):
            g = smooth_path([(side * 6, -20), (side * 82, -24), (side * 78, 10), (side * 44, 22), (side * 12, 8)], close=True)
            c.drawPath(g, P(INK))
            c.drawLine(side * 30, -10, side * 54, -16, P(WHITE, 220, stroke=5))
        c.drawLine(-8, -16, 8, -16, inkp(6))
        c.restore()
    if p['cap'] > 0.01:  # backwards red cap
        c.save(); c.translate(fx * 0.4, -78 - (1 - p['cap']) * 260); c.rotate(-6)
        cap = smooth_path([(-92, 10), (-80, -50), (0, -74), (80, -50), (92, 10)], close=True)
        ink(c, cap, 'r', 5, 'rd', 10, 8)
        ink(c, smooth_path([(-92, 6), (-150, 18), (-150, 34), (-86, 26)], close=True), 'r', 4.5)
        c.restore()
    if p['crown'] > 0.01:
        c.save(); c.translate(fx * 0.5, -96 - (1 - p['crown']) * 260); c.rotate(-8)
        cr = poly_path([(-48, 0), (-56, -52), (-26, -24), (0, -66), (26, -24), (56, -52), (48, 0)])
        ink(c, cr, 'w', 5, 'l', 8, 6)
        for x in (-56, 0, 56): c.drawCircle(x, -52 if x else -66, 8, P(RED))
        c.restore()


def draw_komok(c, p, t):
    """origin = floor under body centre. ~420 tall."""
    sq = p['sq']
    c.save()
    c.scale(1 / math.sqrt(max(0.3, sq)), sq)
    # tail (behind)
    tu = p['tail']
    pts = []
    for i in range(9):
        u = i / 8
        ang = math.radians(-160 + 70 * (1 - tu) * u - 80 * tu * u + math.sin(t * 4 - u * 3) * 16 * p['tailwag'] * u)
        if i == 0: x, y = 110, -110
        else: x, y = pts[-1][0] - math.cos(ang) * 30 * p['tlen'], pts[-1][1] + math.sin(ang) * 30 * p['tlen']
        pts.append((x, y))
    tail = tube(pts, [60 - 14 * (i / 8) for i in range(9)])
    ink(c, tail, 'm', 5, 'd', 8, 6)
    for i in (3, 5, 7): c.drawLine(pts[i][0] - 22, pts[i][1] + 4, pts[i][0] + 22, pts[i][1] - 4, inkp(5))
    # feet
    lg = p['legs']; st = p['step']
    for side in (-1, 1):
        lift = max(0, math.sin(st * math.pi * 2 + (0 if side < 0 else math.pi))) * 26 * (1 if st else 0)
        foot = ellipse_path(side * 66, -18 - lift, 46, 24)
        ink(c, foot, 'w', 4.5, 'l', 6, 6)
        for k in (-1, 1): c.drawLine(side * 66 + k * 12, -30 - lift, side * 66 + k * 12, -10 - lift, inkp(2.5))
    # body ball
    c.save(); c.rotate(p['lean'] * 0.4)
    puff = p['puff']
    body = fluffy(0, -175, 168 * (1 + 0.08 * puff), 160 * (1 + 0.06 * puff), 30, 0.05 + 0.08 * puff, 9, t, 0.01 * puff)
    ink(c, body, 'l', 6, 'm', 22, 18)
    belly = fluffy(0, -150, 98, 108, 18, 0.05, 2)
    ink(c, belly, 'w', 3.5)
    for side in (-1, 1):  # tabby side stripes
        for k in range(3):
            y0 = -250 + k * 40
            c.drawPath(smooth_path([(side * 164, y0), (side * 132, y0 + 8), (side * 112, y0 + 24)]), inkp(5))
    # chain (white links with ink) + red pendant
    if p['chain'] > 0.01:
        n = 11
        for k in range(n):
            u = k / (n - 1)
            x = lerp(-110, 110, u); y = -258 + 70 * math.sin(math.pi * u)
            c.save(); c.translate(x, y); c.rotate(70 if k % 2 else 0)
            ink(c, rrect_path(-11, -7, 11, 7, 6), 'w', 3.5)
            c.restore()
        c.save(); c.translate(0, -180); c.rotate(6 * math.sin(t * 3))
        pend = smooth_path([(-24, -20), (24, -20), (0, 30)], close=True)
        ink(c, pend, 'r', 4.5, 'rd', 6, 6)
        c.restore()
    # arms (paws)
    for side, key in ((-1, 'pl'), (1, 'pr')):
        root = (side * 96, -210)
        tgt = p[key]
        j, e = ik_out(root, tgt, 70, 66, side)
        arm = tube([root, j, e], [50, 42, 38])
        ink(c, arm, 'l', 5, 'm', 6, 6)
        paw = ellipse_path(e[0], e[1], 30, 26)
        ink(c, paw, 'w', 4.5)
        for k in (-1, 0, 1): c.drawLine(e[0] + k * 9, e[1] + 8, e[0] + k * 9, e[1] + 22, inkp(2.5))
        if p['hold'] and side > 0: hold_item(c, p['hold'], e, t)
    c.restore()
    # head
    c.save(); c.translate(0, -360); c.rotate(p['tilt'])
    _kom_head(c, p, t)
    c.restore()
    if p['sweat'] > 0:
        for k in range(2):
            yy = -470 + ((t * 120 + k * 60) % 110)
            ink(c, smooth_path([(150, yy - 18), (160, yy + 6), (140, yy + 6)], close=True), 'w', 3)
    c.restore()


def hold_item(c, item, e, t):
    c.save(); c.translate(e[0], e[1] - 10)
    if item == 'lid':
        c.rotate(-20); ink(c, ellipse_path(0, 0, 62, 16), 'l', 5, 'm', 0, 6); ink(c, rrect_path(-10, -30, 10, -12, 6), 'k', 3)
    elif item == 'sock':
        c.rotate(30); ink(c, smooth_path([(-18, -60), (18, -60), (18, 0), (40, 18), (30, 34), (-12, 24), (-18, 0)], close=True), 'w', 4.5)
        for k in range(3): c.drawLine(-18, -50 + k * 10, 18, -50 + k * 10, P(RED, stroke=4))
    elif item == 'spoon':
        c.rotate(-40); c.drawLine(0, 0, 0, -90, inkp(8)); ink(c, ellipse_path(0, -100, 16, 22), 'w', 4)
    c.restore()


# ====================================================================== ДЕД ВАЛЕРА
VAL0 = dict(lean=0.0, tilt=0.0, turn=0.0, eye=1.0, look=(0.0, 0.0), brow=0.0, mouth='flat', mo=0.0, vow='a', hip=(0.0, 0.0),
            lf=(-50.0, 0.0), rf=(50.0, 0.0), lh=(-100.0, -330.0), rh=(100.0, -330.0), hk_l='open', hk_r='open', prop='', glasses=1.0,
            sweat=0.0, hair=0.0, shades=0.0, chain=0.0, blush=0.0, cap=0.0, slip=0.0)


def val(**kw):
    d = dict(VAL0); d.update(kw); return d


def _hand(c, pos, ang, kind, s=1.0):
    c.save(); c.translate(*pos); c.rotate(ang); c.scale(s, s)
    if kind == 'point':
        ink(c, rrect_path(-12, -18, 22, 18, 10), 'w', 4)
        ink(c, tube([(16, -10), (58, -12)], [14, 12]), 'w', 3.5)
    elif kind == 'fist':
        ink(c, rrect_path(-12, -20, 24, 20, 12), 'w', 4)
        for k in range(3): c.drawLine(16, -12 + k * 10, 24, -12 + k * 10, inkp(2.5))
    elif kind == 'thumb':
        ink(c, rrect_path(-12, -20, 24, 20, 12), 'w', 4)
        ink(c, tube([(0, -18), (2, -52)], [14, 13]), 'w', 3.5)
    else:
        for k, a in enumerate((-30, -10, 10, 30)):
            r = math.radians(a)
            ink(c, tube([(10, 0), (14 + math.cos(r) * 34, math.sin(r) * 34)], [13, 11]), 'w', 3)
        ink(c, tube([(4, -14), (-6, -36)], [13, 12]), 'w', 3)
        ink(c, ellipse_path(6, 0, 20, 19), 'w', 4)
    c.restore()


def _val_head(c, p, t):
    fx = p['turn'] * 16
    for side in (-1, 1): ink(c, ellipse_path(side * 66 - fx * 0.2, 6, 14, 22), 'w', 4, 'l', side * 4, 4)
    head = smooth_path([(-64, -40), (-62, 22), (-48, 64), (-20, 90), (0, 94), (20, 90), (48, 64), (62, 22), (64, -40), (48, -90), (0, -108), (-48, -90)], close=True)
    ink(c, head, 'w', 5.5, 'l', 12, 10)
    c.drawPath(smooth_path([(-30, -90), (-6, -100), (20, -96)]), P(WHITE, 220, stroke=6))  # bald shine
    for side in (-1, 1):  # side hair tufts
        hp_ = []
        for k in range(7):
            u = k / 6
            hp_.append((side * (62 + 14 * (k % 2) + p['hair'] * 20 * (k % 2)), -50 + u * 60))
        ink(c, smooth_path([(side * 58, -56)] + hp_ + [(side * 58, 14)], close=True), 'm', 4)
    b = blink(t, 0.33, 0.7)
    op = clamp(p['eye'] * (1 - b))
    for side in (-1, 1):
        ex, ey = fx + side * 28, -8
        if op > 0.1:
            c.drawOval(skia.Rect(ex - 13, ey - 13 * op, ex + 13, ey + 13 * op), P(WHITE))
            lx, ly = p['look']
            c.drawCircle(ex + lx * 5, ey + ly * 4, 6.5 * min(1, op + 0.3), P(INK))
            c.drawOval(skia.Rect(ex - 13, ey - 13 * op, ex + 13, ey + 13 * op), inkp(3))
        else:
            c.drawLine(ex - 12, ey + 2, ex + 12, ey + 2, inkp(4))
        br = p['brow']
        c.save(); c.translate(ex, ey - 30 - br * 9); c.rotate((br * -10 if br > 0 else -br * 18) * side * -1 if br < 0 else br * -10 * side)
        ink(c, fluffy(0, 0, 24, 9, 12, 0.18, side + 3), 'k', 0)
        c.restore()
    if p['glasses'] > 0.01:
        for side in (-1, 1):
            c.drawCircle(fx + side * 28, -8, 24, inkp(4.5))
            c.drawLine(fx + side * 28 - 12, -22, fx + side * 28 - 2, -28, P(WHITE, 200, stroke=4))
        c.drawLine(fx - 4, -10, fx + 4, -10, inkp(4))
        for side in (-1, 1): c.drawLine(fx + side * 52, -12, side * 64, -6, inkp(4))
    if p['shades'] > 0.01:
        c.save(); c.translate(fx, -8 - (1 - p['shades']) * 200)
        for side in (-1, 1): c.drawPath(smooth_path([(side * 4, -16), (side * 56, -18), (side * 52, 14), (side * 8, 12)], close=True), P(INK))
        c.restore()
    nose = smooth_path([(fx + 2, -8), (fx + 16, 22), (fx + 22, 38), (fx + 6, 46), (fx - 12, 40), (fx - 6, 22)], close=True)
    ink(c, nose, 'w', 4, 'l', 6, 4)
    if p['blush'] > 0:
        for side in (-1, 1): c.drawOval(skia.Rect(fx + side * 40 - 16, 30, fx + side * 40 + 16, 44), P(RED, int(150 * p['blush'])))
    m, mo = p['mouth'], p['mo']
    my = 72
    if mo > 0.05 or m in ('open', 'shout', 'o'):
        o = max(mo, 0.35)
        v = p['vow']
        wd = {'o': 14, 'u': 11, 'e': 26}.get(v, 22) if m != 'shout' else 28
        hh = 8 + 30 * o
        mp = smooth_path([(fx - wd, my), (fx + wd, my), (fx + wd * 0.6, my + hh), (fx - wd * 0.6, my + hh)], close=True)
        c.drawPath(mp, P(INK))
        c.save(); c.clipPath(mp, skia.ClipOp.kIntersect, True); c.drawOval(skia.Rect(fx - wd * 0.6, my + hh * 0.5, fx + wd * 0.6, my + hh * 1.4), P(RED)); c.restore()
    else:
        cur = {'smile': 8, 'frown': -8, 'flat': 0, 'smirk': 3}.get(m, 0)
        c.drawPath(smooth_path([(fx - 20, my + 4 - cur * 0.3), (fx, my + 4 + cur), (fx + 20, my + 4 - cur * 0.3)]), inkp(4))
    # big walrus moustache (moves with speech)
    mlift = -6 * mo
    for side in (-1, 1):
        ms = smooth_path([(fx, 48), (fx + side * 30, 44 + mlift), (fx + side * 58, 58 + mlift), (fx + side * 66, 80 + mlift), (fx + side * 44, 72 + mlift), (fx + side * 20, 66 + mlift), (fx, 62)], close=True)
        ink(c, ms, 'd', 4)
    if p['cap'] > 0.01:
        c.save(); c.translate(fx * 0.3, -86 - (1 - p['cap']) * 260)
        ink(c, smooth_path([(-70, 14), (-62, -38), (0, -58), (62, -38), (70, 14)], close=True), 'k', 4)
        c.drawLine(-60, -6, 60, -6, P(WHITE, stroke=5))
        c.restore()
    if p['sweat'] > 0:
        for k in range(2):
            yy = -60 + ((t * 140 + k * 50) % 90)
            ink(c, smooth_path([(76, yy - 16), (84, yy + 4), (68, yy + 4)], close=True), 'w', 3)


def _slipper(c, e, side):
    c.save(); c.translate(e[0], e[1]); c.scale(side, 1)
    ink(c, smooth_path([(-30, 0), (-30, -16), (10, -26), (54, -16), (60, 0)], close=True), 'r', 4.5, 'rd', 0, 6)
    c.drawLine(-10, -22, 20, -22, P(WHITE, stroke=4))
    c.restore()


def draw_valera(c, p, t):
    """origin = floor between feet. ~860 tall."""
    hx, hy = p['hip']; hip = (hx, -420 + hy)
    for side, key in ((-1, 'lf'), (1, 'rf')):
        root = (hip[0] + side * 34, hip[1])
        ft = p[key]
        j, e = ik_out(root, (ft[0], ft[1] - 16), 212, 208, side)
        leg = tube([root, j, e], [70, 54, 40])
        ink(c, leg, 'k', 4.5)
        q = tube([root, j, e], [6, 6, 6]); qq = skia.Path(q)
        for off in (-18, -8, 2):  # three side stripes
            c.save(); c.translate(side * off * 0.4 + side * 10, 0)
            c.drawPath(smooth_path([root, j, e]), P(WHITE, stroke=3.5)); c.restore()
        _slipper(c, (e[0], e[1] + 16), side)
    c.save(); c.translate(*hip); c.rotate(p['lean'])
    tank = smooth_path([(-70, 20), (-74, -80), (-66, -190), (-40, -250), (-26, -280), (26, -280), (40, -250), (66, -190), (74, -80), (70, 20), (0, 34)], close=True)
    belly = ellipse_path(10, -60, 82, 86)
    tank = union(tank, belly)
    ink(c, tank, 'w', 5, 'l', 14, 10)
    c.drawPath(smooth_path([(-26, -280), (0, -238), (26, -280)]), inkp(4))
    c.drawCircle(18, -70, 4, P(INK))
    c.drawRect(skia.Rect(-76, 6, 76, 40), P(INK)); c.drawLine(-76, 18, 76, 18, P(WHITE, stroke=3))
    if p['chain'] > 0.01:
        for k in range(12):
            u = k / 11; x = lerp(-30, 30, u); y = -270 + 70 * math.sin(math.pi * u)
            c.drawCircle(x, y, 7, P(WHITE)); c.drawCircle(x, y, 7, inkp(2.5))
    # neck + head
    c.drawRect(skia.Rect(-22, -310, 22, -270), P(WHITE)); c.drawLine(-22, -310, -22, -274, inkp(4)); c.drawLine(22, -310, 22, -274, inkp(4))
    c.save(); c.translate(0, -390); c.rotate(p['tilt'])
    _val_head(c, p, t)
    c.restore()
    for side, key, hk in ((-1, 'lh', 'hk_l'), (1, 'rh', 'hk_r')):
        root = (side * 62, -248)
        j, e = ik_out(root, p[key], 150, 142, side)
        arm = tube([root, j, e], [34, 28, 26])
        ink(c, arm, 'w', 4.5, 'l', 6, 4)
        for k in range(4):  # arm hair hatch
            u = 0.2 + k * 0.18; px = lerp(j[0], e[0], u); py = lerp(j[1], e[1], u)
            c.drawLine(px - 4, py - 4, px + 4, py + 2, inkp(1.8, dev=0.4))
        ang = math.degrees(math.atan2(e[1] - j[1], e[0] - j[0]))
        hp = (e[0] + math.cos(math.radians(ang)) * 18, e[1] + math.sin(math.radians(ang)) * 18)
        if p['prop'] and side > 0: val_prop(c, p['prop'], hp, ang, t)
        _hand(c, hp, ang, p[hk], 1.0)
    c.restore()


def val_prop(c, prop, hp, ang, t):
    c.save(); c.translate(*hp)
    if prop == 'paper':
        c.rotate(-8); ink(c, rrect_path(-20, -130, 150, 40, 4), 'w', 4, 'l', 10, 6)
        for k in range(8): c.drawLine(0, -110 + k * 18, 130 - 40 * (k % 3), -110 + k * 18, inkp(3, dev=0.6))
        c.drawRect(skia.Rect(4, -124, 70, -96), P(RED))
    elif prop == 'torch':
        c.rotate(ang)
        ink(c, rrect_path(0, -16, 90, 16, 6), 'k', 4)
        ink(c, poly_path([(90, -22), (118, -30), (118, 30), (90, 22)]), 'w', 4)
    elif prop == 'plate':
        c.rotate(-4)
        ink(c, ellipse_path(40, 0, 90, 20), 'w', 4.5, 'l', 0, 6)
        ink(c, fluffy(40, -12, 40, 16, 12, 0.1, 4), 'd', 4)
    elif prop == 'cup':
        ink(c, rrect_path(-6, -70, 54, 0, 8), 'w', 4.5, 'l', 6, 4)
        c.drawRect(skia.Rect(-6, -50, 54, -36), P(RED))
    elif prop == 'phone':
        c.rotate(ang - 90)
        ink(c, rrect_path(-26, -50, 26, 50, 8), 'k', 4)
    c.restore()


# ====================================================================== ШКЕТ — mouse sidekick
SHK0 = dict(lean=0.0, tilt=0.0, mouth='grin', mo=0.0, lh=(-50, -90), rh=(50, -90), lf=(-20, 0), rf=(20, 0), hk='open', prop='', shades=1.0, jump=0.0)


def shk(**kw):
    d = dict(SHK0); d.update(kw); return d


def draw_shket(c, p, t):
    """origin = floor. ~260 tall."""
    c.save(); c.translate(0, -p['jump'])
    pts = [(30, -60), (80, -50), (110, -90), (100, -130)]
    c.drawPath(smooth_path(pts), inkp(5))
    for side, key in ((-1, 'lf'), (1, 'rf')):
        root = (side * 16, -70)
        j, e = ik_out(root, p[key], 40, 38, side)
        ink(c, tube([root, j, e], [18, 14, 12]), 'p', 3.5)
        ink(c, ellipse_path(e[0] + side * 8, e[1] - 4, 18, 8), 'w', 3)
    c.save(); c.translate(0, -70); c.rotate(p['lean'])
    body = smooth_path([(-40, 0), (-44, -60), (-26, -110), (26, -110), (44, -60), (40, 0)], close=True)
    ink(c, body, 'r', 4.5, 'rd', 8, 6)
    c.drawPath(smooth_path([(-20, -100), (0, -70), (20, -100)]), inkp(3))
    for side, key in ((-1, 'lh'), (1, 'rh')):
        root = (side * 34, -96)
        j, e = ik_out(root, p[key], 38, 36, side)
        ink(c, tube([root, j, e], [16, 14, 12]), 'p', 3.5)
        ink(c, ellipse_path(e[0], e[1], 11, 10), 'w', 3)
        if side > 0 and p['prop'] == 'phone':
            c.save(); c.translate(e[0], e[1] - 20); c.rotate(-10); ink(c, rrect_path(-16, -30, 16, 30, 5), 'k', 3)
            c.drawCircle(0, -18, 4, P(RED)); c.restore()
    c.save(); c.translate(0, -150); c.rotate(p['tilt'])
    for side in (-1, 1):
        ink(c, ellipse_path(side * 52, -52, 44, 44), 'p', 4.5, 'm', side * 6, 6)
        c.drawOval(skia.Rect(side * 52 - 26, -76, side * 52 + 26, -28), P(RED, 170))
    head = smooth_path([(-50, -30), (-40, -60), (0, -70), (40, -60), (50, -30), (40, 10), (60, 34), (0, 40), (-50, 20)], close=True)
    ink(c, head, 'p', 4.5, 'l', 6, 6)
    c.drawCircle(64, 32, 9, P(INK))
    for k in range(3): c.drawLine(56, 36 + k * 4, 100, 30 + k * 10, inkp(1.8, dev=0.4))
    if p['shades'] > 0:
        c.drawPath(smooth_path([(-40, -26), (36, -30), (34, -6), (0, -2), (-36, -6)], close=True), P(INK))
        c.drawLine(-20, -22, 0, -24, P(WHITE, stroke=3))
    mo = p['mo']
    if mo > 0.05 or p['mouth'] == 'grin':
        mp = smooth_path([(-6, 12), (40, 10), (30, 22 + 18 * mo), (0, 22 + 14 * mo)], close=True)
        c.drawPath(mp, P(INK)); c.drawRect(skia.Rect(8, 10, 20, 18), P(WHITE))
    c.restore()
    c.restore()
    c.restore()


# ====================================================================== props / set pieces
def vacuum(c, t, spin=0.0, led=1.0, rider=False):
    body = ellipse_path(0, -40, 170, 52)
    side_ = rrect_path(-170, -40, 170, -6, 20)
    ink(c, union(side_, ellipse_path(0, -6, 170, 46)), 'm', 5)
    ink(c, body, 'w', 5, 'l', 0, 12)
    c.drawOval(skia.Rect(-60, -62, 60, -30), inkp(3.5))
    c.drawCircle(80, -50, 10, P(RED, int(255 * led)))
    c.drawCircle(80, -50, 22, P(RED, int(120 * led), blur=8))
    for k in range(3):  # brush
        a = spin + k * 2.09
        c.drawLine(120, 0, 120 + math.cos(a) * 50, 0 + math.sin(a) * 14, inkp(3))


def sock(c, s=1.0, rot=0.0):
    c.save(); c.rotate(rot); c.scale(s, s)
    ink(c, smooth_path([(-22, -80), (22, -80), (22, 0), (54, 22), (40, 44), (-14, 30), (-22, 0)], close=True), 'w', 5)
    for k in range(3): c.drawLine(-22, -66 + k * 12, 22, -66 + k * 12, P(RED, stroke=5))
    c.drawPath(smooth_path([(-8, 18), (0, 10), (10, 24)]), inkp(3))
    c.restore()


def backpack(c, t, open_=0.0, wob=0.0):
    c.save(); c.rotate(wob)
    bag = smooth_path([(-110, 0), (-120, -150), (-90, -250), (90, -250), (120, -150), (110, 0)], close=True)
    ink(c, bag, 'm', 5.5, 'd', 14, 10)
    flap = smooth_path([(-96, -230 - 50 * open_), (0, -270 - 70 * open_), (96, -230 - 50 * open_), (90, -150 + 40 * open_), (-90, -150 + 40 * open_)], close=True)
    ink(c, flap, 'l', 5)
    ink(c, rrect_path(-70, -110, 70, -30, 10), 'l', 4.5)
    c.drawRect(skia.Rect(-40, -80, 40, -64), P(RED))
    c.restore()


def cup_saucer(c, wob=0.0):
    c.save(); c.rotate(wob)
    ink(c, ellipse_path(0, 0, 80, 16), 'w', 4.5, 'l', 0, 6)
    cup = smooth_path([(-50, -90), (50, -90), (40, -6), (-40, -6)], close=True)
    ink(c, cup, 'w', 5, 'l', 10, 0)
    c.drawPath(smooth_path([(50, -76), (82, -56), (46, -30)]), inkp(9))
    c.drawRect(skia.Rect(-46, -60, 46, -44), P(RED))
    for k in range(3):
        u = (_TIME[0] * 0.6 + k / 3) % 1
        c.drawPath(smooth_path([(-20 + k * 20, -100 - 80 * u), (-30 + k * 20 + 10 * math.sin(u * 8), -130 - 80 * u), (-20 + k * 20, -160 - 80 * u)]), inkp(3, a=int(255 * (1 - u))))
    c.restore()


def draw_komok_top(c, p, t):
    """top-down view (for overhead cameras). origin = body centre on floor; +y = towards cat's front."""
    st = p.get('step', 0.0)
    for side in (-1, 1):
        for fb in (-1, 1):
            ph = st * math.pi * 2 + (0 if side * fb > 0 else math.pi)
            ink(c, ellipse_path(side * 120, fb * 90 + 26 * math.sin(ph), 40, 30), 'w', 4)
    pts = [(0, -150)]
    for i in range(1, 8):
        u = i / 7
        pts.append((60 * math.sin(t * 3 + u * 3) * u, -150 - 40 * i))
    ink(c, tube(pts, [56 - 5 * i for i in range(8)]), 'm', 5)
    ink(c, fluffy(0, 0, 170, 180, 30, 0.05, 9, t), 'l', 6, 'm', 14, 14)
    for k in range(4): c.drawPath(smooth_path([(-90, -90 + k * 50), (0, -80 + k * 50), (90, -90 + k * 50)]), inkp(5))
    ink(c, fluffy(0, 170, 110, 90, 20, 0.06, 3, t), 'l', 5.5, 'm', 8, 8)
    for side in (-1, 1):
        ink(c, smooth_path([(side * 40, 110), (side * 92, 70), (side * 100, 140)], close=True), 'l', 5)
    c.drawCircle(0, 260, 10, P(INK))
