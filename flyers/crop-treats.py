"""Lift Mimi's product photos off her two pricing flyers into public/img/treats/.

The flyers in this folder are the originals she sent; everything under
public/img/treats/ is generated from them by this script, so re-run it rather
than hand-editing the PNGs:

    ../../NEXUS/.venv/bin/python crop-treats.py

Each crop keys its flyer's background colour to transparent, then trims to the
treat's bounding box. Regions are hand-tuned pixel boxes — if a crop clips a
treat or catches a stray bit of her artwork (a title letter, one of the pink
swirl lines, a card border), nudge that entry's numbers.
"""

from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
OUT = HERE.parent / 'public' / 'img' / 'treats'

DOZEN = HERE / '9753E63E-A751-464A-B6DF-6B3FC431339F.PNG'  # pink "By the Dozen"
PACKAGES = HERE / '4F6B7A88-21B0-44DC-B5D1-E66FC18517F5.PNG'  # cream "Treat Packages"

# Background colours sampled from each flyer. DOZEN_PANEL is kept for reference
# — that flyer is the drawing reference for TreatIllustration.astro, not a crop
# source, since it's too low-res to crop cleanly.
DOZEN_PANEL = (247, 222, 214)
DOZEN_CARD = (61, 38, 19)  # the brown her treats are photographed on
PKG_CREAM = (248, 237, 226)
PKG_BORDER = (220, 158, 140)  # the thin card outline on the packages flyer


def near(colour, target, tol):
    return all(abs(colour[i] - target[i]) < tol for i in range(3))


def isolate_on_brown(img, box, card=DOZEN_CARD, tol=26, scale=3):
    """Crop a By-the-Dozen treat and repaint everything around it flat brown.

    Cropping alone can't give a clean treat: her cards carry pink swirl lines
    and title lettering that run right up beside the food, and shrinking the
    box to dodge them clips the treat instead. So this keeps only the treat and
    paints the rest with the card's own brown.

    How it decides what the treat is: mark every pixel that differs from the
    card brown, keep the largest connected blob of those (the food), then flood
    in from the border and repaint whatever that flood can reach. Anything the
    flood can't reach is enclosed by the treat — the dark centre of an Oreo,
    say — so it keeps its original pixels rather than being flattened.
    """
    tile = img.crop(box).convert('RGB')
    w, h = tile.size
    px = tile.load()

    subject = [[not near(px[x, y], card, tol) for x in range(w)] for y in range(h)]

    # largest connected blob of "not background" = the treat
    seen = [[False] * w for _ in range(h)]
    best = []
    for sy in range(h):
        for sx in range(w):
            if not subject[sy][sx] or seen[sy][sx]:
                continue
            blob, stack = [], [(sx, sy)]
            seen[sy][sx] = True
            while stack:
                x, y = stack.pop()
                blob.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and subject[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if len(blob) > len(best):
                best = blob

    treat = [[False] * w for _ in range(h)]
    for x, y in best:
        treat[y][x] = True

    # flood in from the edges over everything that isn't the treat
    outside = [[False] * w for _ in range(h)]
    stack = [(x, y) for x in range(w) for y in (0, h - 1) if not treat[y][x]]
    stack += [(x, y) for y in range(h) for x in (0, w - 1) if not treat[y][x]]
    for x, y in stack:
        outside[y][x] = True
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not treat[ny][nx] and not outside[ny][nx]:
                outside[ny][nx] = True
                stack.append((nx, ny))

    for y in range(h):
        for x in range(w):
            if outside[y][x]:
                px[x, y] = card

    return tile.resize((w * scale, h * scale), Image.LANCZOS)


def drop_small_blobs(tile, min_height=34):
    """Erase leftover opaque specks that are too short to be food.

    Lets the packages-flyer boxes be drawn generously: any line of her card
    text or border dash caught in the crop is only a few px tall and gets
    cleared, while the treats — all far taller — survive. Without this, a box
    roomy enough to not clip the cake pop also swallows the bullet above it.
    """
    w, h = tile.size
    px = tile.load()
    seen = [[False] * w for _ in range(h)]
    for sy in range(h):
        for sx in range(w):
            if px[sx, sy][3] == 0 or seen[sy][sx]:
                continue
            blob, stack = [], [(sx, sy)]
            seen[sy][sx] = True
            while stack:
                x, y = stack.pop()
                blob.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] > 0 and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            top = min(y for _, y in blob)
            bottom = max(y for _, y in blob)
            if bottom - top < min_height:
                for x, y in blob:
                    px[x, y] = (*px[x, y][:3], 0)
    return tile


def lift(img, box, keys, scale=1, strays=None, despeckle=False):
    """Crop `box`, knock out any colour in `keys`, drop `strays`, trim, scale."""
    tile = img.crop(box).convert('RGBA')
    px = tile.load()
    w, h = tile.size
    for y in range(h):
        for x in range(w):
            colour = px[x, y][:3]
            if any(near(colour, t, tol) for t, tol in keys) or (
                strays and strays(x, y, w, h)
            ):
                px[x, y] = (*colour, 0)
    if despeckle:
        tile = drop_small_blobs(tile)
    tile = tile.crop(tile.getbbox())
    if scale != 1:
        tile = tile.resize((tile.width * scale, tile.height * scale), Image.LANCZOS)
    return tile


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # ── By the Dozen: Mimi's photo of each treat ───────────────────────────
    # That flyer is only 512x640, so these are small and get upscaled 3x. They
    # are her product shots and she wants them used, so soft beats redrawn.
    # Boxes leave a couple of px of margin past each treat's true edge — these
    # are rounded objects, and a box drawn flush shaves a visible flat off the
    # bottom of the Oreo or the sides of the cakesicle.
    dozen = Image.open(DOZEN).convert('RGB')
    dozen_keys = [(DOZEN_PANEL, 26)]
    # Bounds were read off a coordinate grid drawn over the flyer, not guessed
    # — every treat sits on her dark card, so an alpha bounding box can't find
    # their edges and an eyeballed box clips them. Boxes are deliberately roomy:
    # isolate_on_brown repaints whatever else falls inside, so giving the treat
    # margin is free and guarantees nothing gets clipped.
    # The Oreo's chocolate wafer is nearly the same brown as the card it sits
    # on, so it needs a tighter tolerance or the wafer reads as background and
    # gets painted away, leaving a floating cream filling.
    for name, box, tol in (
        # Oreo's box also has to stay inside its card: at this tolerance the
        # pink panel beyond the card edge counts as subject and, touching the
        # cookie, would be kept as part of the same blob.
        ('oreo', (167, 363, 234, 423), 13),
        ('krispie', (378, 374, 452, 438), 26),
        ('cakesicle', (191, 456, 250, 543), 26),
        ('pretzel', (264, 488, 350, 554), 26),
    ):
        isolate_on_brown(dozen, box, tol=tol).save(OUT / f'{name}.png')

    # ── Treat Packages: the treat cluster on each tier's card ──────────────
    # This flyer is 1024x1536, so no upscaling needed.
    packages = Image.open(PACKAGES).convert('RGB')
    pkg_keys = [(PKG_CREAM, 30), (PKG_BORDER, 30), ((255, 250, 245), 14)]
    # Roomy boxes on purpose — despeckle clears the card text and border dashes
    # that come with the extra margin, and the old tight boxes were shaving the
    # top off each cake pop.
    for name, box in {
        'pkg-mini': (54, 1062, 324, 1272),
        'pkg-standard': (378, 1100, 622, 1310),
        'pkg-deluxe': (690, 1062, 940, 1272),
    }.items():
        lift(packages, box, pkg_keys, despeckle=True).save(OUT / f'{name}.png')

    # ── Treat Packages: her three "basic decor" illustrations ─────────────
    # Boxes stop short of the strip's own border rule (y=1398) and, for the
    # drizzle, of the "BASIC DECOR INCLUDES:" lettering above it (ends y=1324).
    # Keying the cream hollows each circle out, leaving her ring + artwork.
    for name, box in {
        'decor-dipped': (163, 1296, 270, 1396),
        'decor-drizzled': (443, 1326, 511, 1396),
        'decor-sprinkles': (696, 1326, 772, 1396),
    }.items():
        lift(packages, box, pkg_keys, scale=2).save(OUT / f'{name}.png')

    for f in sorted(OUT.iterdir()):
        print(f.name, Image.open(f).size)


if __name__ == '__main__':
    main()
