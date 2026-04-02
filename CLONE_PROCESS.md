# SpotHopper to Chowdown Migration Process

Gold standard template: Liberty Collective (97 PageSpeed mobile)

## Prerequisites
- `wrangler` CLI installed and logged into client's Cloudflare account
- `gh` CLI logged into ChowdownMedia GitHub
- `ffmpeg`, `cwebp`, `pyftsubset` (fonttools) installed locally
- Liberty Collective repo cloned as template reference

## Phase 1: Site Discovery (15 min)

### 1a. Map the site structure
```bash
# Get all pages from the SpotHopper site
curl -sL 'https://www.TARGET-SITE.com/' | grep -oE 'href="/[^"]*"' | sort -u
```

### 1b. Extract the content from each page
```bash
# For each page, pull the main content HTML
curl -sL 'https://www.TARGET-SITE.com/PAGE/' | sed -n '/<main/,/<\/main>/p'
# OR for SpotHopper WordPress sites:
curl -sL 'https://www.TARGET-SITE.com/PAGE/' | grep -A200 'wp-block-heading'
```

### 1c. Identify all assets
```bash
# Fonts
curl -sL 'https://www.TARGET-SITE.com/' | grep -oE 'fonts/[^"'\'')*]+\.woff2' | sort -u
# Images  
curl -sL 'https://www.TARGET-SITE.com/' | grep -oE 'https://static[^"'\'']+\.(jpg|png|webp)' | sort -u
# Videos
curl -sL 'https://www.TARGET-SITE.com/' | grep -oE 'https://[^"'\'']+\.mp4' | sort -u
# Navigation links
curl -sL 'https://www.TARGET-SITE.com/' | grep -oE 'href="/[^"]*"' | sort -u
```

### 1d. Extract exact CSS values from each page
This is CRITICAL. Do NOT guess CSS values. For every content section:
```bash
curl -sL 'https://www.TARGET-SITE.com/PAGE/' | sed -n '/SECTION_START/,/SECTION_END/p'
```
Extract exact: padding, font-size (clamp values), font-family, text-transform, font-weight, colors, flex/grid layout, gap values.

### 1e. Document vendor pages
SpotHopper sites typically have vendor/restaurant concept subpages. List them all:
```bash
curl -sL 'https://www.TARGET-SITE.com/' | grep -oE '/vendor/[^/"]+' | sort -u
# OR check navigation for restaurant links
```

## Phase 2: Clone Template (30 min)

### 2a. Copy Liberty Collective structure
```bash
cp -r liberty-collective/ TARGET-SITE/
cd TARGET-SITE/
rm -rf .git assets/images/home/*
git init
```

### 2b. What to keep from the template
- `assets/css/styles.css` and `styles.min.css` — design system is shared across SpotHopper clones
- `assets/css/icons.css` — SVG icon replacement (same 20 icons used everywhere)
- `assets/js/main.js` and `main.min.js` — nav, modals, carousels
- `_headers` — security + cache headers
- Font face declarations in `<style>` blocks (Anton, Figtree, Great Vibes are standard SpotHopper fonts)
- Nav structure, footer, contact section, modal HTML — all identical across SpotHopper sites

### 2c. What to change per client
- All text content (headings, descriptions, hours, address, phone, email)
- Logo image
- Hero image/video
- Background images
- Vendor/restaurant pages (add/remove based on client concepts)
- Sport/activity pages (add/remove based on client amenities)  
- External links (ordering, reservations, social media)
- Schema markup (business name, address, phone, coordinates)
- Meta descriptions (keyword-targeted per page)
- Open Graph tags
- Canonical URLs
- Sitemap entries

## Phase 3: Content Migration (2-3 hours)

### 3a. Download and optimize ALL images first
```bash
mkdir -p assets/images/home

# Download all images from SpotHopper CDN
curl -sO 'https://static01.sh-websites.com/uploads/sites/XXX/...'

# Convert to WebP at appropriate sizes
# Background images: 1200px wide, q60
cwebp -q 60 -resize 1200 0 image.jpg -o image.webp

# Gallery/content images: match display dimensions, q70-80
cwebp -q 70 -resize 400 400 gallery.jpg -o gallery.webp

# Logo: keep original size, just convert
cwebp -q 80 logo.png -o logo.webp

# Hero video: compress to ~3-5MB, 720p, no audio, faststart
ffmpeg -i original.mp4 -c:v libx264 -crf 34 -preset slow -vf "scale=1280:-2" -an -movflags +faststart assets/hero-video.mp4
```

### 3b. Subset the Great Vibes font
Only needed if client uses the script font. Check which characters are needed:
```bash
grep -r 'class="script"\|parties-script\|hero-script' *.html
# Then subset to just those characters:
pyftsubset original-great-vibes.woff2 --text="Welcome toFresh food, seamless service" --flavor=woff2 --output-file=great-vibes-subset.woff2
```

### 3c. Update pages — work from the LIVE SITE CODE, not from memory
For every page:
1. `curl` the live SpotHopper page
2. Extract the exact content section HTML
3. Match the CSS values exactly (padding, font-size clamp values, etc.)
4. Replace content in the template
5. Update all image/link references to local paths

**NEVER guess spacing, layout, or CSS values. Always extract from source.**

### 3d. Update all references across ALL files
```bash
# Update logo everywhere
find . -name "index.html" -exec sed -i '' 's|OLD_LOGO_URL|/assets/images/home/logo.webp|g' {} +

# Update favicon everywhere  
find . -name "index.html" -exec sed -i '' 's|OLD_FAVICON_URL|/assets/images/home/favicon.webp|g' {} +

# Verify no external CDN references remain
grep -rn 'sh-websites.com\|spotapps.co' --include="*.html" --include="*.css"
# This should return ZERO results
```

## Phase 4: SEO Setup (1 hour)

### 4a. Every page MUST have
- [ ] `<title>` — unique, keyword-targeted, under 60 chars
- [ ] `<meta name="description">` — unique, compelling, under 160 chars, includes location
- [ ] `<link rel="canonical">` — self-referencing
- [ ] Open Graph tags (og:title, og:description, og:type, og:url, og:image)
- [ ] Twitter card meta tags
- [ ] At least 1 structured data block (JSON-LD)
- [ ] BreadcrumbList schema on subpages

### 4b. Structured data by page type
- **Homepage:** LocalBusiness + BreadcrumbList + (optional Event)
- **Vendor/Restaurant pages:** FoodEstablishment + BreadcrumbList
- **Event pages:** Event schema + BreadcrumbList
- **Sports/Activity pages:** SportsActivityLocation + BreadcrumbList
- **About page:** Organization + BreadcrumbList

### 4c. Sitemap
```bash
# After all pages are created, verify sitemap has every page:
echo "Pages in sitemap:" $(grep -c '<loc>' sitemap.xml)
echo "HTML pages on disk:" $(find . -name "index.html" | wc -l)
# These numbers must match
```

### 4d. robots.txt
```
User-agent: *
Allow: /
Sitemap: https://www.TARGET-SITE.com/sitemap.xml
```

## Phase 5: Performance Optimization (30 min)

### 5a. Homepage critical inline CSS
The homepage MUST have inline critical CSS in `<head>` covering:
- Reset (*,*::before,*::after box-sizing)
- body defaults
- .site-header (fixed positioning)
- .navbar, .nav-container, .nav-logo
- .hero, .hero-video
- .section-welcome (the LCP section)
- .welcome-grid, .welcome-title, .welcome-text
- .container

### 5b. Do NOT defer stylesheets
We tested this — deferring CSS saves 160ms on render blocking but costs 2,000ms on LCP render delay. Not worth it. Keep stylesheets as normal `<link rel="stylesheet">`.

### 5c. Preload critical resources
```html
<link rel="preload" as="image" href="/assets/images/home/LCP_IMAGE.webp" fetchpriority="high">
<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/Anton.woff2" crossorigin>
<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/Figtree.woff2" crossorigin>
```

### 5d. LCP image MUST be an `<img>` tag, not CSS background-image
CSS background-images can't be discovered until CSS is parsed. Use an absolutely-positioned `<img>` with `fetchpriority="high"` instead.

### 5e. Leaflet map CSS must be non-render-blocking
```html
<link rel="stylesheet" href="leaflet.css" media="print" onload="this.media='all'">
```

### 5f. Verify zero external CDN dependencies
```bash
grep -rn 'sh-websites.com\|spotapps.co\|font-awesome' --include="*.html" --include="*.css"
# Must return ZERO results (except maybe og:image if using external)
```

## Phase 6: Deploy (10 min)

### 6a. GitHub
```bash
git add -A && git commit -m "Initial commit: TARGET-SITE static site"
gh repo create ChowdownMedia/TARGET-SITE --public --source=. --push
```

### 6b. Cloudflare Pages
```bash
wrangler pages project create TARGET-SITE --production-branch main
wrangler pages deploy . --project-name TARGET-SITE --branch main
```

### 6c. Verify deployment
```bash
# Check no external references
curl -s 'https://TARGET-SITE.pages.dev/' | grep -c 'sh-websites.com\|spotapps.co'
# Must be 0
```

### 6d. Run PageSpeed
Target: 90+ mobile on every page. If under 90, check:
1. Is the LCP a CSS background-image? Convert to `<img>`
2. Are stylesheets deferred? Don't defer them
3. Are images sized to display dimensions?
4. Are images WebP?
5. Is the hero video under 5MB?
6. Are fonts self-hosted?

## Phase 7: DNS Migration (when client is ready)

See DNS-MIGRATION.md for the zero-downtime procedure. Key steps:
1. Capture all current DNS records (MX, TXT, CNAME, A)
2. Set up all records in Cloudflare FIRST
3. Verify records match before switching nameservers
4. Switch nameservers
5. Don't delete old records for 48 hours
6. Test email delivery both directions

## Lessons Learned (Liberty Collective)

1. **NEVER guess CSS values.** Always curl the live site and extract exact values.
2. **Self-host everything.** External CDN = no cache control + extra DNS lookups.
3. **Font Awesome is 630KB for 20 icons.** Our icons.css is 19KB. Always use it.
4. **Subset decorative fonts.** Great Vibes went from 155KB to 9KB.
5. **Don't defer CSS.** The render delay costs more than the blocking saves.
6. **LCP must be an `<img>` tag** with fetchpriority="high", not a CSS background-image.
7. **Compress hero videos aggressively.** CRF 34, 720p, no audio. 13MB -> 3.5MB.
8. **Size images to display dimensions.** 800x800 displayed at 332x332 = wasted bytes.
9. **The styles.css has font URLs and image URLs embedded.** Update BOTH HTML and CSS files.
10. **Test on the correct Cloudflare URL.** The `-7iw.pages.dev` suffix matters.
