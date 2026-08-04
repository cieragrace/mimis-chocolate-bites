"""Lift the badge off Mimi's 2026-08 Treat Packages flyer into the site logo.

Regenerates public/img/logo.png and public/img/og-image.png from
948465AB-….PNG so the site logo matches the flyer's badge art:

    ../../NEXUS/.venv/bin/python make-logo.py

How the badge is cut out: it's a scalloped near-circle and — unlike the
old logo, whose truffles spilled past the rim — everything sits inside it,
so a supersampled ellipse mask (centre/radii hand-tuned below) is most of
the job. Don't be tempted to flood-recover "spill": the dark ring touches
the "Treat Packages" script below and a flood walks straight into the
lettering.

The one wrinkle: the flyer's chocolate-drip artwork hangs over the badge's
top arc, so there is no clean top rim to extract. Every drip hangs from
the crop's top edge, so a flood over dark pixels seeded from the top rows
finds exactly the drips (plus the rim they touch) without ever reaching
the "Mimi's" lettering, which floats separate. Repair is then two rules:
the whole top-half rim annulus is replaced by its mirror across the
badge's horizontal axis (the clean, symmetric bottom rim), and drip
pixels that fall INSIDE the rim become flat cream — they can't be
mirrored, since their mirror lands on the bonbons.

The og-image keeps the old card's look: its radial-gradient brown is
resampled from the previous og-image's corner/edge colours, with the new
badge pasted centred at the same size the old logo occupied.
"""

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).parent
IMG = HERE.parent / 'public' / 'img'
FLYER = HERE / '948465AB-804A-4150-AD46-B496B2E8FCB6.PNG'

# Badge outline, hand-tuned against the flyer. It's very slightly elliptical:
# ray-scans off the ring give a side radius ≈178 but a bottom radius ≈168
# (the top edge hides behind the drip artwork, so it's assumed symmetric).
CX, CY, RX, RY = 530, 236, 177, 169

def extract_badge():
    img = Image.open(FLYER).convert('RGB')
    box = (CX - RX - 4, CY - RY - 4, CX + RX + 4, CY + RY + 4)
    tile = img.crop(box).convert('RGBA')
    w, h = tile.size
    cx, cy = CX - box[0], CY - box[1]

    # supersampled ellipse mask for a smooth edge
    ss = 4
    mask = Image.new('L', (w * ss, h * ss), 0)
    ImageDraw.Draw(mask).ellipse(
        (ss * (cx - RX), ss * (cy - RY), ss * (cx + RX), ss * (cy + RY)),
        fill=255,
    )
    mask = mask.resize((w, h), Image.LANCZOS)

    # ── reconstruct the drip-covered top arc from the bottom rim ──────────
    px = tile.load()
    cream = px[cx, cy - 60][:3]  # flat badge interior

    # loose on purpose: the drips carry glossy tan highlights that a strict
    # "dark chocolate" test rejects, splitting the flood. Cream, the pink
    # ring and the hearts all still fail it.
    def dark(x, y):
        r, g, b = px[x, y][:3]
        return r < 210 and g < 160 and b < 150

    # flood the drips from the crop's top edge; they never touch the letters
    drip = [[False] * w for _ in range(h)]
    stack = [(x, y) for y in (0, 1, 2) for x in range(w) if dark(x, y)]
    for x, y in stack:
        drip[y][x] = True
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not drip[ny][nx] and dark(nx, ny):
                drip[ny][nx] = True
                stack.append((nx, ny))
    grown = [
        [
            any(
                drip[j][i]
                for j in range(max(0, y - 2), min(h, y + 3))
                for i in range(max(0, x - 2), min(w, x + 3))
            )
            for x in range(w)
        ]
        for y in range(h)
    ]

    # The bottom annulus isn't spotless either — bonbon corners and crumb
    # debris poke into its inner cream band at ~5 and ~7 o'clock, and a
    # straight mirror would stamp them onto the top. So dark mirror-source
    # pixels inside the annulus' cream band (the rim proper starts at
    # ρ≈0.885) are swapped for flat cream — EXCEPT in the thin band the
    # dashed ring occupies (ρ 0.828–0.868), whose dashes are themselves
    # dark and must survive the mirror. Crumbs sitting ON the dash band are
    # told apart from dashes by size: a dash stroke is a few dozen px, a
    # crumb cluster or bonbon corner far more. The real bottom keeps its
    # crumbs either way.
    def rho_at(x, y):
        return ((x - cx) / RX) ** 2 + ((y - cy) / RY) ** 2

    band = [
        [
            y >= cy and 0.82**2 < rho_at(x, y) < 0.875**2 and dark(x, y)
            for x in range(w)
        ]
        for y in range(h)
    ]
    intrusion = [[False] * w for _ in range(h)]
    seen = [[False] * w for _ in range(h)]
    for sy in range(cy, h):
        for sx in range(w):
            if not band[sy][sx] or seen[sy][sx]:
                continue
            blob, stack = [], [(sx, sy)]
            seen[sy][sx] = True
            while stack:
                x, y = stack.pop()
                blob.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and band[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if len(blob) > 70:
                for x, y in blob:
                    intrusion[y][x] = True

    for y in range(cy):
        for x in range(w):
            rho = rho_at(x, y)
            if rho > 0.80**2:
                ys = min(h - 1, 2 * cy - y)
                in_dash_band = 0.828**2 < rho < 0.868**2
                bad = intrusion[ys][x] if in_dash_band else dark(x, ys)
                if rho < 0.885**2 and bad:
                    px[x, y] = (*cream, 255)
                else:
                    px[x, y] = px[x, ys]
            elif grown[y][x]:
                px[x, y] = (*cream, 255)

    tile.putalpha(mask)
    return tile.crop(tile.getbbox())


def make_og(badge):
    # radial gradient sampled off the previous og-image's look
    W, H = 1200, 630
    centre, edge = (72, 48, 36), (40, 26, 19)
    og = Image.new('RGB', (W, H))
    opx = og.load()
    maxd = (0.5 * W) ** 2 + (0.5 * H) ** 2
    for y in range(H):
        for x in range(W):
            t = ((x - W / 2) ** 2 + (y - H / 2) ** 2) / maxd
            opx[x, y] = tuple(
                round(c + (e - c) * t) for c, e in zip(centre, edge)
            )
    scaled = badge.resize(
        (round(badge.width * 380 / badge.height), 380), Image.LANCZOS
    )
    og = og.convert('RGBA')
    og.alpha_composite(
        scaled, ((W - scaled.width) // 2, (H - scaled.height) // 2)
    )
    return og.convert('RGB')


def main():
    badge = extract_badge()
    badge.save(IMG / 'logo.png', optimize=True)
    print('logo.png', badge.size)
    og = make_og(badge)
    og.save(IMG / 'og-image.png', optimize=True)
    print('og-image.png', og.size)


if __name__ == '__main__':
    main()
