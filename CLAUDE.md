# SpotHopper Site Clone Protocol

## Gold Standard Reference
Template repo: `/Users/chuckpfahler/liberty-collective/`
Performance target: 90+ PageSpeed mobile on every page
SEO target: 100 PageSpeed SEO score on every page

## When cloning a SpotHopper site, follow this protocol exactly:

### Step 0: Discover ALL pages automatically
```bash
# Extract sitemap from the source site
curl -sL 'https://www.TARGET.com/sitemap.xml'
# If sitemap index, follow child sitemaps:
curl -sL 'https://www.TARGET.com/wp-sitemap-posts-page-1.xml' | grep '<loc>'
# Also crawl navigation for pages not in sitemap:
curl -sL 'https://www.TARGET.com/' | grep -oE 'href="/[^"]*"' | sort -u
# Also check for vendor/restaurant subpages in nav dropdowns
# Combine all sources into a MASTER PAGE LIST before writing any code
```
**Do not start building until the master page list is complete and confirmed with the user.**

### Step 1: For EVERY page — extract source HTML first
Before writing ANY content for a page:
```bash
curl -sL 'https://www.TARGET.com/PAGE/' > /tmp/page-source.html
```
Then extract the EXACT content section. Find the content between the navigation and footer. Extract:
- Every heading (h1, h2, h3) with exact text
- Every paragraph with exact text
- Every link with exact href
- Every image with exact src and alt
- The CSS values from inline styles: padding, font-size (clamp values), font-weight, text-transform, colors
- The layout structure: wp-block-columns (flex 2-col or 3-col), wp-block-group (constrained 90% width)

### CRITICAL RULE: Never write content from memory or assumption
Every piece of text on our site must come from `curl` output of the source page. If you can't find content via curl, tell the user — do not fabricate or rewrite content.

### Step 2: Match the visual layout using source CSS values
SpotHopper uses WordPress block editor. The key layout patterns are:
- `wp-block-columns is-layout-flex` = flex row with `gap: 2em`, `flex-wrap: nowrap`
- `wp-block-column is-layout-flow` = flex child, equal width
- `wp-container-core-group-is-layout-*` with `max-width: 90%; margin: auto`
- Headings: `padding-top:20px;padding-bottom:10px` (h3), `padding-bottom:10px` (h2)
- Paragraphs: `padding-top:5px;padding-bottom:5px`
- Fonts: Anton (headings), Figtree (body), Great Vibes (script/decorative)
- All text-align: center for content sections

**Use the EXACT clamp() values from the source, not approximations.**

### Step 3: Use the Liberty Collective template structure
Copy the template and modify. The shared components are:
- Navigation HTML (update links/labels per client)
- Footer contact section (update address, hours, phone, social links)
- Modal HTML (birthday, contact forms)
- Floating widgets (birthday pill, contact fab)
- Mobile menu and mobile footer bar
- `assets/css/styles.css` — the full design system
- `assets/css/icons.css` — SVG icon replacement
- `assets/js/main.js` — interactive components
- `_headers` — security + cache headers

### Step 4: Image optimization (do this BEFORE building pages)
Download ALL images from the source site first:
```bash
# Get every image URL from the source
curl -sL 'https://www.TARGET.com/' | grep -oE 'https://static[^"'\'']+\.(jpg|png|webp)' | sort -u
# Download each one
# Convert ALL to WebP at appropriate sizes:
# - Background images: 1200px wide, quality 60
# - Gallery/card images: match display dimensions, quality 70
# - Logo: keep size, quality 80
# - Video poster: match display dimensions, quality 75
# Hero video: ffmpeg -crf 34 -preset slow -vf "scale=1280:-2" -an -movflags +faststart
# Subset Great Vibes font to only characters used on the site
```

### Step 5: SEO — every single page gets ALL of these
- `<title>` unique, keyword-targeted, under 60 chars, includes location
- `<meta name="description">` unique, under 160 chars, includes location and key terms
- `<link rel="canonical">` self-referencing
- `<meta property="og:title">` matches title
- `<meta property="og:description">` matches meta description
- `<meta property="og:type" content="website">`
- `<meta property="og:url">` matches canonical
- `<meta property="og:image">` MUST be a 1200x630 venue photo (JPG for compatibility), NOT the logo. Full absolute URL required.
- `<meta property="og:locale" content="en_US">`
- `<meta name="twitter:card" content="summary_large_image">`
- At least 1 JSON-LD structured data block (type depends on page)
- BreadcrumbList JSON-LD on all subpages

### Step 6: Performance rules (non-negotiable)
1. **Zero external CDN image/font/CSS dependencies** — self-host everything
2. **All images WebP**, sized to display dimensions
3. **Hero video self-hosted**, compressed to under 5MB
4. **Great Vibes font subsetted** to only used characters
5. **LCP element must be an `<img>` tag** with `fetchpriority="high"`, NOT a CSS background-image
6. **Do NOT defer stylesheets** — costs more LCP delay than it saves
7. **Inline critical CSS in homepage `<head>`** for header, hero, and first content section
8. **Preload LCP image and primary fonts** in `<head>`
9. **Leaflet CSS non-render-blocking** via `media="print" onload="this.media='all'"`
10. **`_headers` file** must set `Cache-Control: public, max-age=31536000, immutable` on `/assets/*`
11. **Fonts in styles.css** must point to local paths, not SpotHopper CDN
12. After ALL pages built, verify: `grep -rn 'sh-websites.com\|spotapps.co' --include="*.html" --include="*.css"` returns ZERO

### Step 7: Sitemap and robots.txt
- sitemap.xml must include EVERY page (count must match `find . -name "index.html" | wc -l`)
- robots.txt must reference sitemap with production domain

### Step 8: Deploy
```bash
git init && git add -A && git commit -m "Initial commit"
gh repo create ChowdownMedia/SITE-NAME --public --source=. --push
wrangler pages project create SITE-NAME --production-branch main
wrangler pages deploy . --project-name SITE-NAME --branch main
```

### Step 9: Verify
- Run PageSpeed on deployed URL — must be 90+ mobile
- If under 90, check LCP breakdown for render delay > 500ms
- Verify all pages load correctly
- Verify no external CDN references remain

### Step 10: Redirects
Create `_redirects` file mapping all old SpotHopper URLs to new paths. Use Google Search Console to find all indexed pages on the old domain. Common patterns:
```
/menu          /food-beverage/  301
/contact       /#contact        301
/about-us      /about/          301
```

### Step 11: Accessibility
Target: 100 Lighthouse accessibility. Non-negotiable checklist:
- All images have descriptive `alt` text
- Sufficient color contrast on all text
- Keyboard navigable
- Touch targets minimum 48x48px with adequate spacing
- Heading elements in sequentially-descending order (no skipping h2 to h4)
- `<video>` elements have `<track kind="captions">`

### Step 12: Analytics & Search Console (at build time, not after)
- GA4 measurement ID installed before launch
- GSC verified under agency property on day one (DNS TXT record)
- Document GA4 and GSC property IDs in repo CLAUDE.md

### Step 13: GHL Integration
Forms must POST to GHL, not just sit as HTML. Before launch:
- [ ] GHL location stood up with data structured for API consumption
- [ ] Hours entered in GHL and confirmed returning via API
- [ ] Newsletter form wired to GHL (embed or API POST)
- [ ] Contact form wired to GHL
- [ ] Birthday/VIP capture wired to GHL
- [ ] Confirm form submissions hitting GHL CRM before launch
- [ ] Document GHL `locationId` and form IDs in CLAUDE.md

**GHL is the data layer. The site is the display layer. Hours and events should come from GHL via Cloudflare Worker, not be hardcoded in HTML.**

### Step 14: Reviews
- Google Places API call configured (agency API key)
- Filter: 4+ stars only
- Display: 3-5 rotating reviews
- Falls back gracefully if API unavailable

## Intake Brief (must be completed before building)
```
Client Name:
Domain (current registrar):
GHL Account ID:
GSC Property (agency account):
GA4 Measurement ID:
Google Place ID (for reviews):
Primary Brand Color (hex):
Secondary Brand Color (hex):
Logo file (WebP):
Phone:
Address:
Hours (all day parts):
Cuisine / Venue Type:
Social Links:
Ordering URLs:
GHL Form Embed ID (newsletter):
GHL Form Embed ID (contact):
GHL Form Embed ID (birthday/VIP):
Schema Type (Restaurant / FoodEstablishment / EntertainmentBusiness):
```
**If the intake brief isn't filled out, don't start building.**

## Infrastructure
- **Cloudflare Account**: `chuckp@livewiremediapartners.com` — super admin, never delegate
- **GitHub Org**: ChowdownMedia — one repo per client
- **Hosting**: Cloudflare Pages (free tier)
- **Dynamic Logic**: Cloudflare Workers ($5/month flat)
- **Domains**: Leave at current registrar, point DNS to Cloudflare — no transfer required
- **Credentials**: Proton Pass under Chowdown vault — never in repo files

## Developer Access Model
- Developers get access to specific GitHub repos only
- Push to feature branch — Chuck reviews and merges to `main`
- `main` auto-deploys to Cloudflare Pages
- Developers NEVER receive Cloudflare credentials
- All API keys and GHL credentials in Proton Pass — never in repo files

## DNS Migration
See DNS-MIGRATION.md for zero-downtime procedure. Always capture MX/TXT/CNAME records BEFORE switching nameservers.

## What NOT to do
- Do NOT guess CSS values — always extract from source
- Do NOT fabricate page content — always extract from source
- Do NOT use Font Awesome — use icons.css
- Do NOT defer CSS — the LCP tradeoff is not worth it
- Do NOT use CSS background-image for LCP elements — use `<img>` tags
- Do NOT load fonts from external CDNs — self-host
- Do NOT skip pages — discover ALL pages before starting
- Do NOT use agents for this work — do it directly
- Do NOT open new windows
