from phworld import *
from phlyrics import *
from ink3d import _TIME, _PL
from phworld import at
from phcast import _slipper

# =========================================================================== animation helpers
def twos(t, fps=30):
    return math.floor(t * fps) / fps


def hits(t, times, seq, snap=0.12, before=None):
    i = bisect.bisect_right(times, t) - 1
    if i < 0: return dict(before if before is not None else seq[0])
    cur = seq[i % len(seq)]
    prev = seq[(i - 1) % len(seq)] if i > 0 else (before if before is not None else seq[0])
    return mix_pose(prev, cur, ease_out_back((t - times[i]) / snap))


def on_beats(t, t0, seq, every=1.0, snap=0.1):
    n0 = math.ceil(beat_pos(t0) - 0.1)
    k = int(math.floor((beat_pos(t) - n0) / every))
    if k < 0: return dict(seq[0])
    cur = seq[k % len(seq)]; prev = seq[(k - 1) % len(seq)] if k > 0 else seq[0]
    return mix_pose(prev, cur, ease_out_back((t - beat_time(n0 + k * every)) / snap))


def beats_in(t0, t1, every=1.0):
    n0 = math.ceil(beat_pos(t0) - 0.05); out = []; n = n0
    while beat_time(n) < t1: out.append(beat_time(n)); n += every
    return out


def sing(t, who):
    ws = WORDS[who]; ts = [x for x, _ in ws]
    i = bisect.bisect_right(ts, t) - 1
    if i < 0: return 0.0, 'a'
    x, v = ws[i]
    nxt = ts[i + 1] if i + 1 < len(ts) else x + 0.5
    dur = clamp(nxt - x, 0.12, 0.45); d = t - x
    if d > dur: return 0.0, v
    return clamp((1 - math.exp(-d / 0.03)) * (1 - (d / dur) ** 1.6)), v


def stepped(t, t0, t1, a, b, beat_every=0.5, frac=0.35):
    """beat-stepped interpolation: moves fast on each subdivision, holds the rest (phonk camera)."""
    ts = beats_in(t0, t1, beat_every)
    if not ts: return lerp(a, b, clamp((t - t0) / (t1 - t0)))
    n = len(ts); i = bisect.bisect_right(ts, t) - 1
    if i < 0: return a
    seg = SPB * beat_every
    u = (i + ease_out_expo(clamp((t - ts[i]) / (seg * frac)))) / n
    return lerp(a, b, clamp(u))


class Act:
    def __init__(self, pos, fn, shadow=150, s=1.0, yaw=0.0, face=True):
        self.pos, self.fn, self.shadow, self.s, self.yaw, self.face = pos, fn, shadow, s, yaw, face


def stage(c, cam, acts):
    for a in acts:
        if a.shadow and a.pos[1] > -5: shadow_blob(c, cam, a.pos[0], a.pos[2], a.shadow * a.s)
    for a in sorted(acts, key=lambda a: -depth_of(cam, a.pos)):
        with board(c, cam, a.pos, a.s, a.face, a.yaw) as b:
            if b: a.fn(c)


def KOM(t, p, flip=1):
    def f(c):
        c.save(); c.scale(flip, 1); draw_komok(c, p, t); c.restore()
    return f


def VAL(t, p, flip=1, singing=True):
    q = dict(p)
    if singing:
        mo, v = sing(t, 'val')
        if mo > 0.05: q.update(mouth='open', mo=mo, vow=v)

    def f(c):
        c.save(); c.scale(flip, 1); draw_valera(c, q, t); c.restore()
    return f


def SHK(t, p, flip=1, singing=True):
    q = dict(p)
    if singing:
        mo, _ = sing(t, 'shk')
        if mo > 0.05: q.update(mo=mo)

    def f(c):
        c.save(); c.scale(flip, 1); draw_shket(c, q, t); c.restore()
    return f


def K3(*keys):
    def cam(t):
        v = smooth_keys(t, list(keys))
        return Cam3(*v)
    return cam


def poof(c, cam, pos, t0, t, n=9, r=220):
    d = t - t0
    if d < 0 or d > 0.9: return
    for i in range(n):
        a = i / n * math.tau + hash01(i) * 0.5
        rr = r * ease_out_cubic(d / 0.5) * (0.6 + 0.6 * hash01(i * 3))
        x = pos[0] + math.cos(a) * rr; y = pos[1] - 200 + math.sin(a) * rr * 0.7; z = pos[2] - 40
        sz = 110 * (1 - d / 0.9) * (0.6 + 0.6 * hash01(i * 7))
        with board(c, cam, (x, y, z)) as b:
            if b:
                pth = fluffy(0, 0, sz, sz * 0.85, 10, 0.16, i)
                c.drawPath(pth, P(WHITE)); c.drawPath(pth, inkp(4))


def sfx(c, cam, pos, text, t0, t, size=260, col=WHITE, rot=-8, life=0.6):
    d = t - t0
    if d < 0 or d > life: return
    sc = ease_out_back(d / 0.12, 3) * (1 + 0.15 * d)
    a = int(255 * clamp((life - d) / 0.2))
    with board(c, cam, pos) as b:
        if b:
            c.save(); c.rotate(rot); c.scale(sc, sc)
            f = font(size, FONT_BLACK); w = f.measureText(text)
            c.drawString(text, -w / 2 + 14, 16, f, P(RED, a))
            c.drawString(text, -w / 2, 0, f, P(INK, a, stroke=size * 0.14))
            c.drawString(text, -w / 2, 0, f, P(col, a))
            c.restore()


# =========================================================================== shot system
class Shot:
    def __init__(self, t0, t1, draw, cam, trans='cut', shake=0.6, punch=0.03, inv=None, freeze=None, weave=1.0):
        self.t0, self.t1, self.draw, self.cam, self.trans, self.shake, self.punch = t0, t1, draw, cam, trans, shake, punch
        self.inv = inv or []; self.freeze = freeze; self.weave = weave


SHOTS = []


def shot(t0, t1, cam, snap_=True, **kw):
    def deco(f):
        a = (snap_beat(t0) if snap_ else t0) if t0 > 0 else 0.0
        SHOTS.append(Shot(a, t1, f, cam, **kw)); return f
    return deco


def T(i, j=0): return LINES[i]['times'][j]


# ============================================================ INTRO — city, night
def facade(c, cam, t, our=(0, -1000), lit_k=0, cat_sil=True):
    with wall(c, cam, 1500, (-8000, -9000, 8000, 800)) as pl:
        if not pl: return
        with at(c, -8000, -9000): plane_img(c, 'facade', 16000, 9800, _facade_img, 0.22)
        ox, oy = our
        # neighbour windows flick on with the vocal hits
        for i in range(lit_k):
            x = -2800 + (hash01(i * 7) * 14 // 1) * 400; y = -3600 + (hash01(i * 3) * 8 // 1) * 600
            c.drawRect(skia.Rect(x + 60, y + 100, x + 300, y + 420), P(PAPER))
        r = skia.Rect(ox - 240, oy - 330, ox + 240, oy + 100)
        c.drawRect(r, P(PAPER))
        c.drawCircle(ox + 120, oy - 180, 120, P(RED))
        if cat_sil:
            c.save(); c.translate(ox - 30, oy + 90); c.scale(0.55, 0.55)
            sil = union(ellipse_path(0, -170, 170, 160), ellipse_path(0, -360, 120, 92), poly_path([(-110, -400), (-74, -500), (-36, -430)]), poly_path([(110, -400), (74, -500), (36, -430)]))
            c.drawPath(sil, P(INK))
            pts = [(140, -100)] + [(160 + 60 * math.sin(t * 3 + u * 2) * u, -100 - u * 320) for u in (0.25, 0.5, 0.75, 1.0)]
            c.drawPath(tube(pts, [56, 52, 48, 44, 40]), P(INK))
            c.restore()
        c.drawRect(r, inkp(22, WHITE, dev=0)); c.drawRect(r, inkp(6))
        c.drawLine(ox, r.top(), ox, r.bottom(), inkp(14, WHITE, dev=0))


def _facade_img(cc):
    cc.drawRect(skia.Rect(0, 0, 16000, 9800), P(PAPER_D))
    cc.drawRect(skia.Rect(0, 0, 16000, 9800), P(shader=tone_shader(4.0, INK, 4)))
    for r in range(15):
        for k in range(40):
            x = k * 400; y = r * 600
            cc.drawRect(skia.Rect(x + 60, y + 100, x + 300, y + 420), P(INK))
            cc.drawRect(skia.Rect(x + 60, y + 100, x + 300, y + 420), P(PAPER_D, stroke=14))
            if (r + k) % 3 == 0:
                cc.drawRect(skia.Rect(x + 20, y + 330, x + 340, y + 470), P(PAPER))
                cc.drawRect(skia.Rect(x + 20, y + 330, x + 340, y + 470), P(INK, stroke=10))
                for q in range(6): cc.drawLine(x + 40 + q * 52, y + 340, x + 40 + q * 52, y + 460, P(INK, stroke=6))
        cc.drawLine(0, r * 600, 16000, r * 600, P(INK, stroke=12))
    for k in range(40): cc.drawLine(k * 400, 0, k * 400, 9800, P(INK, 120, stroke=8))


INTRO_HITS = [T(i, 3) for i in range(4)]


@shot(0, 8.95, K3((0, (0, -1400, -9000, 0, 6, 0, 1300)), (7.6, (0, -1050, -1600, 0, 1, 0, 1300), 'io'), (8.95, (0, -1000, 300, 0, 0, 0, 1300), 'in')), shake=0.1, weave=1.5)
def s_intro_city(c, cam, t):
    far_sky(c, cam, 12000, moon=(-2600, -5200), moon_r=1500)
    city(c, cam, ((9000, 0.2), (6500, 0.25)), base_y=900)
    facade(c, cam, t, (0, -1000), bisect.bisect_right(INTRO_HITS, t) * 5)
    with floor(c, cam, 800, (-20000, -20000, 20000, 1500)) as pl:
        if pl: prect(c, (-20000, -20000, 20000, 1500), P(INK))


def _room_cat(t, p=None):
    return Act((0, -590, 1180), KOM(t, kom(**(p or {}))), shadow=0, s=0.85)


HALL = [9.6, 11.2, 12.25]


@shot(8.95, 13.3, lambda t: Cam3(0, -140, stepped(t, 8.95, 13.3, -1700, -150, 1.0, 0.3), 0, 4 + 6 * ease_in_out((t - 9) / 4), 2 * math.sin(t * 2), 1100), trans='ink', shake=0.7, punch=0.05)
def s_hall(c, cam, t):
    apartment(c, cam, {'shadow_cat': 0.0})
    acts = [Act((-380, 0, -900), lambda c_: sock(c_, 1.4, -20), 40), Act((420, 0, -500), lambda c_: backpack(c_, t), 120),
            Act((-200, 0, 100), lambda c_: (_slipper(c_, (0, 0), 1), _slipper(c_, (90, 10), 1)), 60), _room_cat(t, dict(eye=0.0, tailwag=0.8))]
    stage(c, cam, acts)


DETAIL = beats_in(13.3, 15.55, 1.0)


def _detail_cam(t):
    i = max(0, bisect.bisect_right(DETAIL, t) - 1); lt = t - (DETAIL[i] if DETAIL else 13.3)
    k = [(140, -760, 760, -20, 8, -8, 1300), (-80, -880, 820, 4, -4, 6, 1300), (0, -840, 790, 0, -2, 0, 1300), (40, -900, 740, 8, 4, -4, 1300), (0, -880, 600, 0, 0, 0, 1300)][i % 5]
    return Cam3(k[0], k[1], k[2] + 60 * ease_out_cubic(lt / 0.5), k[3], k[4], k[5], k[6])


@shot(13.3, 15.55, _detail_cam, trans='cut', shake=0.8, punch=0.06, inv=DETAIL[1::2])
def s_details(c, cam, t):
    apartment(c, cam)
    i = max(0, bisect.bisect_right(DETAIL, t) - 1)
    p = [dict(eye=0.0, tailwag=2.0), dict(eye=0.0, pr=(80, -230)), dict(eye=0.0), dict(eye=0.0, tilt=-6), dict(eye=1.0, glare=1.0, look=(0, 0.3))][i % 5]
    stage(c, cam, [_room_cat(t, p)])


@shot(15.55, 17.41, K3((15.55, (0, -760, -400, 0, -4, 0, 1300)), (17.41, (0, -760, 100, 0, -4, 0, 1300), 'io')), trans='slam', shake=0.2, freeze=(15.9, 17.2))
def s_title(c, cam, t):
    apartment(c, cam)
    lamp(c, cam, 0, 700)
    stage(c, cam, [_room_cat(t, dict(eye=0.6, mouth='smirk', look=(0.2, 0.3), chain=1)),
                   Act((-850, 0, 700), VAL(t, val(eye=0.0, tilt=14, lean=-8, lh=(-120, -160), rh=(120, -160), prop='paper', mouth='open', mo=0.2), singing=False), 160, 0.85)])


# ============================================================ VERSE 1
def lookat(pos, tgt, roll=0.0, f=1300):
    dx, dy, dz = tgt[0] - pos[0], tgt[1] - pos[1], tgt[2] - pos[2]
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1
    return Cam3(pos[0], pos[1], pos[2], math.degrees(math.atan2(dx, dz)), math.degrees(math.asin(-dy / n)), roll, f)


def orbit(cx, cy, cz, r, yaw, y_off=0.0, pitch=0.0, f=1300, roll=0.0):
    a = math.radians(yaw)
    return Cam3(cx - math.sin(a) * r, cy + y_off, cz - math.cos(a) * r, yaw, pitch, roll, f)


@shot(T(4), T(5), lambda t: orbit(0, -820, 1180, 1500, lerp(-34, 22, ease_in_out((t - T(4)) / 2.6)), -60, -2, 1300), trans='ink', shake=0.5, punch=0.04)
def s_sill(c, cam, t):
    apartment(c, cam)
    lamp(c, cam, 0, 700)
    pz = on_beats(t, T(4), [kom(eye=0.55, mouth='smirk'), kom(eye=0.55, puff=1, tilt=6, mouth='smirk'), kom(eye=0.4, tilt=-4), kom(eye=0.55, puff=1, look=(0.6, 0.2))], 1.0)
    stage(c, cam, [_room_cat(twos(t), pz), Act((-850, 0, 700), VAL(t, val(eye=0.0, tilt=14, lean=-8, lh=(-120, -160), rh=(120, -160), prop='paper', mouth='open', mo=0.25), singing=False), 160, 0.85)])


def _tail_cam(t):
    u = ease_in_out((t - T(5, 1)) / 1.3)
    return lookat((380, -720, 150), (lerp(0, -120, u), lerp(-920, -1400, u), lerp(1180, 1000, u)), 0, 1150)


@shot(T(5), T(6), _tail_cam, trans='cut', shake=0.4)
def s_tail(c, cam, t):
    apartment(c, cam)
    tl = 1.0 + 2.6 * ease_out_back((t - T(5, 1)) / 0.5) if t > T(5, 1) else 1.0
    sw = 22 * math.sin((t - T(5, 3)) * 6) * math.exp(-(t - T(5, 3)) * 1.5) if t > T(5, 3) else 0
    lamp(c, cam, -120, 980, sw)
    stage(c, cam, [_room_cat(twos(t), dict(eye=0.5, mouth='smirk', tail=1.0, tlen=tl, tailwag=0.2, look=(0.8, -0.8)))])
    if t > T(5, 3): sfx(c, cam, (-120, -1500, 900), 'ДЗЫНЬ', T(5, 3), t, 160)


def _sock_pos(t):
    t0 = T(6, 1); land = T(6, 3)
    if t < t0: return (60, -600, 1130), 0
    u = clamp((t - t0) / (land - t0))
    return (lerp(60, 120, u), lerp(-600, -560, u) + 0 * u, lerp(1130, 860, u)), 400 * u


@shot(T(6), T(6, 4), K3((T(6), (100, -720, 300, 0, -10, 0, 1300)), (T(6, 2), (100, -620, 300, 0, 6, 0, 1300), 'io'), (T(6, 3), (60, -360, 120, 0, 18, 4, 1300), 'snap')), trans='cut', shake=0.5)
def s_sock(c, cam, t):
    apartment(c, cam)
    tt = t
    if T(6, 1) < t < T(6, 3):  # speed ramp: slow-mo while the sock falls
        u = (t - T(6, 1)) / (T(6, 3) - T(6, 1)); tt = T(6, 1) + (T(6, 3) - T(6, 1)) * (u ** 2.2)
    (sx, sy, sz), rot = _sock_pos(tt)
    if tt > T(6, 1):
        u = clamp((tt - T(6, 1)) / (T(6, 3) - T(6, 1)))
        sy = lerp(-600, -800, u) - 380 * math.sin(math.pi * u)
    pz = hits(t, [T(6), T(6, 1)], [kom(eye=0.5, look=(0.4, 0.6), mouth='smirk'), kom(eye=0.5, pr=(150, -170), look=(0.5, 0.8), mouth='smirk')])
    acts = [_room_cat(twos(t), pz), Act((sx, sy, sz), lambda c_: sock(c_, 1.0, rot), 0, 0.9),
            Act((120, 0, 800), VAL(t, val(eye=0.0 if t < T(6, 3) else 1.0, brow=1 if t > T(6, 3) else 0, tilt=10, lh=(-120, -160), rh=(120, -160), prop='paper', mouth='o' if t > T(6, 3) else 'open', mo=0.3), singing=False), 160, 0.85)]
    stage(c, cam, acts)


@shot(T(6, 4), T(7), lambda t: Cam3(0, -300, 300 - 500 * ease_in_out((t - T(6, 4)) / 1.0), 0, 16, 0, lerp(1300, 2300, ease_in_out((t - T(6, 4)) / 1.0))), trans='cut', shake=0.3)
def s_vertigo(c, cam, t):
    apartment(c, cam)
    stage(c, cam, [_room_cat(twos(t), kom(eye=0.42, look=(0, 1), tilt=-4, mouth='smirk', brow=-0.4))])


def _plan(c, t, stamps):
    prect(c, (-2600, -1700, 2600, 1700), P(PAPER))
    prect(c, (-2600, -1700, 2600, 1700), P(shader=tone_shader(2.0, INK, 3)))
    rooms = [(-2400, -1500, -300, 200, 'ЗАЛ'), (-300, -1500, 2400, -200, 'КУХНЯ'), (-300, -200, 1100, 1500, 'ВАННАЯ'), (1100, -200, 2400, 1500, 'СПАЛЬНЯ'), (-2400, 200, -300, 1500, 'КОРИДОР')]
    for (x0, y0, x1, y1, nm) in rooms:
        r = skia.Rect(x0, y0, x1, y1)
        c.drawRect(r, P(WHITE)); c.drawRect(r, inkp(26))
        draw_text(c, nm, (x0 + x1) / 2, y0 + 170, 120, INK, face=FONT_BLACK)
    for i, (ts, (x, y)) in enumerate(stamps):
        if t < ts: continue
        sc = lerp(2.0, 1.0, ease_out_expo((t - ts) / 0.14)); a = int(255 * clamp((t - ts) / 0.05))
        c.save(); c.translate(x, y); c.rotate(-10 + 14 * hash01(i)); c.scale(sc, sc)
        r = skia.Rect(-330, -170, 330, 170)
        c.drawRect(r, P(RED, a, stroke=36))
        f = font(240, FONT_BLACK); w = f.measureText('МОЁ')
        c.drawString('МОЁ', -w / 2, 86, f, P(RED, a))
        c.restore()


STAMPS = [(T(7, 1), (-1350, -650)), (T(7, 2), (1050, -850)), (T(7, 4), (400, 650)), (T(7, 5), (1750, 650)), (T(7, 6), (-1350, 850))]


@shot(T(7), T(8), lambda t: Cam3(0, -3600 - 900 * ease_in_out((t - T(7)) / 2.1), 0, 0, -90, lerp(-12, 12, ease_in_out((t - T(7)) / 2.1)), 1300), trans='slam', shake=0.6, punch=0.05, inv=[T(7, 6)])
def s_plan(c, cam, t):
    with floor(c, cam, 0, (-2600, -1700, 2600, 1700)) as pl:
        if pl: c.scale(1, -1); _plan(c, t, STAMPS)
    with floor(c, cam, -20, (-600, -600, 600, 600)) as pl:
        if pl:
            c.scale(1, -1); draw_komok_top(c, kom(), t)


STEPS = LINES[8]['echo']


def _sneak_cam(t):
    i = bisect.bisect_right(STEPS, t)
    k = [(-700, -380, -300, 18, 0, -6, 1300), (-500, -260, 100, 30, 0, 8, 1300), (-40, -200, 300, 0, 4, -10, 1300), (300, -160, 380, -20, 6, 6, 1300)][min(i, 3)]
    return Cam3(k[0] + 120 * (t - T(8)), *k[1:])


def _sneak_x(t):
    return stepped(t, T(8), T(9), -1000, 300, 0.5, 0.45)


@shot(T(8), T(9), _sneak_cam, trans='cut', shake=0.5, inv=STEPS)
def s_sneak(c, cam, t):
    x = _sneak_x(t)
    pr = [(x2, 600, 210) for x2 in [-1000 + k * 160 for k in range(int((x + 1000) / 160) + 1)]]
    apartment(c, cam, {'prints': [(px, pz, a) for px, pz, a in pr], 'rug': 0})
    ph = beat_pos(t) * 1.0
    pz = kom(eye=0.35, look=(1, 0.2), brow=-0.8, mouth='smirk', lean=8, step=ph, tail=0.9, tailwag=0.2, pl=(-40, -120), pr=(90, -100))
    stage(c, cam, [Act((x, 0, 600), KOM(twos(t), pz), 150, 0.9)])
    for s_ in STEPS: sfx(c, cam, (x + 120, -560, 560), 'ШАГ', s_, t, 220)
    c.drawRect(skia.Rect(-4000, -4000, 4000, 4000), P((6, 4, 20), 110))


BAG = [T(9, 1), T(9, 2), T(9, 3), T(9, 4)]


@shot(T(9), T(10), lambda t: lookat((lerp(560, 500, (t - T(9)) / 2.2), -560, lerp(-350, -60, ease_in_out((t - T(9)) / 2.2))), (300, -230, 500), -4 * ease_in_out((t - T(9)) / 2.2), 1300), trans='cut', shake=0.6, punch=0.05)
def s_bag(c, cam, t):
    apartment(c, cam)
    op = ease_out_back((t - BAG[0]) / 0.2) if t > BAG[0] else 0
    acts = [Act((420, 0, 500), lambda c_: backpack(c_, t, op, 5 * kick(t, 8)), 140),
            Act((150, 0, 520), KOM(twos(t), hits(t, [T(9)] + BAG, [kom(eye=0.6, look=(1, 0.4)), kom(eye=1, pr=(190, -260), look=(1, 0.3), mouth='o'), kom(eye=0.8, pr=(200, -230), mouth='open', mo=0.4),
                                                                 kom(eye=0.5, pr=(190, -280), mouth='smirk'), kom(eye=0.4, pr=(80, -80), mouth='smirk', blush=0.6)])), 150, 0.85)]
    items = ['sandwich', 'keys', 'sock2', 'bill']
    for i, ts in enumerate(BAG[1:]):
        d = t - ts
        if d > 0:
            x = 420 - 300 * d * (1 if i % 2 else -0.6); y = -420 - 800 * d + 1900 * d * d; z = 500 - 100 * d
            if y < 0:
                acts.append(Act((x, y, z), (lambda k: (lambda c_: _item(c_, k, t)))(items[i]), 0, 1.0))
    stage(c, cam, acts)


def _item(c, k, t):
    c.save(); c.rotate(t * 400)
    if k == 'sandwich':
        ink(c, rrect_path(-60, -20, 60, 20, 10), 'w', 4, 'l', 0, 8); c.drawRect(skia.Rect(-56, -4, 56, 6), P(RED))
    elif k == 'keys':
        c.drawCircle(0, 0, 22, inkp(6)); ink(c, rrect_path(10, -6, 70, 6, 3), 'k', 3)
    elif k == 'sock2':
        sock(c, 0.7)
    else:
        ink(c, rrect_path(-50, -26, 50, 26, 3), 'l', 4); draw_text(c, '₽', 0, 14, 40, INK, face=FONT_BLACK)
    c.restore()


def _bq_cam(t):
    if t < T(10, 6):
        u = ease_in_out((t - T(10)) / (T(10, 6) - T(10)))
        return lookat((lerp(-60, 0, u), -860, lerp(-150, 120, u)), (-250, -720, 700), lerp(-6, 6, u), 1300)
    u = ease_out_expo((t - T(10, 6)) / 0.25)
    return lookat((lerp(0, 380, u), lerp(-860, -560, u), 200), (lerp(-250, 200, u), lerp(-720, -330, u), lerp(700, 900, u)), 0, 1300)


@shot(T(10), T(11), _bq_cam, trans='cut', shake=0.6, punch=0.05)
def s_boss_q(c, cam, t):
    apartment(c, cam)
    vp = hits(t, [T(10), T(10, 2), T(10, 4), T(10, 6)], [val(lh=(-80, -330), rh=(220, -560), hk_r='point', brow=-0.6, look=(1, 0)), val(lh=(-220, -560), hk_l='open', rh=(220, -560), hk_r='open', brow=0.6),
                                                         val(rh=(240, -520), hk_r='point', lh=(-60, -260), brow=-1, lean=6), val(rh=(300, -480), hk_r='point', lh=(-60, -260), brow=-1, lean=10, tilt=8)])
    stage(c, cam, [Act((-250, 0, 700), VAL(t, vp), 160, 1.0), Act((200, 0, 900), KOM(twos(t), kom(eye=0.4, look=(-1, 0), mouth='smirk')), 150, 0.85)])


def _mur_cam(t):
    z = lerp(520, 640, ease_in_out((t - T(11)) / 1.4))
    if t > T(11, 6): z = 640 + 90 * ease_out_expo((t - T(11, 6)) / 0.2)
    return lookat((40, -880, z), (0, -880, 1180), -3 if t > T(11, 6) else 2, 1300)


@shot(T(11), T(12), _mur_cam, trans='cut', shake=0.4, punch=0.08, inv=[T(11, 6)])
def s_mur(c, cam, t):
    apartment(c, cam)
    e = 0.45 if t < T(11, 5) else (0.0 if t < T(11, 6) else 0.4)
    stage(c, cam, [_room_cat(twos(t), dict(eye=e, mouth='w', look=(0, 0), shades=ease_out_back((t - T(11, 6)) / 0.25) if t > T(11, 6) else 0, blush=0.5))])
    sfx(c, cam, (250, -1050, 1100), 'МУР', T(11, 6), t, 160, life=0.5)


# ============================================================ CHORUS — void stage, robo-vacuum drift
def vac_act(t, x, z, ang=0.0, rider=None, rider_s=0.75):
    def f(c):
        vacuum(c, t, t * 30)
        if rider: c.save(); c.translate(0, -60); c.scale(rider_s, rider_s); rider(c); c.restore()
    return Act((x, 0, z), f, 200)


def _ch(i, j=0, base=None):
    return base[i]['times'][j]


def chorus_block(B, t0_next, variant):
    """B: list of 7 chorus lines (+ optional extra). variant 1/2/3 changes cast and story."""
    L0, L1, L2, L3, L4, L5, L6 = B[:7]
    sh_ = lambda t: SHK(t, on_beats(t, L0['times'][0], [shk(lh=(-60, -160), rh=(60, -60), prop='phone'), shk(lh=(-80, -100), rh=(70, -170), tilt=8, jump=30), shk(lh=(-70, -170), rh=(60, -160), tilt=-8)], 0.5))

    def cast(t, cat_pose, cat_on=True, extra=()):
        acts = []
        if cat_on: acts.append(vac_act(t, 0, 0, rider=KOM(twos(t), cat_pose), rider_s=0.9))
        acts.append(Act((560, 0, -200), sh_(t), 50, 1.0))
        if variant >= 2:
            vp = val(shades=1 if variant == 3 else 0, chain=1 if variant == 3 else 0, cap=1 if variant == 3 else 0, brow=-1 if variant == 2 else 0, mouth='shout' if variant == 2 else 'smile',
                     lh=(-200, -500), rh=(200, -500), hk_l='fist', hk_r='fist')
            if variant == 3: vp = dict(vp, **on_beats(t, L0['times'][0], [dict(lh=(-260, -600), rh=(120, -260), hk_l='point', lean=-6, hip=(0, 30), lf=(-110, 0), rf=(80, -40)), dict(lh=(-120, -260), rh=(260, -600), hk_r='point', lean=6, hip=(0, 10), lf=(-60, 0), rf=(110, 0))], 0.5))
            acts.append(Act((-620, 0, 200), VAL(t, vp, singing=False), 160, 0.95))
        return acts + list(extra)

    t0 = L0['times'][0]
    t1 = L1['times'][0]; t2 = L2['times'][0]; t3 = L3['times'][0]; t4 = L4['times'][0]; t5 = L5['times'][0]; t6 = L6['times'][0]

    @shot(t0, t1, lambda t: orbit(0, -380, 0, 1500, lerp(-60, 10, ease_out_cubic((t - t0) / 1.0)), -40, 4, 1250), trans='ink' if variant == 1 else 'tear', shake=1.0, punch=0.08, inv=[t0])
    def a(c, cam, t):
        void(c, cam, {'drift': [(0, 0, 420, 140)]})
        stage(c, cam, cast(t, hits(t, L0['times'], [kom(shades=1, mouth='smirk', eye=0.5), kom(shades=1, pr=(160, -260), mouth='open', mo=0.6), kom(shades=1, pl=(-160, -260), pr=(160, -260), puff=1)])))

    def b_cam(t):
        return orbit(0, -420, 0, 1400 - 300 * ease_out_expo((t - L1['times'][2]) / 0.3) if t > L1['times'][2] else 1400, 18, -40, 4, 1250)

    @shot(t1, t2, b_cam, trans='cut', shake=1.0, punch=0.06, inv=[L1['times'][2]])
    def b(c, cam, t):
        void(c, cam, {})
        gone = t > L1['times'][2]
        stage(c, cam, cast(t, kom(shades=1, mouth='smirk', eye=0.5), cat_on=not gone, extra=[vac_act(t, 0, 0)] if gone else []))
        poof(c, cam, (0, -200, 0), L1['times'][2], t)
        if gone:
            with board(c, cam, (0, -300, -10)) as bb:
                if bb: speed_lines(c, 0, -100, 200, 1200, 40, a=180, col=WHITE)

    @shot(t2, t3, lambda t: Cam3(0, -900, -1700, 0, lerp(6, 24, ease_in_out((t - t2) / 1.0)), 0, 1250), trans='cut', shake=0.8, punch=0.06)
    def c_(c, cam, t):
        void(c, cam, {})
        if variant == 2:
            acts = cast(t, kom(), cat_on=False, extra=[vac_act(t, 0, 0)])
            acts = [a_ for a_ in acts]
            stage(c, cam, acts)
            # cat sits on grandpa's head
            with board(c, cam, (-620, -820, 199)) as bb:
                if bb: c.scale(0.6, 0.6); draw_komok(c, kom(shades=1, eye=0.5, mouth='smirk', pl=(-30, -200), pr=(60, -30)), twos(t))
        else:
            box(c, cam, -400, 400, -1600, 0, 300, 700, 'l', 'l', 'm', 6)
            stage(c, cam, cast(t, kom(), cat_on=False, extra=[vac_act(t, 0, -200)] + [Act((0, -1600, 500), KOM(twos(t), kom(shades=1, mouth='smirk', eye=0.5, pr=(140, -230))), 0, 0.85)]))

    @shot(t3, t4, lambda t: Cam3(0, -900, -1600 + 400 * ease_out_cubic((t - t3) / 1.0), 0, 10, 6, 1250), trans='cut', shake=0.8, punch=0.06, inv=[L3['times'][1]])
    def d(c, cam, t):
        void(c, cam, {})
        with wall(c, cam, 600) as pl:
            if pl:
                fr = rrect_path(-500, -1700, 500, -300, 0)
                c.drawPath(fr, P(PAPER)); c.drawPath(fr, P(shader=tone_shader(2.6)))
                c.drawCircle(160, -1300, 200, P(RED))
                c.drawPath(fr, inkp(40, WHITE, dev=0)); c.drawPath(fr, inkp(8))
                c.drawLine(0, -1700, 0, -300, inkp(26, WHITE, dev=0)); c.drawLine(0, -1700, 0, -300, inkp(6))
        y = lerp(-300, -1050, ease_out_cubic((t - t3) / 0.8))
        pz = kom(eye=0.9, mouth='open', mo=0.5, pl=(-120, -330), pr=(120, -330), puff=0.5, look=(0, -1)) if variant != 2 else kom(eye=1, mouth='o', pl=(-150, -300), pr=(150, -300), squish=1, sweat=1)
        stage(c, cam, [Act((0, y, 560), KOM(twos(t), pz), 0, 0.8)])
        sfx(c, cam, (380, -1300, 500), 'ОКНОЛЕЗ', L3['times'][1], t, 150, life=0.8)

    w4 = L4['times']

    def e_cam(t):
        i = max(0, bisect.bisect_right(w4, t) - 1)
        k = [(560, -330, -650, 0, 0, -6), (0, -500, -1100, -14, 0, 6), (560, -330, -600, 8, 0, 4), (-200, -600, -1200, 18, -2, -6), (-200, -600, -1200, 18, -2, -6), (0, -450, -1500, 0, -2, 0)][i]
        return Cam3(*k, 1250)

    @shot(t4, t5, e_cam, trans='cut', shake=1.0, punch=0.07, inv=[w4[1], w4[3]])
    def e(c, cam, t):
        void(c, cam, {'drift': [(0, 0, 420, 140)]})
        stage(c, cam, cast(t, hits(t, w4, [kom(shades=1, pr=(160, -280), mouth='open', mo=0.5), kom(shades=1, pl=(-160, -280), tilt=-8), kom(shades=1, puff=1, pl=(-170, -250), pr=(170, -250)),
                                          kom(shades=1, pr=(160, -290), tilt=8), kom(shades=1, pr=(160, -290), tilt=8), kom(shades=1, mouth='open', mo=0.8, pl=(-180, -300), pr=(180, -300), puff=1)])))

    # three slammed manga panels (one per word)
    w5 = L5['times']

    def f_cam(t):
        return Cam3(0, -470, -1450, 0, 0, 0, 1250)

    @shot(t5, t6, f_cam, trans='cut', shake=0.6, punch=0.0, inv=list(w5))
    def f(c, cam, t):
        c.drawRect(skia.Rect(-100, -100, W + 100, H + 100), P(INK))
        polys = [[(0, 0), (720, 0), (600, H), (0, H)], [(720, 0), (1320, 0), (1240, H), (600, H)], [(1320, 0), (W, 0), (W, H), (1240, H)]]
        poses = [kom(shades=1, pl=(-170, -300), pr=(170, -300), puff=1, mouth='open', mo=0.7), kom(shades=1, pr=(160, -290), tilt=10, mouth='smirk'), kom(shades=0, eye=0.0, mouth='w', blush=1, tilt=-10)]
        cams = [(-160, -420, -1150, 8, 0, -6), (140, -460, -1000, -8, 0, 6), (0, -560, -800, 0, 0, 0)]
        for i, ts in enumerate(w5):
            if t < ts: continue
            d = t - ts
            sc = lerp(1.35, 1.0, ease_out_expo(d / 0.16)); rot = lerp(-8 if i % 2 else 8, 0, ease_out_expo(d / 0.16))
            pts = polys[i]
            cx = sum(p_[0] for p_ in pts) / 4; cy = H / 2
            c.save(); c.translate(cx, cy); c.rotate(rot); c.scale(sc, sc); c.translate(-cx, -cy)
            path = poly_path(pts)
            c.save(); c.clipPath(path, skia.ClipOp.kIntersect, True)
            cm = Cam3(*cams[i], 1250)
            c.save(); c.translate(cx - W / 2, 0)
            void(c, cm, {}); stage(c, cm, [vac_act(t, 0, 0, rider=KOM(twos(t), poses[i]), rider_s=0.9)])
            c.restore()
            speed_lines(c, cx, H / 2, 380, 1200, 30, seed=i, a=150, col=WHITE)
            c.restore()
            c.drawPath(path, P(WHITE, stroke=22)); c.drawPath(path, inkp(8))
            c.restore()

    return t6


def drift_block(t0, t1, variant):
    def pos(t):
        u = (t - t0)
        a = u * 2.6
        return (math.cos(a) * 900, math.sin(a) * 650 + 300), a

    def cam(t):
        (x, z), a = pos(t)
        if t < (t0 + t1) / 2:
            cx_, cz_ = x * 0.35, z * 0.35 - 1500
            return lookat((cx_, -420, cz_), (x, -250, z), 6 * math.sin(t * 2), 1100)
        u = (t - (t0 + t1) / 2) / ((t1 - t0) / 2)
        return Cam3(0, lerp(-2000, -3000, ease_in_out(u)), 300, 0, -90, (t - t0) * 20, 1300)

    @shot(t0, t1, cam, trans='cut', shake=0.9, punch=0.06, inv=beats_in(t0, t1, 4.0))
    def dr(c, cam_, t):
        trail = []
        for k in range(1, 26):
            tt = t - k * 0.06
            if tt < t0: break
            (x, z), _ = pos(tt)
            trail.append((x, z, 60 + 8 * k, max(0, 210 - 8 * k)))
        (x, z), a = pos(t)
        marks = [(0, 300, 900, 120), (0, 300, 700, 90)]
        void(c, cam_, {'drift': marks})
        pz = kom(shades=1, mouth='open', mo=0.4, lean=-14, pl=(-160, -280), pr=(140, -120), tilt=-10)
        acts = [vac_act(t, x, z, rider=KOM(twos(t), pz), rider_s=0.9), Act((1400, 0, 900), SHK(t, shk(lh=(-60, -170), rh=(60, -170), jump=40 * abs(math.sin(math.pi * beat_pos(t))))), 50, 1.2)]
        if variant == 2:
            (x2, z2), _ = pos(t - 0.45)
            acts.append(vac_act(t, x2 * 0.8, z2 * 0.8, rider=VAL(t, val(hip=(0, 220), lf=(-160, 0), rf=(160, 0), lh=(-260, -420), rh=(260, -420), shades=0, mouth='shout', mo=0.7, brow=-1), singing=False), rider_s=0.55))
        if variant == 3:
            (x2, z2), _ = pos(t - 0.45)
            acts.append(vac_act(t, x2 * 0.8, z2 * 0.8, rider=VAL(t, val(hip=(0, 220), lf=(-160, 0), rf=(160, 0), lh=(-260, -420), rh=(260, -420), shades=1, chain=1, cap=1, mouth='smile'), singing=False), rider_s=0.55))
        if topdown(cam_):
            with floor(c, cam_, -6, (-4000, -4000, 4000, 4000)) as pl:
                if pl:
                    for (sx, sz, r, a_) in trail: c.drawPath(fluffy(sx, sz, r, r, 10, 0.15, int(sx) % 7), P(WHITE, a_))
                    c.save(); c.translate(x, z); c.rotate(math.degrees(a) + 90)
                    ink(c, ellipse_path(0, 0, 175, 175), 'w', 6, 'l', 0, 16); c.drawCircle(0, -120, 16, P(RED))
                    c.scale(0.7, 0.7); draw_komok_top(c, kom(), t); c.restore()
                    if variant >= 2:
                        (x2, z2), a2 = pos(t - 0.45)
                        c.save(); c.translate(x2 * 0.8, z2 * 0.8); c.rotate(math.degrees(a2) + 90)
                        ink(c, ellipse_path(0, 0, 175, 175), 'w', 6, 'l', 0, 16)
                        ink(c, ellipse_path(0, 0, 110, 90), 'w', 5); ink(c, ellipse_path(0, -40, 70, 76), 'w', 5, 'l', 6, 6)
                        c.restore()
        else:
            smoke(c, cam_, trail)
            stage(c, cam_, acts)


t_end = chorus_block(C1, 0, 1)
drift_block(C1[6]['times'][0], C1[7]['times'][0], 1)


@shot(C1[7]['times'][0], 53.12, lambda t: Cam3(0, -500, -1500 + 250 * (t - 48.3), 0, -2, 0, 1250), trans='cut', shake=0.9, punch=0.06, inv=beats_in(48.3, 53, 2.0))
def s_c1_end(c, cam, t):
    void(c, cam, {'drift': [(0, 0, 420, 140), (300, 300, 600, 100)]})
    pz = on_beats(t, 48.3, [kom(shades=1, pl=(-170, -300), pr=(170, -300), puff=1, mouth='open', mo=0.5), kom(shades=1, pr=(160, -280), tilt=8, mouth='smirk'), kom(shades=1, pl=(-160, -260), tilt=-8)], 1.0)
    stage(c, cam, [vac_act(t, 0, 0, rider=KOM(twos(t), pz), rider_s=0.9), Act((560, 0, -200), SHK(t, on_beats(t, 48.3, [shk(lh=(-60, -170), rh=(60, -170)), shk(lh=(-80, -100), rh=(70, -170), jump=40)], 0.5)), 50, 1.0)])


# ============================================================ VERSE 2 — kitchen
KIT = {'wall': 'kitchen', 'rug': 0}
TBL = (-500, 500, 400, 900)


def kitchen(c, cam, st=None):
    s = dict(KIT); s.update(st or {})
    apartment(c, cam, s)
    table(c, cam, *TBL)


def _tabletop(x, z): return (x, -760, z)


@shot(V2[0]['times'][0], V2[1]['times'][0], lambda t: lookat((lerp(-520, -260, ease_in_out((t - V2[0]['times'][0]) / 2.2)), -1050, 80), (60, -900, 660), 0, 1300), trans='ink', shake=0.4)
def s_cup(c, cam, t):
    kitchen(c, cam)
    w = V2[0]['times']
    wob = 14 * math.sin((t - w[1]) * 18) * math.exp(-(t - w[1]) * 3) if t > w[1] else 0
    pz = hits(t, [w[0], w[3]], [kom(eye=0.5, look=(-1, 0.5), mouth='smirk', pr=(150, -170)), kom(eye=0.0, mouth='w', tilt=8, blush=0.4)])
    stage(c, cam, [Act(_tabletop(-120, 650), lambda c_: cup_saucer(c_, wob), 0, 1.0), Act(_tabletop(200, 680), KOM(twos(t), pz), 0, 0.7)])


SPOON = V2[1]['times']


@shot(SPOON[0], V2[2]['times'][0], K3((SPOON[0], (150, -1020, 280, 0, 2, 0, 1300)), (V2[2]['times'][0], (150, -1020, 380, 0, 2, 0, 1300), 'io')), trans='cut', shake=0.3)
def s_spoon(c, cam, t):
    kitchen(c, cam)
    sw = math.sin(math.pi * beat_pos(t)) * 1.0
    stage(c, cam, [Act(_tabletop(150, 760), KOM(twos(t), kom(eye=0.9, look=(sw, 0.2), tilt=sw * 6, pupil=1, mouth='o', mo=0.2)), 0, 0.85)])
    with board(c, cam, (150 + sw * 160, -1080, 520)) as b:
        if b:
            c.save(); c.rotate(sw * 25)
            c.drawLine(0, -240, 0, 40, inkp(16, WHITE, dev=0)); c.drawLine(0, -240, 0, 40, inkp(5))
            ink(c, ellipse_path(0, 70, 34, 46), 'w', 5, 'l', 6, 6)
            c.restore()


TABLES = [(-1500, -1000), (-700, -200), (100, 600), (900, 1400)]
RUN = V2[2]['times']


def _run_x(t):
    return stepped(t, RUN[0], V2[3]['times'][0], -1300, 1250, 0.5, 0.5)


@shot(RUN[0], V2[3]['times'][0], lambda t: Cam3(_run_x(t) * 0.85, -800, -700, 0, 4, 3 * math.sin(math.pi * beat_pos(t)), 1200), trans='cut', shake=0.8, punch=0.05)
def s_tables(c, cam, t):
    apartment(c, cam, KIT)
    for x0, x1 in TABLES: table(c, cam, x0, x1, 300, 700, h=700, cloth=True)
    x = _run_x(t)
    ph = beat_pos(t) * 2
    jump = 120 * abs(math.sin(math.pi * ph))
    has = t > RUN[1]
    pz = kom(eye=0.7, look=(1, 0), mouth='grin' if has else 'smirk', step=ph, lean=10, hold='lid' if has else '', pr=(150, -260))
    stage(c, cam, [Act((x, -700 - jump, 500), KOM(twos(t), pz), 0, 0.7), Act((-1250, -700, 500), lambda c_: (ink(c_, rrect_path(-90, -110, 90, 0, 14), 'm', 5, 'd', 8, 8), None if has else (c_.save(), c_.translate(0, -110), hold_item(c_, 'lid', (0, 10), t), c_.restore())), 0, 1.0)])
    if t > RUN[1]: sfx(c, cam, (x - 300, -1300, 450), 'ХВАТЬ', RUN[1], t, 170)


RUG = V2[3]['times']


@shot(RUG[0], V2[4]['times'][0], K3((RUG[0], (0, -1700, -700, 0, -48, 0, 1300)), (V2[4]['times'][0], (0, -1900, -500, 0, -52, -6, 1300), 'io')), trans='cut', shake=0.4)
def s_rug(c, cam, t):
    hid = t > RUG[2]
    apartment(c, cam, {'rug_bump': 1 if hid else 0})
    if hid:
        with floor(c, cam, -4, (-1000, -400, 1000, 900)) as pl:
            if pl: c.drawOval(skia.Rect(-110, 230, 150, 370), P(RED_D)); c.drawOval(skia.Rect(-110, 230, 150, 370), inkp(5))
    x = lerp(-600, 20, ease_in_out((t - RUG[0]) / 0.9))
    pz = hits(t, RUG, [kom(eye=0.6, hold='lid', pr=(150, -250), look=(1, 0.5)), kom(eye=0.6, hold='lid', pr=(160, -120)), kom(eye=0.5, pr=(120, -60), look=(-0.5, 0.6), mouth='smirk'), kom(eye=0.0, mouth='w', blush=0.6), kom(eye=0.0, mouth='w', blush=0.8, tilt=8)])
    stage(c, cam, [Act((x, -20 if hid else 0, 300), KOM(twos(t), pz), 150, 0.9)])


STEPS2 = V2[4]['echo']


@shot(V2[4]['times'][0], V2[5]['times'][0], lambda t: Cam3(stepped(t, V2[4]['times'][0], V2[5]['times'][0], -900, 600, 0.5, 0.45), -1650, 300, 0, -90, 90, 1300), trans='slam', shake=0.4, inv=STEPS2)
def s_top_sneak(c, cam, t):
    x = stepped(t, V2[4]['times'][0], V2[5]['times'][0], -900, 600, 0.5, 0.45)
    pr = [(px, 260 + 70 * (k % 2), 220) for k, px in enumerate(range(-900, int(x), 130))]
    apartment(c, cam, {'prints': pr, 'rug': 0})
    with floor(c, cam, -10, (-2000, -2000, 2000, 2000)) as pl:
        if pl:
            c.save(); c.translate(x, 300); c.rotate(-90); draw_komok_top(c, kom(step=beat_pos(t) * 2), t); c.restore()
            c.save(); c.translate(100, -500); c.rotate(-90)
            ink(c, rrect_path(-220, -500, 220, 500, 60), 'm', 6, 'd', 10, 10)
            ink(c, ellipse_path(0, -380, 120, 100), 'w', 5)
            c.drawPath(smooth_path([(-60, -330), (0, -300), (60, -330)]), inkp(6))
            ink(c, rrect_path(-200, -260, 200, 480, 40), 'r', 5, 'rd', 0, 12)
            c.restore()
            zzz_t = t
            for k in range(3):
                u = (zzz_t * 0.7 + k / 3) % 1
                draw_text(c, 'Z', 400 + 140 * u, -700 - 60 * u, 90 + 60 * u, INK, face=FONT_BLACK, a=int(255 * (1 - u)))
    for s_ in STEPS2: sfx(c, cam, (x, -300, 300), 'ШАГ', s_, t, 200, rot=0)


BAG2 = V2[5]['times']


@shot(BAG2[0], V2[6]['times'][0], lambda t: lookat((lerp(40, 160, ease_in_out((t - BAG2[0]) / 2.2)), -620, lerp(-350, -120, ease_in_out((t - BAG2[0]) / 2.2))), (300, -250, 490), 3, 1300), trans='cut', shake=0.5)
def s_bag2(c, cam, t):
    apartment(c, cam)
    op = ease_out_back((t - BAG2[1]) / 0.2) if t > BAG2[1] else 0
    inside = t > BAG2[3]
    if inside: op = max(0, 1 - ease_out_cubic((t - BAG2[4]) / 0.2)) if t > BAG2[4] else 1
    acts = [Act((420, 0, 500), lambda c_: backpack(c_, t, op, (8 * math.sin(t * 30) if inside else 0)), 140)]
    if not inside:
        x = lerp(80, 360, ease_in_out((t - BAG2[2]) / 0.4)) if t > BAG2[2] else 80
        y = -260 * math.sin(math.pi * clamp((t - BAG2[2]) / 0.5)) if t > BAG2[2] else 0
        acts.append(Act((x, y, 470), KOM(twos(t), kom(eye=0.8, look=(1, 0.3), pr=(180, -260), pl=(-150, -260) if t > BAG2[2] else (-70, -70), mouth='grin')), 150, 0.75))
    else:
        sfx(c, cam, (420, -500, 480), 'ВЖУХ', BAG2[4], t, 160)
    stage(c, cam, acts)


BOSS2 = V2[6]['times']


@shot(BOSS2[0], V2[7]['times'][0], lambda t: orbit(0, -700, 500, 1500, lerp(-40, 30, ease_in_out((t - BOSS2[0]) / 2.3)), 0, 0, 1300), trans='cut', shake=0.6, punch=0.05, inv=[BOSS2[6]])
def s_boss2(c, cam, t):
    apartment(c, cam)
    pop = t > BOSS2[2]
    vp = hits(t, [BOSS2[0], BOSS2[2], BOSS2[6]], [val(lh=(-60, -260), rh=(150, -380), prop='', hk_r='open', look=(1, 0.5)), val(lh=(-60, -260), rh=(150, -380), brow=1, hair=1, mouth='o'),
                                               val(rh=(260, -540), hk_r='point', brow=-1, lh=(-120, -380))])
    acts = [Act((-300, 0, 500), VAL(t, vp), 160, 1.0), Act((60, -380, 470), lambda c_: backpack(c_, t, 1 if pop else 0, 0), 0, 0.8)]
    if pop:
        y = -380 - 200 * ease_out_back((t - BOSS2[2]) / 0.3)
        acts.append(Act((60, y, 460), KOM(twos(t), kom(crown=ease_out_back((t - BOSS2[2]) / 0.3), eye=0.5, mouth='smirk', pl=(-150, -260), pr=(150, -260))), 0, 0.6))
    stage(c, cam, acts)


MURS = [V2[7]['times'][6]] + list(V2[7]['echo'][1:])


@shot(V2[7]['times'][0], C2[0]['times'][0], lambda t: lookat((-60, -600, lerp(-380, -150, ease_in_out((t - V2[7]['times'][0]) / 2.0))), (-80, -420, 650), 0, 1300), trans='cut', shake=0.4, punch=0.12, inv=MURS[::2])
def s_mur2(c, cam, t):
    apartment(c, cam)
    k = bisect.bisect_right(MURS, t)
    stage(c, cam, [Act((-420, 0, 700), VAL(t, val(blush=min(1, k * 0.3), eye=1, look=(1, 0), lh=(-100, -300), rh=(160, -380), brow=0.5)), 160, 1.0),
                   Act((140, 0, 640), lambda c_: backpack(c_, t, 1, 0), 140, 0.9),
                   Act((140, -210, 620), KOM(twos(t), kom(crown=1, eye=0.0 if k else 0.45, mouth='w', blush=0.3 * k, puff=0.3 * k)), 0, 0.62)])
    for i, m in enumerate(MURS):
        sfx(c, cam, (140 + [-300, 330, -240, 280][i % 4], -760 + [0, -120, 80, -60][i % 4], 600), 'МУР', m, t, 120, rot=[-10, 8, -6, 12][i % 4], life=0.5)
        d = t - m
        if 0 < d < 0.5:
            with board(c, cam, (140, -560, 600)) as b:
                if b: c.drawCircle(0, 0, 160 + 900 * d, P(INK, int(200 * (1 - d / 0.5)), stroke=12))


# ============================================================ CHORUS 2 (drift battle) + BRIDGE + CHORUS 3
chorus_block(C2, 0, 2)
drift_block(C2[6]['times'][0], BR[0]['times'][0], 2) if False else None


@shot(C2[6]['times'][0], BR[0]['times'][0], lambda t: Cam3(0, -500, -1400, 0, -2, 0, 1250), trans='cut', shake=0.8, punch=0.06, inv=[C2[6]['times'][3]])
def s_c2_end(c, cam, t):
    void(c, cam, {'drift': [(0, 0, 420, 140)]})
    stage(c, cam, [vac_act(t, 0, 0, rider=KOM(twos(t), kom(shades=1, pl=(-170, -300), pr=(170, -300), puff=1, mouth='open', mo=0.5)), rider_s=0.9),
                   Act((-620, 0, 200), VAL(t, val(mouth='shout', mo=0.5, brow=-1, lh=(-200, -520), rh=(200, -520)), singing=False), 160, 0.95)])


def dark(c, cam, t, beam_from, beam_to, extra=None, reveal=0.0):
    apartment(c, cam, {'csway': 0})
    if extra: extra()
    # everything black except inside the torch cone
    bp = cam.project(beam_from); bt = cam.project(beam_to)
    c.saveLayer(None, None)
    c.drawRect(skia.Rect(-200, -200, W + 200, H + 200), P((4, 3, 8), 205))
    if bp and bt:
        ang = math.atan2(bt[1] - bp[1], bt[0] - bp[0]); L = math.hypot(bt[0] - bp[0], bt[1] - bp[1]) + 300
        spread = 0.32
        cone = poly_path([(bp[0], bp[1]), (bp[0] + math.cos(ang - spread) * L, bp[1] + math.sin(ang - spread) * L), (bp[0] + math.cos(ang + spread) * L, bp[1] + math.sin(ang + spread) * L)])
        p = P(WHITE); p.setBlendMode(skia.BlendMode.kDstOut); p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30))
        c.drawPath(cone, p)
        c.drawCircle(bt[0], bt[1], 260, p)
    c.restore()


def _torch_val(t, look=(1, 0), rh=(260, -420), extra=None):
    q = val(rh=rh, prop='torch', hk_r='fist', look=look, brow=0.5, lean=6, eye=1)
    if extra: q.update(extra)
    return q


@shot(BR[0]['times'][0], BR[1]['times'][0], lambda t: Cam3(-200, -700, -400, 6 * math.sin((t - 81.6) * 0.8), 2, 0, 1300), trans='ink', shake=0.2, weave=2.0)
def s_br1(c, cam, t):
    sweep = math.sin((t - 81.6) * 1.6)
    tgt = (300 + 700 * sweep, -500, 1100)
    def ex():
        stage(c, cam, [Act((-500, 0, 500), VAL(t, _torch_val(t, (sweep, 0), (260, -420), dict(lh=(-40, -470), hk_l='point') if t > BR[0]['times'][2] else None), singing=True), 160, 1.0),
                       Act((-120, 0, 300), SHK(t, shk(shades=0, lh=(-40, -160), rh=(40, -160), mouth='o', mo=0.3), singing=False), 50, 1.0)])
    dark(c, cam, t, (-240, -720, 500), tgt, ex)
    if t > BR[0]['times'][2]: sfx(c, cam, (-640, -1180, 480), 'ТСС!', BR[0]['times'][2], t, 150, life=1.0)


@shot(BR[1]['times'][0], BR[2]['times'][0], lambda t: Cam3(-300, -720, lerp(-500, 400, ease_in_out((t - BR[1]['times'][0]) / 2.1)), 4, 2, 0, 1300), trans='cut', shake=0.2, weave=2.0)
def s_br2(c, cam, t):
    def ex():
        wardrobe(c, cam, 900, 1500, 600, 1100)
        stage(c, cam, [Act((-560, 0, 600), VAL(t, _torch_val(t, (1, 0)), singing=True), 160, 1.0)])
    dark(c, cam, t, (-300, -720, 600), (1000, -900, 600), ex)


@shot(BR[2]['times'][0], BR[3]['times'][0], lambda t: lookat((lerp(500, 650, ease_in_out((t - BR[2]['times'][0]) / 2)), -1100, lerp(-500, -150, ease_in_out((t - BR[2]['times'][0]) / 2))), (1200, -2250, 900), 0, 1300), trans='cut', shake=0.2, weave=2.0)
def s_br3(c, cam, t):
    def ex():
        wardrobe(c, cam, 900, 1500, 600, 1100)
        tl = ease_out_back((t - BR[2]['times'][1]) / 0.4) if t > BR[2]['times'][1] else 0.3
        with board(c, cam, (1200, -2100, 900)) as b:
            if b:
                pts = [(0, 40)] + [(30 * math.sin(t * 3 + u * 3) * u, 40 - 420 * tl * u) for u in (0.25, 0.5, 0.75, 1.0)]
                ink(c, tube(pts, [60, 56, 52, 48, 42]), 'm', 6)
    dark(c, cam, t, (0, -800, 300), (1200, -2300, 900), ex)


def _br4_cam(t):
    t1 = BR[3]['times'][1]
    if t < t1: return lookat((-300, -800, -500), (300, -1200, 700), 0, 1300)
    u = ease_out_expo((t - t1) / 0.3)
    return lookat((lerp(-300, 700, u), lerp(-800, -1700, u), lerp(-500, 150, u)), (lerp(300, 1200, u), lerp(-1200, -2300, u), lerp(700, 900, u)), 0, 1300)


@shot(BR[3]['times'][0], 90.2, _br4_cam, trans='cut', shake=0.3, inv=[BR[3]['times'][1]])
def s_br4(c, cam, t):
    def ex():
        wardrobe(c, cam, 900, 1500, 600, 1100)
        stage(c, cam, [Act((-400, 0, 400), VAL(t, _torch_val(t, (1, -1), (300, -560), dict(brow=1, mouth='o')), singing=True), 160, 1.0),
                       Act((1200, -2100, 900), KOM(twos(t), kom(eye=1 if t > BR[3]['times'][1] else 0.0, glare=1, look=(-1, 0.6), mouth='smirk', tail=1)), 0, 0.85)])
    dark(c, cam, t, (-150, -820, 380), (1200, -2300, 900), ex)
    if t > BR[3]['times'][1]:
        p_ = cam.project((1200, -2400, 890))
        if p_:
            for side in (-1, 1): c.drawCircle(p_[0] + side * 40 * 1300 / p_[2], p_[1], 60 * 1300 / p_[2], P(RED, 120, blur=18))


BUILD = beats_in(90.2, 97.4, 1.0)


@shot(90.2, 97.51, lambda t: Cam3(0, -870, 1180 - 1500 + stepped(t, 90.2, 96.5, 0, 1000, 1.0, 0.25), 0, 0, 2 * math.sin(t * 9) * clamp((t - 94) / 3), 1300), trans='cut', shake=0.7, punch=0.06, inv=BUILD[-6::2])
def s_build(c, cam, t):
    apartment(c, cam)
    stage(c, cam, [_room_cat(twos(t), kom(eye=0.9, glare=clamp((t - 92) / 4), look=(0, 0), brow=-1, puff=clamp((t - 93) / 3), pupil=0.5))])
    k = clamp((t - 92) / 5)
    if k > 0:
        speed_lines(c, W / 2, H / 2, 420 - 200 * k, 1300, int(30 + 60 * k), a=int(255 * k))
    if t > 96.9:
        c.drawRect(skia.Rect(-100, -100, W + 100, H + 100), P(INK))
        for side in (-1, 1):
            c.drawOval(skia.Rect(W / 2 + side * 220 - 120, H / 2 - 90, W / 2 + side * 220 + 120, H / 2 + 90), P(RED))
            c.drawOval(skia.Rect(W / 2 + side * 220 - 16, H / 2 - 80, W / 2 + side * 220 + 16, H / 2 + 80), P(INK))


chorus_block(C3, 0, 3)
drift_block(C3[6]['times'][0], 108.6, 3)


# ============================================================ OUTRO
def _sleepers(t):
    return [Act((-200, 0, 700), lambda c_: None, 0),
            ]


@shot(108.6, 116.9, lambda t: Cam3(-200, lerp(-760, -900, ease_in_out((t - 108.6) / 8)), lerp(80, -1100, ease_in_out((t - 108.6) / 8.3)), lerp(0, 6, (t - 108.6) / 8), 2, 0, 1300), trans='ink', shake=0.15, weave=1.5)
def s_out1(c, cam, t):
    apartment(c, cam)
    lamp(c, cam, 0, 700, 3 * math.sin(t))
    def chair(c_):
        ink(c_, rrect_path(-300, -780, 300, -340, 80), 'm', 6, 'd', 14, 12)
        ink(c_, rrect_path(-340, -420, 340, -140, 60), 'l', 6, 'm', 0, 14)
        c_.save(); c_.translate(0, -180); draw_valera(c_, val(hip=(0, 240), lf=(-160, 0 + 180), rf=(160, 180), lh=(-120, -260), rh=(120, -260), eye=0.0, tilt=14, mouth='open', mo=0.25 + 0.1 * math.sin(t * 2), shades=0, chain=1, glasses=1), t); c_.restore()
        c_.save(); c_.translate(20, -560); c_.scale(0.55, 0.55)
        draw_komok(c_, kom(eye=0.0, mouth='w', blush=0.5, pl=(-60, -40), pr=(60, -40), tailwag=0.2, crown=1), t)
        c_.restore()
        c_.save(); c_.translate(-60, -800); c_.scale(0.6, 0.6); draw_shket(c_, shk(shades=0, mouth='smile', lh=(-30, -60), rh=(30, -60)), t); c_.restore()
        for k in range(3):
            u = (t * 0.5 + k / 3) % 1
            draw_text(c_, 'Z', 260 + 80 * u, -900 - 200 * u, 60 + 50 * u, INK, face=FONT_BLACK, a=int(255 * (1 - u)))
        for sx in (-260, 220): c_.drawRect(skia.Rect(sx, -120, sx + 40, 0), P(INK))
    stage(c, cam, [Act((-200, 0, 800), chair, 200, 1.0)])


@shot(116.9, 126.4, K3((116.9, (0, -1000, 200, 0, 0, 0, 1300)), (126.4, (0, -1400, -6000, 0, 4, 0, 1300), 'out')), trans='ink', shake=0.1, weave=1.5)
def s_out2(c, cam, t):
    far_sky(c, cam, 12000, moon=(-2600, -5200), moon_r=1500)
    city(c, cam, ((9000, 0.2), (6500, 0.25)), base_y=900)
    facade(c, cam, t, (0, -1000), 0, cat_sil=True)
    with floor(c, cam, 800, (-20000, -20000, 20000, 1500)) as pl:
        if pl: prect(c, (-20000, -20000, 20000, 1500), P(INK))


SHOTS.sort(key=lambda s: s.t0)
for a_, b_ in zip(SHOTS, SHOTS[1:]): a_.t1 = b_.t0
