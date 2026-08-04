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

# Background colours sampled from each flyer.
DOZEN_PANEL = (247, 222, 214)
PKG_CREAM = (248, 237, 226)
PKG_BORDER = (220, 158, 140)  # the thin card outline on the packages flyer


def near(colour, target, tol):
    return all(abs(colour[i] - target[i]) < tol for i in range(3))


def lift(img, box, keys, scale=1, strays=None):
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
    tile = tile.crop(tile.getbbox())
    if scale != 1:
        tile = tile.resize((tile.width * scale, tile.height * scale), Image.LANCZOS)
    return tile


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # ── By the Dozen: one photo per treat ──────────────────────────────────
    # That flyer is only 512x640, so these come out small and get upscaled 3x.
    dozen = Image.open(DOZEN).convert('RGB')
    dozen_keys = [(DOZEN_PANEL, 26)]
    for name, box in {
        'oreo': (179, 363, 232, 423),
        'krispie': (384, 380, 447, 431),
        'pretzel': (276, 492, 339, 549),
    }.items():
        lift(dozen, box, dozen_keys, scale=3).save(OUT / f'{name}.png')

    # The cakesicle sits against one of her pink swirl lines, with a stray bit
    # of title lettering above it — neither keys out by colour, so cut them.
    def cakesicle_strays(x, y, w, h):
        return x > w * 0.78 or (x > w * 0.60 and y > h * 0.78) or (
            x < w * 0.30 and y < h * 0.15
        )

    lift(
        dozen, (201, 467, 249, 537), dozen_keys, scale=3, strays=cakesicle_strays
    ).save(OUT / 'cakesicle.png')

    # ── Treat Packages: the treat cluster on each tier's card ──────────────
    # This flyer is 1024x1536, so no upscaling needed.
    packages = Image.open(PACKAGES).convert('RGB')
    pkg_keys = [(PKG_CREAM, 30), (PKG_BORDER, 30), ((255, 250, 245), 14)]
    for name, box in {
        'pkg-mini': (38, 1085, 315, 1266),
        'pkg-standard': (352, 1120, 612, 1284),
        'pkg-deluxe': (658, 1085, 935, 1266),
    }.items():
        lift(packages, box, pkg_keys).save(OUT / f'{name}.png')

    for f in sorted(OUT.iterdir()):
        print(f.name, Image.open(f).size)


if __name__ == '__main__':
    main()
