#!/usr/bin/env python3
"""
Chowdown Site Crawler — Module 1
Crawls a SpotHopper/WordPress restaurant site and outputs:
  - page-tree.json: complete page inventory with types and status
  - All discovered assets (images, videos, fonts) cataloged

Strategy:
  1. Check /wp-sitemap.xml first (all SpotHopper sites are WordPress)
  2. If found, parse sub-sitemaps — wp-sitemap-posts-page-1.xml is the real pages
  3. Skip blog posts (wp-sitemap-posts-post-1.xml), taxonomy, and author sitemaps
  4. Fall back to /sitemap.xml if no WP sitemap
  5. Crawl homepage nav links as secondary source
  6. Cross-reference sitemap vs crawl — flag discrepancies
  7. Output merged, deduplicated page-tree.json

Usage:
  python3 crawl.py https://www.westfield-collective.com

Output written to: ./output/{domain}/page-tree.json
"""

import sys
import os
import json
import re
import warnings
from urllib.parse import urlparse, urljoin, urldefrag

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Suppress XML-as-HTML warnings from BeautifulSoup
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Page type detection based on URL patterns
PAGE_TYPE_PATTERNS = [
    (r'^/$', 'home'),
    (r'^/food-beverage/?$', 'food-beverage'),
    (r'^/food_and_beverage/?$', 'food-beverage'),
    (r'^/events/?$', 'events'),
    (r'^/sand-sports/?$', 'sand-sports'),
    (r'^/private-parties/?$', 'private-parties'),
    (r'^/about/?$', 'about'),
    (r'^/about/be-an-insider/?$', 'be-an-insider'),
    (r'^/about/igloo-rentals/?$', 'igloo-rentals'),
    (r'^/become-a-vendor/?$', 'become-a-vendor'),
    (r'^/clubs/?$', 'clubs'),
    (r'^/news/?$', 'news'),
    (r'^/leagues/?$', 'leagues'),
    (r'^/volleyball-leagues/?$', 'volleyball-leagues'),
    (r'^/golf-simulator/?$', 'golf-simulator'),
    (r'^/reserve/?$', 'reserve'),
    (r'^/party/?$', 'party'),
    (r'^/catering/?$', 'catering'),
    (r'^/drinks/?$', 'drinks'),
    (r'^/specials/?$', 'specials'),
    (r'^/gift-cards/?$', 'gift-cards'),
    (r'^/menu/?$', 'menu'),
    (r'^/activities/[^/]+/?$', 'activity'),
    (r'^/vendor/[^/]+/?$', 'vendor'),
    (r'^/food-beverage/[^/]+/?$', 'vendor'),
    (r'^/food_and_beverage/[^/]+/?$', 'vendor'),
    (r'^/sport/[^/]+/?$', 'sport'),
]

# URLs to always skip — WordPress internals, feeds, archives
SKIP_PATTERNS = [
    r'/wp-json/', r'/wp-includes/', r'/wp-content/', r'/wp-admin/',
    r'/feed/?$', r'/comments/feed', r'/xmlrpc', r'\?', r'#',
    r'/wp-sitemap', r'/oembed', r'/trackback',
    r'\.(pdf|jpg|jpeg|png|gif|svg|mp4|mp3|css|js|woff|woff2|zip)$',
    r'/author/', r'/page/\d+',                   # author archives, pagination
    r'^/blog/[^/]+/?$',                           # blog category pages (not real site pages)
    r'^/blog/[^/]+/page/',                        # paginated blog categories
]

# Sub-sitemaps to skip — these are NOT real site pages
WP_SITEMAP_SKIP = [
    'wp-sitemap-posts-post',      # blog posts
    'wp-sitemap-taxonomies',       # category/tag archives
    'wp-sitemap-users',            # author archives
]

ASSET_PATTERNS = {
    'images': re.compile(r'https?://[^"\'>\s]+\.(?:jpg|jpeg|png|webp|gif)', re.I),
    'videos': re.compile(r'https?://[^"\'>\s]+\.(?:mp4|webm)', re.I),
    'fonts': re.compile(r'https?://[^"\'>\s]+\.(?:woff2?|ttf|otf)', re.I),
}


def detect_page_type(path):
    """Detect page type from URL path."""
    for pattern, ptype in PAGE_TYPE_PATTERNS:
        if re.match(pattern, path):
            return ptype
    return 'unknown'


def should_skip(path):
    """Check if URL path should be skipped."""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, path, re.I):
            return True
    return False


def normalize_path(path):
    """Normalize a URL path: ensure trailing slash."""
    path = path.rstrip('/')
    if path == '':
        path = '/'
    else:
        path = path + '/'
    return path


def fetch_wp_sitemap(root_url, domain):
    """
    Fetch WordPress sitemap hierarchy.
    Primary source: /wp-sitemap.xml → sub-sitemaps → page URLs.
    Only includes wp-sitemap-posts-page (real pages), skips posts/taxonomy/users.
    Returns (pages_set, found_bool).
    """
    pages = set()
    wp_sitemap_url = f'{root_url}/wp-sitemap.xml'

    print(f'  Checking {wp_sitemap_url}...')
    try:
        resp = requests.get(wp_sitemap_url, timeout=10)
        if resp.status_code != 200:
            print(f'  Not found (HTTP {resp.status_code})')
            return pages, False

        soup = BeautifulSoup(resp.text, 'html.parser')
        sub_sitemaps = []

        for sitemap_tag in soup.find_all('sitemap'):
            loc = sitemap_tag.find('loc')
            if loc:
                sub_url = loc.text.strip()
                sub_sitemaps.append(sub_url)

        if not sub_sitemaps:
            print(f'  wp-sitemap.xml found but contains no sub-sitemaps')
            return pages, False

        print(f'  Found wp-sitemap.xml with {len(sub_sitemaps)} sub-sitemaps:')

        for sub_url in sub_sitemaps:
            # Determine if we should process or skip this sub-sitemap
            skip = False
            for skip_pattern in WP_SITEMAP_SKIP:
                if skip_pattern in sub_url:
                    skip = True
                    break

            basename = sub_url.split('/')[-1]
            if skip:
                print(f'    SKIP: {basename} (blog posts/taxonomy/authors)')
                continue

            print(f'    FETCH: {basename}')
            try:
                sub_resp = requests.get(sub_url, timeout=10)
                if sub_resp.status_code == 200:
                    sub_soup = BeautifulSoup(sub_resp.text, 'html.parser')
                    count = 0
                    for url_tag in sub_soup.find_all('url'):
                        loc_tag = url_tag.find('loc')
                        if loc_tag:
                            parsed = urlparse(loc_tag.text.strip())
                            if parsed.netloc == domain:
                                path = normalize_path(parsed.path)
                                if not should_skip(path):
                                    pages.add(path)
                                    count += 1
                    print(f'           → {count} pages extracted')
            except Exception as e:
                print(f'           → ERROR: {e}')

        return pages, True

    except Exception as e:
        print(f'  ERROR: {e}')
        return pages, False


def fetch_generic_sitemap(root_url, domain):
    """Fallback: try /sitemap.xml (non-WP or custom sitemap)."""
    pages = set()
    sitemap_url = f'{root_url}/sitemap.xml'

    print(f'  Checking {sitemap_url}...')
    try:
        resp = requests.get(sitemap_url, timeout=10)
        if resp.status_code != 200:
            print(f'  Not found')
            return pages, False

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Check for sitemap index first
        index_sitemaps = soup.find_all('sitemap')
        if index_sitemaps:
            for sitemap_tag in index_sitemaps:
                loc = sitemap_tag.find('loc')
                if loc:
                    sub_url = loc.text.strip()
                    # Apply same skip logic
                    skip = False
                    for skip_pattern in WP_SITEMAP_SKIP:
                        if skip_pattern in sub_url:
                            skip = True
                            break
                    if skip:
                        continue
                    try:
                        sub_resp = requests.get(sub_url, timeout=10)
                        if sub_resp.status_code == 200:
                            sub_soup = BeautifulSoup(sub_resp.text, 'html.parser')
                            for url_tag in sub_soup.find_all('url'):
                                loc_tag = url_tag.find('loc')
                                if loc_tag:
                                    parsed = urlparse(loc_tag.text.strip())
                                    if parsed.netloc == domain:
                                        path = normalize_path(parsed.path)
                                        if not should_skip(path):
                                            pages.add(path)
                    except Exception:
                        pass
        else:
            # Direct URL entries
            for url_tag in soup.find_all('url'):
                loc = url_tag.find('loc')
                if loc:
                    parsed = urlparse(loc.text.strip())
                    if parsed.netloc == domain:
                        path = normalize_path(parsed.path)
                        if not should_skip(path):
                            pages.add(path)

        if pages:
            print(f'  Found {len(pages)} pages in sitemap.xml')
        return pages, bool(pages)

    except Exception:
        print(f'  Not found')
        return pages, False


def extract_internal_links(soup, base_url, domain):
    """Extract all internal links from a page."""
    links = set()
    for tag in soup.find_all('a', href=True):
        href = tag['href'].strip()
        if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue
        full_url = urljoin(base_url, href)
        full_url, _ = urldefrag(full_url)
        parsed = urlparse(full_url)
        if parsed.netloc and parsed.netloc != domain:
            continue
        if should_skip(parsed.path):
            continue
        path = normalize_path(parsed.path)
        links.add(path)
    return links


def extract_nav_links(soup, base_url, domain):
    """Extract links specifically from navigation elements."""
    links = set()
    nav_elements = soup.find_all(['nav', 'header'])
    for nav in nav_elements:
        for tag in nav.find_all('a', href=True):
            href = tag['href'].strip()
            if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            full_url = urljoin(base_url, href)
            full_url, _ = urldefrag(full_url)
            parsed = urlparse(full_url)
            if parsed.netloc and parsed.netloc != domain:
                continue
            if should_skip(parsed.path):
                continue
            path = normalize_path(parsed.path)
            links.add(path)
    return links


def extract_assets(html):
    """Extract all asset URLs from raw HTML."""
    assets = {'images': set(), 'videos': set(), 'fonts': set()}
    for asset_type, pattern in ASSET_PATTERNS.items():
        for match in pattern.findall(html):
            assets[asset_type].add(match)
    return assets


def extract_external_links(soup, domain):
    """Extract all external links (ordering, social, etc.)."""
    external = []
    for tag in soup.find_all('a', href=True):
        href = tag['href'].strip()
        if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue
        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc != domain and parsed.scheme in ('http', 'https'):
            text = tag.get_text(strip=True) or ''
            external.append({'url': href, 'text': text[:100]})
    return external


def crawl(root_url):
    """Crawl the site starting from root URL."""
    parsed_root = urlparse(root_url)
    domain = parsed_root.netloc
    scheme = parsed_root.scheme
    base_url = f'{scheme}://{domain}'

    print(f'\n{"="*50}')
    print(f'  CHOWDOWN SITE CRAWLER — Module 1')
    print(f'{"="*50}')
    print(f'Target: {root_url}')
    print(f'Domain: {domain}\n')

    # ── Phase 1: WordPress sitemap (primary source) ──
    print('[Phase 1] WordPress sitemap discovery (primary source)...')
    wp_pages, wp_found = fetch_wp_sitemap(root_url, domain)

    # ── Phase 1b: Generic sitemap (fallback) ──
    generic_pages = set()
    if not wp_found:
        print('\n[Phase 1b] Fallback: generic sitemap.xml...')
        generic_pages, _ = fetch_generic_sitemap(root_url, domain)

    sitemap_pages = wp_pages | generic_pages
    print(f'\n  Total sitemap pages: {len(sitemap_pages)}')

    # ── Phase 2: Crawl homepage for nav links ──
    print(f'\n[Phase 2] Crawling homepage for navigation links...')
    crawled_links = set()
    crawled_links.add('/')

    try:
        resp = requests.get(root_url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        nav_links = extract_nav_links(soup, root_url, domain)
        body_links = extract_internal_links(soup, root_url, domain)
        crawled_links.update(nav_links)
        crawled_links.update(body_links)
        print(f'  Nav links: {len(nav_links)}')
        print(f'  Body links: {len(body_links)}')
        print(f'  Total from crawl: {len(crawled_links)}')
    except Exception as e:
        print(f'  ERROR crawling homepage: {e}')
        return None

    # ── Phase 3: Cross-reference sitemap vs crawl ──
    print(f'\n[Phase 3] Cross-referencing sitemap vs crawl...')

    in_sitemap_only = sitemap_pages - crawled_links
    in_crawl_only = crawled_links - sitemap_pages
    in_both = sitemap_pages & crawled_links

    print(f'  In both: {len(in_both)}')
    if in_sitemap_only:
        print(f'  In sitemap only ({len(in_sitemap_only)}):')
        for p in sorted(in_sitemap_only):
            print(f'    + {p}')
    if in_crawl_only:
        print(f'  In crawl only ({len(in_crawl_only)}):')
        for p in sorted(in_crawl_only):
            ptype = detect_page_type(p)
            print(f'    + {p} [{ptype}]')

    # Merge: sitemap is primary, crawl fills gaps
    all_paths = sitemap_pages | crawled_links

    # ── Phase 4: Visit each page, extract data ──
    print(f'\n[Phase 4] Visiting {len(all_paths)} pages...')
    visited = set()
    pages = []
    all_assets = {'images': set(), 'videos': set(), 'fonts': set()}
    all_external = []

    to_visit = sorted(all_paths)

    while to_visit:
        path = to_visit.pop(0)
        if path in visited:
            continue
        visited.add(path)

        url = f'{base_url}{path}'
        try:
            resp = requests.get(url, timeout=15, allow_redirects=True)
            status = resp.status_code

            if status == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')

                title_tag = soup.find('title')
                title = title_tag.get_text(strip=True) if title_tag else ''

                meta_desc = soup.find('meta', attrs={'name': 'description'})
                description = meta_desc['content'] if meta_desc and meta_desc.get('content') else ''

                page_type = detect_page_type(path)

                # Discover additional internal links (may find pages missed by sitemap + nav)
                new_links = extract_internal_links(soup, url, domain)
                for link in new_links:
                    if link not in visited and link not in to_visit:
                        to_visit.append(link)
                        to_visit.sort()

                page_assets = extract_assets(resp.text)
                for atype in all_assets:
                    all_assets[atype].update(page_assets[atype])

                externals = extract_external_links(soup, domain)
                all_external.extend(externals)

                # Track which source discovered this page
                source = []
                if path in sitemap_pages:
                    source.append('sitemap')
                if path in crawled_links:
                    source.append('crawl')
                if not source:
                    source.append('discovered')  # found during recursive crawl

                page_data = {
                    'url': path,
                    'type': page_type,
                    'status': status,
                    'title': title,
                    'description': description,
                    'source': source,
                }

                pages.append(page_data)
                src_label = '+'.join(source)
                print(f'  ✓ {path} [{page_type}] ({src_label}) — {title[:50]}')
            else:
                pages.append({
                    'url': path,
                    'type': detect_page_type(path),
                    'status': status,
                    'title': '',
                    'description': '',
                    'source': ['sitemap' if path in sitemap_pages else 'crawl'],
                })
                print(f'  ✗ {path} — HTTP {status}')

        except Exception as e:
            pages.append({
                'url': path,
                'type': detect_page_type(path),
                'status': 0,
                'title': f'ERROR: {str(e)[:80]}',
                'description': '',
                'source': ['sitemap' if path in sitemap_pages else 'crawl'],
            })
            print(f'  ✗ {path} — ERROR: {e}')

    # Deduplicate external links
    seen_urls = set()
    unique_external = []
    for ext in all_external:
        if ext['url'] not in seen_urls:
            seen_urls.add(ext['url'])
            unique_external.append(ext)

    pages.sort(key=lambda p: p['url'])

    # ── Build output ──
    ok_pages = [p for p in pages if p['status'] == 200]
    err_pages = [p for p in pages if p['status'] != 200]

    output = {
        'root': root_url,
        'domain': domain,
        'platform': 'wordpress/spothopper' if wp_found else 'unknown',
        'sitemap_source': 'wp-sitemap.xml' if wp_found else ('sitemap.xml' if generic_pages else 'none'),
        'discovery': {
            'sitemap_pages': len(sitemap_pages),
            'crawl_pages': len(crawled_links),
            'in_both': len(in_both),
            'sitemap_only': sorted(in_sitemap_only),
            'crawl_only': sorted(in_crawl_only),
            'total_merged': len(all_paths),
            'total_with_discovered': len(ok_pages),
        },
        'total_pages': len(ok_pages),
        'pages': pages,
        'assets': {
            'images': sorted(all_assets['images']),
            'videos': sorted(all_assets['videos']),
            'fonts': sorted(all_assets['fonts']),
        },
        'external_links': unique_external,
    }

    # Write output
    output_dir = os.path.join('output', domain.replace('www.', ''))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'page-tree.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    # ── Summary ──
    print(f'\n{"="*50}')
    print(f'  CRAWL COMPLETE')
    print(f'{"="*50}')
    print(f'Platform: {"WordPress/SpotHopper" if wp_found else "Unknown"}')
    print(f'Sitemap source: {output["sitemap_source"]}')
    print(f'')
    print(f'Pages found: {len(ok_pages)}')
    if err_pages:
        print(f'Errors: {len(err_pages)}')
        for p in err_pages:
            print(f'  ✗ {p["url"]} — HTTP {p["status"]}')
    print(f'')
    print(f'Assets:')
    print(f'  Images: {len(all_assets["images"])}')
    print(f'  Videos: {len(all_assets["videos"])}')
    print(f'  Fonts: {len(all_assets["fonts"])}')
    print(f'External links: {len(unique_external)}')
    print(f'')

    # Page type summary
    types = {}
    for p in ok_pages:
        types[p['type']] = types.get(p['type'], 0) + 1
    print(f'Page types:')
    for ptype, count in sorted(types.items()):
        print(f'  {ptype}: {count}')

    # Discovery cross-reference
    print(f'\nDiscovery cross-reference:')
    print(f'  Sitemap: {len(sitemap_pages)} pages')
    print(f'  Crawl: {len(crawled_links)} pages')
    print(f'  Overlap: {len(in_both)}')
    if in_sitemap_only:
        print(f'  Sitemap-only (added): {len(in_sitemap_only)}')
    if in_crawl_only:
        print(f'  Crawl-only (added): {len(in_crawl_only)}')
    discovered = len(ok_pages) - len(all_paths)
    if discovered > 0:
        print(f'  Discovered during deep crawl: {discovered}')

    print(f'\nOutput: {output_path}')
    return output


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 crawl.py <URL>')
        print('Example: python3 crawl.py https://www.westfield-collective.com')
        sys.exit(1)

    root_url = sys.argv[1].rstrip('/')
    crawl(root_url)
