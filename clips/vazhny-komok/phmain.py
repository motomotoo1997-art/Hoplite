import sys, os, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ink3d
from phstory import *
from phcast import _slipper  # noqa

FPS = int(os.environ.get('FPS', 60))
SS = float(os.environ.get('SS', 2))
DUR = 126.4
F_COND = skia.Typeface.MakeFromFile('/usr/share/fonts/truetype/roboto/unhinted/RobotoCondensed-Bold.ttf')
_starts = [s.t0 for s in SHOTS]


# ============================================================== screen-space 3D cards
SCAM = Cam3(0, 0, -1300, 0, 0, 0, 1300)


class Card:
    def __init__(self, c, x, y, yaw=0.0, pitch=0.0, s=1.0):
        ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        cp_, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
        U = np.array([ca, 0, sa]) * s
        V = np.array([sa * sp * 0, cp_, -sp]) * s
        self.pl = Plane(c, SCAM, (x - W / 2, y - H / 2, 0), U, V, clip=False)

    def __enter__(self): return self.pl.__enter__()

    def __exit__(self, *a): self.pl.__exit__(*a)


def text_w(s, size, face): return font(size, face).measureText(s)


def slab_word(c, s, size, face, fill, a, outline=INK, shadow=RED, ow=0.13):
    f = font(size, face); w = f.measureText(s)
    if shadow: c.drawString(s, -w / 2 + size * 0.07, size * 0.36 + size * 0.07, f, P(shadow, a))
    if ow: c.drawString(s, -w / 2, size * 0.36, f, P(outline, a, stroke=size * ow))
    c.drawString(s, -w / 2, size * 0.36, f, P(fill, a))
    return w


def torn_strip(c, x0, x1, y0, y1, seed, a=255, col=WHITE):
    pts = []
    n = int((x1 - x0) / 26) + 2
    for i in range(n + 1): pts.append((lerp(x0, x1, i / n), y0 + (hash01(seed + i) - 0.5) * 12))
    for i in range(n, -1, -1): pts.append((lerp(x0, x1, i / n), y1 + (hash01(seed + 99 + i) - 0.5) * 12))
    path = poly_path(pts)
    sh = skia.Path(path); sh.offset(10, 12)
    c.drawPath(sh, P(INK, int(a * 0.6)))
    c.drawPath(path, P(col, a))
    c.drawPath(path, inkp(4, a=a, dev=0.8))


def _windows():
    out = []
    for i, ln in enumerate(LINES):
        st = ln['times'][0] - 0.05
        nxt = LINES[i + 1]['times'][0] - 0.05 if i + 1 < len(LINES) else 999
        last = max(ln['times'][-1], ln['echo'][-1] if ln['echo'] else 0)
        end = min(nxt, last + 1.2)
        if ln['style'] == 'intro': end = 8.95
        out.append((st, end, ln, i))
    return out


WIN = _windows()


def typography(c, t):
    for st, end, ln, li in WIN:
        if not (st <= t < end + 0.25): continue
        ex = clamp((t - end) / 0.25)
        sty = ln['style']; words = ln['words']; times = ln['times']
        if sty == 'intro':
            k = li  # 0..3 seals in four positions
            pos = [(300, 300), (W - 300, 300), (300, H - 260), (W - 300, H - 260)][k]
            d = t - times[0]
            sc = lerp(2.2, 1.0, ease_out_expo(d / 0.15)); a = int(255 * clamp(d / 0.05) * (1 - ex))
            c.save(); c.translate(*pos); c.rotate(-8 + 16 * hash01(k)); c.scale(sc, sc)
            r = skia.Rect(-170, -150, 170, 150)
            c.drawRect(r, P(RED, a)); c.drawRect(r.makeInset(12, 12), P(WHITE, a, stroke=6))
            f = font(78, F_COND)
            for j, wd in enumerate(['МОЙ КОТ', 'ОБОРМОТ']):
                if t < times[0 if j == 0 else 3]: continue
                w = f.measureText(wd); c.drawString(wd, -w / 2, -14 + j * 90, f, P(WHITE, a))
            c.restore()
            continue
        if sty == 'verse':
            size = 74
            sp = 22
            ws = [text_w(w, size, F_COND) for w in words]
            total = sum(ws) + sp * (len(ws) - 1)
            lines = [list(range(len(words)))]
            if total > 1500:
                mid = len(words) // 2; lines = [list(range(mid)), list(range(mid, len(words)))]
            for li2, idxs in enumerate(lines):
                tot = sum(ws[i] for i in idxs) + sp * (len(idxs) - 1)
                y = H - 170 + (li2 - (len(lines) - 1)) * 104
                t_in = times[idxs[0]]
                d = t - t_in
                if d < -0.02: continue
                yaw = lerp(80, 0, ease_out_back(d / 0.3, 1.6)) - 40 * ex
                x0 = W / 2 - tot / 2
                with Card(c, W / 2, y, yaw, 0) as ok:
                    if not ok: continue
                    torn_strip(c, -tot / 2 - 40, -tot / 2 - 40 + (tot + 80) * ease_out_expo(d / 0.25), -58, 40, li * 13 + li2, int(255 * (1 - ex)))
                    x = -tot / 2
                    for i in idxs:
                        wt = times[i]
                        if t >= wt - 0.02:
                            dd = t - wt
                            a = int(255 * clamp(dd / 0.06) * (1 - ex))
                            f = font(size, F_COND)
                            col = RED if i == len(words) - 1 else INK
                            c.save(); c.translate(x, 0)
                            c.clipRect(skia.Rect(-10, -80 + 160 * (1 - ease_out_expo(dd / 0.12)), ws[i] + 10, 60))
                            c.drawString(words[i], 0, 22, f, P(col, a))
                            c.restore()
                        x += ws[i] + sp
            for j, e in enumerate(ln['echo']):
                d = t - e
                if 0 <= d < 0.5:
                    pass
            continue
        if sty in ('chorus', 'big', 'outro', 'whisper'):
            if sty == 'big':
                i = max(0, bisect.bisect_right(times, t) - 1)
                if t < times[0] - 0.02: continue
                wd = words[i].strip(',').upper(); d = t - times[i]
                sc = lerp(2.6, 1.0, ease_out_expo(d / 0.16)) * (1 + 0.04 * kick(t, 6))
                c.save(); c.translate(W / 2, H * 0.78); c.rotate([-6, 5, -3][i % 3]); c.scale(sc, sc)
                w = text_w(wd, 190, FONT_BLACK)
                c.drawRect(skia.Rect(-w / 2 - 40, -160, w / 2 + 40, 60), P(RED, int(255 * (1 - ex))))
                slab_word(c, wd, 190, FONT_BLACK, WHITE, int(255 * (1 - ex)), INK, INK)
                c.restore()
                continue
            if sty == 'whisper':
                y = H - 150; f = font(56, F_COND)
                txt = ''
                for i, wd in enumerate(words):
                    if t >= times[i]: txt += (' ' if txt else '') + wd.lower()
                a = int(230 * (1 - ex))
                spc = 10
                w = f.measureText(txt) + spc * len(txt)
                x = W / 2 - w / 2
                for ch in txt:
                    c.drawString(ch, x, y, f, P(WHITE, a)); x += f.measureText(ch) + spc
                continue
            size = 120 if sty == 'chorus' else 96
            yb = 190 if ln['pos'] == 't' else H - 180
            if sty == 'outro': yb = H - 170
            ws = [text_w(w.upper(), size, FONT_BLACK) for w in words]
            sp = 36; tot = sum(ws) + sp * (len(ws) - 1)
            yaw = 14 * math.sin(math.pi * beat_pos(t) / 2) if sty == 'chorus' else 0
            with Card(c, W / 2, yb, yaw, 0) as ok:
                if not ok: continue
                x = -tot / 2
                for i, wd in enumerate(words):
                    if t >= times[i] - 0.02:
                        d = t - times[i]
                        sc = lerp(2.0, 1.0, ease_out_expo(d / 0.14)) if sty == 'chorus' else 1.0
                        a = int(255 * clamp(d / 0.05) * (1 - ex))
                        if sty == 'outro': a = int(a * clamp(d / 0.6))
                        c.save(); c.translate(x + ws[i] / 2, 10 * ex * ex * (1 if i % 2 else -1) * 30); c.rotate((hash01(i * 7 + li) - 0.5) * 8 + ex * 30 * (1 if i % 2 else -1)); c.scale(sc, sc)
                        fill = RED if wd.lower().startswith('обормот') and sty == 'chorus' else WHITE
                        slab_word(c, wd.upper(), size, FONT_BLACK, fill, a, INK, INK if fill == RED else RED)
                        c.restore()
                    x += ws[i] + sp


# ============================================================== post
class Post:
    def __init__(self):
        rng = np.random.default_rng(3)
        n = rng.normal(0, 1, (270, 480)).astype(np.float32)
        from numpy.fft import fft2, ifft2
        ky = np.fft.fftfreq(270)[:, None]; kx = np.fft.fftfreq(480)[None, :]
        lowf = np.real(ifft2(fft2(n) * np.exp(-(kx ** 2 + ky ** 2) * 900)))
        lowf = (lowf - lowf.min()) / (np.ptp(lowf) + 1e-6)
        fine = rng.random((1080, 1920)).astype(np.float32)
        lo = np.kron(lowf, np.ones((4, 4)))[:1080, :1920]
        v = (0.86 + 0.14 * lo * 0.7 + 0.14 * fine * 0.5)
        v = np.clip(v * 255, 0, 255).astype(np.uint8)
        a = np.zeros((1080, 1920, 4), dtype=np.uint8); a[..., 0] = v; a[..., 1] = (v * 0.985).astype(np.uint8); a[..., 2] = (v * 0.95).astype(np.uint8); a[..., 3] = 255
        self.paper = skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType)
        self.samp = skia.SamplingOptions(skia.FilterMode.kLinear)

    def finish(self, c, t, inv):
        p = skia.Paint(); p.setBlendMode(skia.BlendMode.kMultiply)
        c.drawImageRect(self.paper, skia.Rect(0, 0, W, H), self.samp, p)
        c.drawRect(skia.Rect(0, 0, W, H), P(shader=rgrad((W / 2, H / 2), W * 0.75, [(0, 0, 0, 0), (0, 0, 0, 0), (10, 6, 8, 170)], [0, 0.62, 1])))
        if inv:
            q = P(WHITE); q.setBlendMode(skia.BlendMode.kDifference); c.drawRect(skia.Rect(-50, -50, W + 50, H + 50), q)


# ============================================================== frame
def scene_time(sh, t):
    if sh.freeze and sh.freeze[0] <= t < sh.freeze[1]: return sh.freeze[0]
    return t


def draw_shot(c, sh, t, dx=0.0, dy=0.0, zoom=1.0, rot=0.0):
    tt = scene_time(sh, t)
    set_time(tt if sh.freeze and sh.freeze[0] <= t < sh.freeze[1] else t)
    cam = sh.cam(t)
    sk = sh.shake * (0.4 * low(t) + 0.6 * kick(t, 10)) * 10
    wv = sh.weave * 2.2
    sd = int(t * 12)
    ox = noise(t * 21, 1) * sk + (hash01(sd) - 0.5) * wv + dx
    oy = noise(t * 27, 5) * sk + (hash01(sd + 7) - 0.5) * wv + dy
    z = (1 + sh.punch * kick(t, 9)) * zoom
    c.save()
    c.translate(W / 2 + ox, H / 2 + oy); c.rotate(rot); c.scale(z, z); c.translate(-W / 2, -H / 2)
    c.drawRect(skia.Rect(-200, -200, W + 200, H + 200), P(PAPER))
    sh.draw(c, cam, tt)
    c.restore()
    set_time(t)


def freeze_card(c, t, sh):
    if not (sh.freeze and sh.freeze[0] <= t < sh.freeze[1] + 0.3): return
    d = t - sh.freeze[0]; ex = clamp((t - sh.freeze[1]) / 0.3)
    p = skia.Paint(); p.setColorFilter(skia.ColorFilters.Matrix([0.33, 0.33, 0.33, 0, 0] * 3 + [0, 0, 0, 1, 0]))
    c.drawRect(skia.Rect(0, 0, W, H), P(INK, int(70 * (1 - ex))))
    x = lerp(-900, 0, ease_out_expo(d / 0.3)) - 1200 * ease_in_cubic(ex)
    c.save(); c.translate(x, 0)
    c.drawPath(poly_path([(0, 620), (1180, 590), (1120, 860), (0, 900)]), P(RED))
    c.drawPath(poly_path([(0, 620), (1180, 590), (1120, 860), (0, 900)]), inkp(8))
    f = font(170, FONT_BLACK)
    c.drawString('КОМОК', 70, 790, f, P(INK, stroke=24)); c.drawString('КОМОК', 70, 790, f, P(WHITE))
    f2 = font(46, F_COND)
    c.drawString('ВАЖНЫЙ. ПУШИСТЫЙ. ГЛАВНЫЙ.', 80, 850, f2, P(INK))
    c.drawString('БОСС ПОДОКОННИКА', 640, 660, font(40, F_COND), P(WHITE))
    c.restore()
    if d < 0.06: c.drawRect(skia.Rect(0, 0, W, H), P(WHITE, int(200 * (1 - d / 0.06))))


def render_frame(c, post, t):
    i = max(0, bisect.bisect_right(_starts, t) - 1)
    sh = SHOTS[i]; lt = t - sh.t0; prev = SHOTS[i - 1] if i > 0 else None
    c.clear(C(PAPER))
    tr = sh.trans
    if tr == 'ink' and prev and lt < 0.34:
        draw_shot(c, prev, t)
        u = ease_in_cubic(lt / 0.34)
        blob = fluffy(W / 2, H / 2, 40 + 1500 * u, 40 + 1300 * u, 18, 0.22, 5, t)
        for k in range(7):
            a = k / 7 * math.tau + 0.4
            blob = union(blob, ellipse_path(W / 2 + math.cos(a) * (200 + 1300 * u), H / 2 + math.sin(a) * (160 + 900 * u), 30 + 160 * u, 30 + 160 * u))
        c.save(); c.clipPath(blob, skia.ClipOp.kIntersect, True); draw_shot(c, sh, t); c.restore()
        c.drawPath(blob, P(INK, stroke=34 * (1 - u) + 6))
    elif tr == 'tear' and prev and lt < 0.3:
        u = ease_out_expo(lt / 0.3)
        xe = lerp(W + 200, -200, u)
        pts = [(xe + (hash01(k) - 0.5) * 60, k * 40) for k in range(int(H / 40) + 2)]
        right = poly_path(pts + [(W + 400, H + 40), (W + 400, -40)])
        left = poly_path(pts + [(-400, H + 40), (-400, -40)])
        c.save(); c.clipPath(left, skia.ClipOp.kIntersect, True); draw_shot(c, prev, t, dx=-200 * u); c.restore()
        c.save(); c.clipPath(right, skia.ClipOp.kIntersect, True); draw_shot(c, sh, t); c.restore()
        c.drawPath(smooth_path(pts), P(WHITE, stroke=28)); c.drawPath(smooth_path(pts), inkp(5))
    elif tr == 'slam' and lt < 0.22:
        u = ease_out_expo(lt / 0.22)
        c.drawRect(skia.Rect(0, 0, W, H), P(INK))
        s_ = lerp(1.25, 1.0, u); r_ = lerp(-7, 0, u)
        c.save(); c.translate(W / 2, H / 2); c.rotate(r_); c.scale(s_ * 0.94 + 0.06 * u, s_ * 0.94 + 0.06 * u); c.translate(-W / 2, -H / 2)
        c.save(); c.clipRect(skia.Rect(0, 0, W, H)); draw_shot(c, sh, t); c.restore()
        c.drawRect(skia.Rect(0, 0, W, H), P(WHITE, stroke=30)); c.drawRect(skia.Rect(0, 0, W, H), inkp(8))
        c.restore()
    else:
        draw_shot(c, sh, t)
    freeze_card(c, t, sh)
    typography(c, t)
    if t > 121.2:
        d = t - 121.2
        c.save(); c.translate(W / 2, H * 0.42); c.rotate(-4); c.scale(ease_out_back(d / 0.4), ease_out_back(d / 0.4))
        c.drawRect(skia.Rect(-640, -150, 640, 70), P(RED)); c.drawRect(skia.Rect(-640, -150, 640, 70), inkp(8))
        slab_word(c, 'ВАЖНЫЙ КОМОК', 150, FONT_BLACK, WHITE, 255, INK, INK)
        c.restore()
        if d > 0.6:
            f2 = font(48, F_COND); s = 'PHONK1S'; w = f2.measureText(s)
            c.drawString(s, W / 2 - w / 2, H * 0.42 + 150, f2, P(WHITE, int(255 * clamp((d - 0.6) / 0.4))))
    inv = any(0 <= t - x < 0.034 for x in sh.inv)
    post.finish(c, t, inv)
    fade = clamp(1 - t / 0.5) + clamp((t - 125.0) / 1.3)
    if fade > 0: c.drawRect(skia.Rect(0, 0, W, H), P(INK, int(255 * clamp(fade))))


def make_surface():
    w, h = int(W * SS), int(H * SS)
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    return arr, skia.Surface(arr)


def frame_into(c, post, t):
    c.save(); c.scale(SS, SS); render_frame(c, post, t); c.restore()


def render_range(f0, f1, out):
    arr, surf = make_surface(); c = surf.getCanvas(); post = Post()
    h, w = arr.shape[:2]
    enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{w}x{h}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '10', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(f0, f1):
        tt = f / FPS
        frame_into(c, post, tt)
        enc.stdin.write(arr.tobytes())
        if (f - f0) % 240 == 0: print(f'[{out}] {f - f0}/{f1 - f0} t={tt:.1f} {(time.time() - t0) / max(1, f - f0 + 1):.3f}s/f', flush=True)
    enc.stdin.close(); enc.wait()


def still(ts, path):
    global SS
    arr, surf = make_surface(); c = surf.getCanvas(); post = Post()
    from PIL import Image
    tiles = []
    for t in ts:
        t0 = time.time(); frame_into(c, post, t)
        tiles.append(Image.fromarray(arr[:, :, :3].copy()).resize((480, 270), Image.LANCZOS))
        print(f't={t} {time.time() - t0:.3f}s', flush=True)
    cols = 4; rows = math.ceil(len(tiles) / cols)
    sheet = Image.new('RGB', (480 * cols, 270 * rows))
    for k, im in enumerate(tiles): sheet.paste(im, ((k % cols) * 480, (k // cols) * 270))
    sheet.save(path, quality=90)


def scan():
    import traceback
    arr, surf = make_surface(); c = surf.getCanvas(); post = Post()
    t = 0.0; bad = 0; seen = set()
    while t < DUR:
        try: frame_into(c, post, t)
        except Exception:
            bad += 1; key = traceback.format_exc().strip().splitlines()[-1]
            if key not in seen: seen.add(key); print('ERR', round(t, 2)); traceback.print_exc()
        t += 0.2
    print('scan errors:', bad)


if __name__ == '__main__':
    m = sys.argv[1]
    if m == 'still': still([float(x) for x in sys.argv[3:]], sys.argv[2])
    elif m == 'range': render_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif m == 'scan': scan()
