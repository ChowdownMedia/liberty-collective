# Photography Needed — Westfield Collective

The following pages are using **placeholder images from Liberty Collective** (site 208). These are functional but not specific to the Westfield location. The client should provide Westfield-specific photography to replace them.

Each placeholder is marked in the HTML with:
```html
<!-- PLACEHOLDER: client to provide Westfield-specific photo -->
```

## Pages Requiring Client Photography

### 1. Bristol's (`/vendor/bristols/`)
- **Current placeholder:** `s208-pulled-pork-sandwich-1024x683.webp`
- **What's needed:** Bristol's hero/feature image — food shot or interior photo specific to the Westfield location
- **Recommended size:** 1024x683 or larger, landscape orientation

### 2. Collective Pour (`/vendor/collective-pour/`)
- **Current placeholder:** `s208-enscape_2024-12-04-19-00-09-1024x576.webp`
- **What's needed:** Collective Pour hero/feature image — self-pour wall or interior photo specific to the Westfield location
- **Recommended size:** 1024x576 or larger, landscape orientation

### 3. Main Bar (`/vendor/main-bar/`)
- **Current placeholder:** `s208-drinks-scaled-1-1024x683.webp`
- **What's needed:** Main Bar hero/feature image — bar interior or signature cocktail photo specific to the Westfield location
- **Recommended size:** 1024x683 or larger, landscape orientation

### 4. Mezzanine Bar (`/vendor/mezzanine-bar/`)
- **Current placeholder:** `s208-mezz-drinks-1024x683.webp`
- **What's needed:** Mezzanine Bar hero/feature image — second-floor bar or drinks photo specific to the Westfield location
- **Recommended size:** 1024x683 or larger, landscape orientation

### 5. Ms. Lei Lei's (`/vendor/ms-lei-leis/`)
- **Current placeholder:** `s208-img_1444-1024x669.webp`
- **What's needed:** Ms. Lei Lei's hero/feature image — food shot or interior photo specific to the Westfield location
- **Recommended size:** 1024x669 or larger, landscape orientation

### 6. Roberto and Miguel's (`/vendor/roberto-and-miguels/`)
- **Current placeholder:** `s208-9-tacos-layout-819x1024.webp`
- **What's needed:** Roberto and Miguel's hero/feature image — taco spread or interior photo specific to the Westfield location
- **Recommended size:** 819x1024 or larger, portrait orientation

## How to Replace

When client provides photos:
1. Run through the asset pipeline: `python3 tools/assets.py` with new images
2. Update the HTML to reference the new local path
3. Remove the `<!-- PLACEHOLDER -->` comment
4. Deploy

## Notes
- All other images on the site are Westfield-specific (site 222) or shared design assets
- The background texture (`westfield-texture-bg.webp`) is a generic SpotHopper asset used on both sites — not a placeholder, safe to keep
