# Brand assets

Tachocline Industries mark: a magnetically active Sun with coronal loops, dark orange on black. Themes: eclipse, prominences, plage, faculae, sunspots, flares, tachocline / sub-surface loops, magnetic activity.

## Files
| File | Role |
|---|---|
| `ti-logo.svg` | Vector master |
| `ti-logo-512.png`, `ti-logo-192.png` | App / PWA icons |
| `favicon.ico` | Browser favicon (16 + 32 px) |
| `ti-hero-wide.png` / `.webp` | Desktop hero (1920×1080) |
| `ti-hero-tall.png` / `.webp` | Mobile hero (1080×1920) |
| `LICENSE-ASSETS.md` | Creator and rights |

Runtime copies used by the Vite app live under `web/public/` (`favicon.ico`, `brand/ti-logo.svg`, icon PNGs). Change the SVG master here, then re-export and copy into `web/public/` before committing.

## Rebuild icons from the SVG
```bash
rsvg-convert -w 512 -h 512 assets/brand/ti-logo.svg -o assets/brand/ti-logo-512.png
rsvg-convert -w 192 -h 192 assets/brand/ti-logo.svg -o assets/brand/ti-logo-192.png
rsvg-convert -w 32 -h 32 assets/brand/ti-logo.svg -o /tmp/ti-32.png
rsvg-convert -w 16 -h 16 assets/brand/ti-logo.svg -o /tmp/ti-16.png
magick /tmp/ti-16.png /tmp/ti-32.png assets/brand/favicon.ico
cp assets/brand/ti-logo.svg assets/brand/ti-logo-192.png assets/brand/ti-logo-512.png web/public/brand/
cp assets/brand/favicon.ico web/public/favicon.ico
```
