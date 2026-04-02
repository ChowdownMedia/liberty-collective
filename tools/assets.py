#!/usr/bin/env python3
"""
Chowdown Asset Pipeline — Module 3
Downloads all images/videos/fonts from content-brief.json,
optimizes them, and outputs asset-manifest.json mapping
original URLs to local paths.

Usage:
  python3 assets.py output/westfield-collective.com/content-brief.json

Output:
  - Downloads to output/{domain}/assets/
  - Manifest at output/{domain}/asset-manifest.json
"""

import sys
import os
import json
import re
import hashlib
import subprocess
from urllib.parse import urlparse

import requests


def slugify(text):
    """Convert text to a safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:60]


def get_extension(url):
    """Get file extension from URL."""
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'):
        return ext
    if ext in ('.mp4', '.webm'):
        return ext
    if ext in ('.woff', '.woff2', '.ttf', '.otf'):
        return ext
    return '.jpg'  # default for CDN URLs without extension


def short_hash(url):
    """Generate a short hash from URL for deduplication."""
    return hashlib.md5(url.encode()).hexdigest()[:8]


def download_file(url, output_path):
    """Download a file from URL."""
    try:
        resp = requests.get(url, timeout=30, stream=True)
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f'    Download error: {e}')
    return False


def convert_to_webp(input_path, output_path, quality=75, resize_width=None):
    """Convert image to WebP using cwebp."""
    cmd = ['cwebp', '-q', str(quality)]
    if resize_width:
        cmd.extend(['-resize', str(resize_width), '0'])
    cmd.extend([input_path, '-o', output_path])
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0
    except Exception:
        return False


def compress_video(input_path, output_path):
    """Compress video: 720p, CRF 34, no audio, faststart."""
    cmd = [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264', '-crf', '34', '-preset', 'slow',
        '-vf', 'scale=1280:-2', '-an', '-movflags', '+faststart',
        output_path, '-y'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        return result.returncode == 0
    except Exception:
        return False


def subset_font(input_path, output_path, text_chars):
    """Subset a font to only needed characters."""
    cmd = [
        'pyftsubset', input_path,
        f'--text={text_chars}',
        '--flavor=woff2',
        f'--output-file={output_path}'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0
    except Exception:
        return False


def classify_image(url, page_path):
    """Classify image for sizing: hero, background, gallery, content, logo."""
    url_lower = url.lower()
    if 'logo' in url_lower:
        return 'logo', 80, None
    if 'hero' in url_lower or 'banner' in url_lower:
        return 'hero', 60, 1920
    if 'welcome_back' in url_lower or 'about_03' in url_lower or 'gallery_back' in url_lower:
        return 'background', 60, 1200
    if 'beach' in url_lower or 'reviews' in url_lower:
        return 'background', 60, 1200
    if any(dim in url_lower for dim in ['-150x150', '-300x200', '-300x300', '-400x400']):
        return 'thumbnail', 75, None  # keep original size for thumbnails
    if '-1024x' in url_lower or '-1536x' in url_lower or '-2048x' in url_lower:
        return 'content-large', 70, 1200
    if '-768x' in url_lower:
        return 'content-medium', 70, None
    # Default
    return 'content', 70, 800


def run(brief_path):
    """Run the asset pipeline."""
    with open(brief_path) as f:
        brief = json.load(f)

    domain = brief['site']['domain'].replace('www.', '')
    output_dir = os.path.dirname(brief_path)
    assets_dir = os.path.join(output_dir, 'assets')
    images_dir = os.path.join(assets_dir, 'images')
    fonts_dir = os.path.join(assets_dir, 'fonts')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(fonts_dir, exist_ok=True)

    print(f'\n{"="*50}')
    print(f'  CHOWDOWN ASSET PIPELINE — Module 3')
    print(f'{"="*50}')
    print(f'Domain: {domain}\n')

    # Collect all unique image URLs across all pages
    all_images = {}  # url -> {pages, alt}
    all_videos = set()
    all_fonts = set()

    for page_path, page_data in brief['pages'].items():
        if page_data.get('error'):
            continue
        images = page_data.get('images', []) or []
        for img in images:
            src = img['src']
            if src not in all_images:
                all_images[src] = {'pages': [], 'alt': img.get('alt', ''), 'cdn': img.get('cdn', False)}
            all_images[src]['pages'].append(page_path)

    # Filter to CDN images only (skip external non-CDN images like map tiles)
    cdn_images = {url: data for url, data in all_images.items() if data['cdn']}

    print(f'Total unique images found: {len(all_images)}')
    print(f'CDN images to download: {len(cdn_images)}')

    # Download and convert images
    print(f'\n[Phase 1] Downloading and optimizing {len(cdn_images)} images...')
    manifest = {}
    downloaded = 0
    converted = 0
    skipped = 0

    for url, data in sorted(cdn_images.items()):
        ext = get_extension(url)
        url_hash = short_hash(url)

        # Generate descriptive filename
        path_parts = urlparse(url).path.split('/')
        filename_base = os.path.splitext(path_parts[-1])[0] if path_parts else url_hash
        filename_base = slugify(filename_base) or url_hash

        # Deduplicate: skip size variants of same image (keep largest)
        # e.g. image-300x200.jpg, image-768x512.jpg, image-1024x683.jpg, image.jpg
        # We want the base image, not all variants
        base_name = re.sub(r'-\d+x\d+$', '', filename_base)

        raw_path = os.path.join(images_dir, f'{filename_base}{ext}')
        webp_path = os.path.join(images_dir, f'{filename_base}.webp')

        # Skip if we already have this webp
        if os.path.exists(webp_path):
            manifest[url] = f'/assets/images/{filename_base}.webp'
            skipped += 1
            continue

        # Download
        if download_file(url, raw_path):
            downloaded += 1

            # Classify and convert
            img_type, quality, resize = classify_image(url, data['pages'][0] if data['pages'] else '/')

            if ext in ('.svg',):
                # Keep SVGs as-is
                manifest[url] = f'/assets/images/{filename_base}{ext}'
                print(f'  ✓ {filename_base}{ext} (SVG, kept as-is)')
                continue

            if convert_to_webp(raw_path, webp_path, quality, resize):
                # Get sizes
                raw_size = os.path.getsize(raw_path)
                webp_size = os.path.getsize(webp_path)
                savings = ((raw_size - webp_size) / raw_size * 100) if raw_size > 0 else 0

                manifest[url] = f'/assets/images/{filename_base}.webp'
                converted += 1

                # Remove raw file to save space
                os.remove(raw_path)

                if savings > 0:
                    print(f'  ✓ {filename_base}.webp [{img_type}] ({raw_size//1024}KB → {webp_size//1024}KB, -{savings:.0f}%)')
                else:
                    print(f'  ✓ {filename_base}.webp [{img_type}] ({webp_size//1024}KB)')
            else:
                # cwebp failed, keep original
                manifest[url] = f'/assets/images/{filename_base}{ext}'
                print(f'  ! {filename_base}{ext} (conversion failed, kept original)')
        else:
            print(f'  ✗ {filename_base} — download failed')

    # Download fonts
    print(f'\n[Phase 2] Processing fonts...')
    # Get font URLs from the brief's site data or crawl the homepage
    try:
        resp = requests.get(f'https://{brief["site"]["domain"]}/', timeout=15)
        font_urls = re.findall(r'https?://[^"\'>\s]+\.woff2', resp.text)
        font_urls = list(set(font_urls))
    except Exception:
        font_urls = []

    for font_url in font_urls:
        filename = os.path.basename(urlparse(font_url).path)
        font_path = os.path.join(fonts_dir, filename)
        if not os.path.exists(font_path):
            if download_file(font_url, font_path):
                size = os.path.getsize(font_path)
                manifest[font_url] = f'/assets/fonts/{filename}'
                print(f'  ✓ {filename} ({size//1024}KB)')
            else:
                print(f'  ✗ {filename} — download failed')
        else:
            manifest[font_url] = f'/assets/fonts/{filename}'
            print(f'  ✓ {filename} (already exists)')

    # Write manifest
    manifest_path = os.path.join(output_dir, 'asset-manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    # Summary
    total_webp_size = sum(
        os.path.getsize(os.path.join(images_dir, f))
        for f in os.listdir(images_dir)
        if f.endswith('.webp')
    )

    print(f'\n{"="*50}')
    print(f'  ASSET PIPELINE COMPLETE')
    print(f'{"="*50}')
    print(f'Images downloaded: {downloaded}')
    print(f'Images converted to WebP: {converted}')
    print(f'Images skipped (already exist): {skipped}')
    print(f'Fonts downloaded: {len(font_urls)}')
    print(f'Total WebP size: {total_webp_size//1024}KB ({total_webp_size//1024//1024}MB)')
    print(f'Manifest entries: {len(manifest)}')
    print(f'\nManifest: {manifest_path}')
    print(f'Assets: {assets_dir}/')

    return manifest


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 assets.py <content-brief.json>')
        sys.exit(1)

    run(sys.argv[1])
