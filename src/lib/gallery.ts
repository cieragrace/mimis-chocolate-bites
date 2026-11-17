/**
 * Folder-driven gallery loader for /gallery.
 *
 * Drop photos/videos into src/assets/gallery/ and rebuild — nothing else.
 * See src/assets/gallery/README.md for naming, captions and ordering.
 *
 * - Photos are imported as ImageMetadata so Astro optimizes them (WebP).
 * - Videos are imported with `?url`, so Vite copies them (hashed) into the build.
 * - `<name>.poster.<img>` is used as the poster for `<name>.<video>` and is
 *   not shown as its own tile.
 * - Optional per-file overrides live in src/data/gallery.json.
 *
 * !! The `_placeholder-*.png` files in src/assets/gallery/ are TEMPORARY and
 *    must be deleted when Mimi's real media lands.
 */
import type { ImageMetadata } from 'astro';
import overridesJson from '../data/gallery.json';

interface Override {
  alt?: string;
  caption?: string;
  order?: number;
  hidden?: boolean;
}
const overrides = overridesJson as Record<string, Override>;

const imageMods = import.meta.glob<{ default: ImageMetadata }>(
  '/src/assets/gallery/*.{jpg,jpeg,png,webp,avif,JPG,JPEG,PNG,WEBP,AVIF}',
  { eager: true },
);
const videoMods = import.meta.glob<string>('/src/assets/gallery/*.{mp4,webm,mov,MP4,WEBM,MOV}', {
  eager: true,
  query: '?url',
  import: 'default',
});

export type GalleryItem =
  | { kind: 'image'; file: string; alt: string; caption: string; order?: number; image: ImageMetadata }
  | { kind: 'video'; file: string; alt: string; caption: string; order?: number; url: string; poster?: ImageMetadata };

const BRAND = "Mimi's Chocolate Bites";
const baseName = (path: string) => path.split('/').pop() as string;
const stem = (file: string) => file.replace(/\.[^.]+$/, '');

/** "2026-11-02_cake-pops.jpg" → "Cake pops — Mimi's Chocolate Bites" */
function deriveAlt(file: string, kind: 'image' | 'video'): string {
  const words = stem(file)
    .replace(/^_placeholder-/, '')
    .replace(/^\d{4}-\d{2}-\d{2}[-_ ]?/, '')
    .replace(/[-_]+/g, ' ')
    .trim();
  // Instagram's own download names are just numbers — no useful words there.
  if (!/[a-z]{2,}/i.test(words)) {
    return `${kind === 'video' ? 'Video' : 'Treats'} from Mimi's kitchen — ${BRAND}`;
  }
  return `${words[0].toUpperCase()}${words.slice(1)} — ${BRAND}`;
}

export function getGalleryItems(): GalleryItem[] {
  const posters = new Map<string, ImageMetadata>();
  const items: GalleryItem[] = [];

  for (const [path, mod] of Object.entries(imageMods)) {
    const file = baseName(path);
    const m = file.match(/^(.*)\.poster\.[^.]+$/);
    if (m) {
      posters.set(m[1], mod.default);
      continue;
    }
    const o = overrides[file] ?? {};
    if (o.hidden) continue;
    items.push({
      kind: 'image',
      file,
      alt: o.alt || deriveAlt(file, 'image'),
      caption: o.caption ?? '',
      order: o.order,
      image: mod.default,
    });
  }

  for (const [path, url] of Object.entries(videoMods)) {
    const file = baseName(path);
    const o = overrides[file] ?? {};
    if (o.hidden) continue;
    items.push({
      kind: 'video',
      file,
      alt: o.alt || deriveAlt(file, 'video'),
      caption: o.caption ?? '',
      order: o.order,
      url,
      poster: posters.get(stem(file)),
    });
  }

  // pinned (`order`) first, ascending; then filename Z→A (date-prefixed = newest first)
  return items.sort((a, b) => {
    const ao = a.order ?? Infinity;
    const bo = b.order ?? Infinity;
    if (ao !== bo) return ao - bo;
    return b.file.localeCompare(a.file, undefined, { numeric: true });
  });
}
