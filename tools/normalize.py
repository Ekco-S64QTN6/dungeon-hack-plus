"""Turn foreign art into Dungeon Hack-ready indexed frames.

Dungeon Hack palette model (measured from HACK.RES):
  0..223   fixed colours shared by monsters, items, portraits, UI (Main Base Palette)
  224..238 floor ramp   } "wall/floor palette NN": 15-step brightness ramp (0 = brightest)
  240..254 wall ramp    }  + 1 accent; recoloured per dungeon level, shaded by stepping down the ramp
So wall/floor art is stored as *brightness levels*, never as colours.
"""
import numpy as np
from PIL import Image

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5


def luminance(rgb):
    a = np.asarray(rgb, dtype=np.float32)
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def to_ramp(rgb, base=240, levels=15, dither=True, stretch=(2, 98)):
    """RGB array -> ramp indices base..base+levels-1 (base = brightest)."""
    lum = luminance(rgb)
    lo, hi = np.percentile(lum, stretch)
    t = np.clip((lum - lo) / max(1.0, hi - lo), 0, 1) * (levels - 1)
    if dither:
        h, w = t.shape
        t = t + np.tile(BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w] * 0.9
    lvl = np.clip(np.rint(t), 0, levels - 1).astype(np.uint8)
    return (base + (levels - 1 - lvl)).astype(np.uint8)


def dh_sprite_indices(res):
    """Palette indices DH's own monster sprites use (80x88, 6 frames): fixed colours known to look
    the same on every level. Portraits and icons are quantized to these."""
    import aesop
    out = set()
    for i in res.indices():
        p = res.entry(i)[2]
        if aesop.kind(p, '') != 'old_shapes':
            continue
        fr = aesop.decode_shapes(p)
        if len(fr) == 6 and fr[0][:2] == (80, 88):
            for w, h, px, m in fr:
                out.update(v for v, mm in zip(px, m) if mm)
    return out


def quantize_fixed(rgb, palette, allowed):
    """Nearest colour (redmean metric) restricted to `allowed` palette indices."""
    pal = np.array(palette, dtype=np.float32).reshape(-1, 3)
    idx = np.array(sorted(allowed))
    cand = pal[idx]
    px = np.asarray(rgb, dtype=np.float32).reshape(-1, 1, 3)
    rmean = (px[..., 0] + cand[None, :, 0]) / 2
    d = px - cand[None]
    dist = (2 + rmean / 256) * d[..., 0] ** 2 + 4 * d[..., 1] ** 2 + (2 + (255 - rmean) / 256) * d[..., 2] ** 2
    return idx[dist.argmin(1)].astype(np.uint8).reshape(np.asarray(rgb).shape[:2])


def fit_sprite(rgba_img, w, h):
    """Scale to fit w x h keeping aspect, anchored bottom-centre (DH monster frames are 80x88)."""
    im = rgba_img.convert('RGBA')
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    s = min(w / im.width, h / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.NEAREST if s >= 1 else Image.LANCZOS)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.paste(im, ((w - im.width) // 2, h - im.height), im)
    return out


def warp_to_mask(tex, mask, w, h):
    """Map a flat texture (H x W array) onto the opaque area of an existing DH wall panel.

    Each target column's opaque run is one texture column; u is interpolated
    perspective-correctly using column height as 1/z, so side-wall trapezoids
    foreshorten like the original art. Returns (pixels, mask) in target space.
    """
    m = np.frombuffer(bytes(mask), dtype=np.uint8).reshape(h, w)
    cols = [x for x in range(w) if m[:, x].any()]
    out = np.zeros((h, w), dtype=tex.dtype)
    if not cols:
        return out, m
    x0, x1 = cols[0], cols[-1]
    span = lambda x: (np.flatnonzero(m[:, x])[0], np.flatnonzero(m[:, x])[-1])
    hl = span(x0)[1] - span(x0)[0] + 1
    hr = span(x1)[1] - span(x1)[0] + 1
    th, tw = tex.shape
    for x in cols:
        t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        u = t * hr / ((1 - t) * hl + t * hr)
        tx = min(tw - 1, int(u * tw))
        ys = np.flatnonzero(m[:, x])
        y0, y1 = ys[0], ys[-1]
        v = ((ys - y0) / max(1, y1 - y0 + 1) * th).astype(int).clip(0, th - 1)
        out[ys, x] = tex[v, tx]
    return out, m


def slice_sheet(img, bg=(0, 0, 0), min_area=150):
    """Split a sprite sheet (e.g. an EOB monster .CPS) into RGBA crops, ordered row-major."""
    a = np.asarray(img.convert('RGB'))
    fg = np.any(a != np.array(bg, np.uint8), axis=2)
    h, w = fg.shape
    seen = np.zeros_like(fg)
    boxes = []
    for y0 in range(h):
        for x0 in range(w):
            if fg[y0, x0] and not seen[y0, x0]:
                stack = [(y0, x0)]; seen[y0, x0] = True
                ys, xs = [], []
                while stack:
                    y, x = stack.pop(); ys.append(y); xs.append(x)
                    for dy in (-2, -1, 0, 1, 2):          # 2-px reach joins thin gaps
                        for dx in (-2, -1, 0, 1, 2):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h and 0 <= nx < w and fg[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True; stack.append((ny, nx))
                if len(ys) >= min_area:
                    boxes.append((min(ys), min(xs), max(ys) + 1, max(xs) + 1))
    boxes.sort(key=lambda b: (b[0] // 40, b[1]))
    rgba = np.dstack([a, (fg * 255).astype(np.uint8)])
    return [Image.fromarray(rgba[t:b, l:r]) for t, l, b, r in boxes]


def ramp_shape(lums):
    """'single' for a bright->dark ramp (DH palettes 00-14), 'double' otherwise (15-20, EOB3 Forest)."""
    return 'single' if all(a >= b - 3 for a, b in zip(lums[:15], lums[1:15])) else 'double'


def to_ramp_target(rgb, profile, base, dither=True, stretch=(2, 98), lohi=None):
    """Posterize against the real ramp(s) the art will be shown with.

    profile: luminance of ramp indices 0..14 (mean over the palettes the game may
    pair with this art). Source luminance is stretched onto the profile's range and
    each pixel takes the index whose luminance rank is nearest, so two-ramp
    palettes (rising then falling) are handled as well as plain ramps.
    """
    prof = np.asarray(profile[:15], dtype=np.float32)
    order = np.argsort(prof, kind='stable')
    lum = luminance(rgb)
    lo, hi = lohi if lohi is not None else np.percentile(lum, stretch)
    target = prof[order[0]] + np.clip((lum - lo) / max(1.0, hi - lo), 0, 1) * (prof[order[-1]] - prof[order[0]])
    rank = np.interp(target, prof[order], np.arange(15, dtype=np.float32))
    if dither:
        h, w = rank.shape
        rank = rank + np.tile(BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w] * 0.9
    return (base + order[np.clip(np.rint(rank), 0, 14).astype(int)]).astype(np.uint8)
