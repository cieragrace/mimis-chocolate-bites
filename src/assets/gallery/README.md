# Gallery media — drop files here, rebuild, done

Everything in this folder shows up on /gallery automatically (no code edits).

- Photos: .jpg .jpeg .png .webp .avif (optimized to WebP at build time)
- Videos: .mp4 .webm .mov (copied as-is; prefer .mp4 — Instagram downloads are .mp4,
  and Cloudflare Pages rejects any single file over 25 MB)
- Optional video poster: name an image `<video-name>.poster.jpg`
  (e.g. `cake-reveal.mp4` + `cake-reveal.poster.jpg`). It is used as the video's
  still frame and does NOT appear as its own tile.

How the page lays them out:

- **Photos** → a grid at the top ("Recent treats"): uniform 4:5 tiles, 2 across on
  phones, 3 on tablets, 4 on desktop. The first 12 show; a "See all N photos"
  button reveals the rest. Crop photos to 4:5 before dropping them in (tiles use
  object-cover, so other shapes get trimmed). Tapping a photo opens the viewer;
  its arrows move through photos only.
- **Videos** → the auto-rotating carousel below ("Watch it come together"),
  videos only. Tapping the centre video opens the viewer with sound; its arrows
  move through videos only.
- A section with nothing in it simply doesn't show.

Order (within each section): entries with an `order` first, then newest first if
files are named with a date prefix, e.g. `2026-11-02-cake-pops.jpg` (sorted by
filename, Z→A / newest→oldest).

Alt text is made from the filename ("2026-11-02-cake-pops.jpg" →
"Cake pops — Mimi's Chocolate Bites"). For better alt text, a caption, a
pinned order, or to hide a file, add an entry in `src/data/gallery.json`
keyed by the exact filename:

    "2026-11-02-cake-pops.jpg": { "alt": "...", "caption": "...", "order": 1, "hidden": false }

Entries with an `order` come first (1, 2, 3 …); the rest follow by filename.

