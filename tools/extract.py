#!/usr/bin/env python3
"""
Chowdown Content Extractor — Module 2
Extracts structured content from every included page in page-tree.json.

Usage:
  python3 extract.py output/westfield-collective.com/page-tree.json

Output: output/{domain}/content-brief.json
"""

import sys
import os
import json
import re
import warnings
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning, NavigableString

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# SpotHopper CDN patterns
CDN_PATTERNS = [
    'static01.sh-websites.com',
    'static.spotapps.co',
    'res.cloudinary.com',
]


def is_cdn_url(url):
    return any(cdn in url for cdn in CDN_PATTERNS)


def extract_headings(soup):
    """Extract all headings with hierarchy."""
    headings = []
    content_area = find_content_area(soup)
    if not content_area:
        content_area = soup
    for tag in content_area.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text = tag.get_text(strip=True)
        if text:
            headings.append({
                'level': tag.name,
                'text': text
            })
    return headings


def find_content_area(soup):
    """Find the main content area, skipping nav and footer."""
    # Try common WordPress content containers
    for selector in ['main', '.entry-content', '.wp-block-post-content', 'article']:
        area = soup.find(selector)
        if area:
            return area
    return None


def extract_body_copy(soup):
    """Extract all paragraph text blocks from the content area."""
    blocks = []
    content_area = find_content_area(soup)
    if not content_area:
        content_area = soup.find('body') or soup

    # Get paragraphs, but skip nav/header/footer
    skip_parents = {'nav', 'header', 'footer', 'script', 'style', 'noscript'}

    for p in content_area.find_all(['p', 'li']):
        # Skip if inside nav/header/footer
        parent_tags = {parent.name for parent in p.parents if parent.name}
        if parent_tags & skip_parents:
            continue

        text = p.get_text(strip=True)
        if text and len(text) > 5:  # Skip tiny fragments
            blocks.append(text)

    return blocks


def extract_external_links(soup, domain):
    """Extract all external links with anchor text."""
    links = []
    seen = set()
    for tag in soup.find_all('a', href=True):
        href = tag['href'].strip()
        if not href or href.startswith(('javascript:', '#')):
            continue
        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc != domain and parsed.scheme in ('http', 'https'):
            if href not in seen:
                seen.add(href)
                text = tag.get_text(strip=True) or ''
                links.append({'text': text, 'url': href})
    return links


def extract_mailto_tel(soup):
    """Extract email and phone from mailto: and tel: links."""
    emails = set()
    phones = set()
    for tag in soup.find_all('a', href=True):
        href = tag['href'].strip()
        if href.startswith('mailto:'):
            emails.add(href.replace('mailto:', '').split('?')[0])
        elif href.startswith('tel:'):
            phones.add(tag.get_text(strip=True))
    return list(emails), list(phones)


def extract_images(soup, page_url):
    """Extract all image URLs, focusing on CDN images."""
    images = []
    seen = set()

    # From <img> tags
    for img in soup.find_all('img', src=True):
        src = urljoin(page_url, img['src'])
        if src not in seen:
            seen.add(src)
            alt = img.get('alt', '')
            images.append({'src': src, 'alt': alt, 'cdn': is_cdn_url(src)})

        # Also check srcset
        srcset = img.get('srcset', '')
        if srcset:
            for entry in srcset.split(','):
                parts = entry.strip().split()
                if parts:
                    url = urljoin(page_url, parts[0])
                    if url not in seen:
                        seen.add(url)
                        images.append({'src': url, 'alt': alt, 'cdn': is_cdn_url(url)})

    # From inline style background-images
    for tag in soup.find_all(style=True):
        style = tag.get('style', '')
        bg_urls = re.findall(r'url\(["\']?(https?://[^"\')\s]+)["\']?\)', style)
        for url in bg_urls:
            if url not in seen:
                seen.add(url)
                images.append({'src': url, 'alt': '', 'cdn': is_cdn_url(url)})

    return images


def extract_social_links(soup):
    """Extract social media URLs."""
    social = {}
    social_domains = {
        'facebook.com': 'facebook',
        'instagram.com': 'instagram',
        'tiktok.com': 'tiktok',
        'x.com': 'twitter',
        'twitter.com': 'twitter',
        'youtube.com': 'youtube',
        'yelp.com': 'yelp',
        'google.com/search': 'google_reviews',
        'google.com/maps': 'google_maps',
    }
    for tag in soup.find_all('a', href=True):
        href = tag['href'].strip()
        for domain_key, name in social_domains.items():
            if domain_key in href and name not in social:
                social[name] = href
    return social


def extract_hours(soup):
    """Try to extract hours from the page content."""
    hours_blocks = []
    content_area = find_content_area(soup)
    if not content_area:
        content_area = soup

    # Look for common hours patterns
    text = content_area.get_text()
    # Match patterns like "Mon-Fri 11am - 9pm" or "Monday -- Thursday 11am -- 10pm"
    hour_pattern = re.compile(
        r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'
        r'[^:]*?(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))',
        re.I
    )

    # Also look for specific hour sections
    for tag in content_area.find_all(['p', 'div', 'span', 'h4', 'h3']):
        tag_text = tag.get_text(strip=True)
        if any(kw in tag_text.lower() for kw in ['hour', 'am', 'pm', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
                                                    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                                                    'everyday', 'daily']):
            if len(tag_text) < 200:  # Skip large blocks
                hours_blocks.append(tag_text)

    return hours_blocks if hours_blocks else None


def extract_cta_buttons(soup):
    """Extract CTA buttons — links styled as buttons."""
    buttons = []
    content_area = find_content_area(soup)
    if not content_area:
        content_area = soup

    # SpotHopper uses custom button blocks
    for tag in content_area.find_all('a', class_=True):
        classes = ' '.join(tag.get('class', []))
        if any(kw in classes.lower() for kw in ['btn', 'button', 'cta', 'wp-block-button', 'custom-temp-btn']):
            text = tag.get_text(strip=True)
            href = tag.get('href', '')
            if text and href:
                buttons.append({'text': text, 'url': href})

    # Also check <button> inside <a> or standalone
    for tag in content_area.find_all(['a'], href=True):
        text = tag.get_text(strip=True)
        href = tag.get('href', '')
        classes = ' '.join(tag.get('class', []))
        if 'btn' in classes or 'button' in classes or 'custom-temp-btn' in classes:
            if text and href and {'text': text, 'url': href} not in buttons:
                buttons.append({'text': text, 'url': href})

    return buttons


def extract_address(soup):
    """Try to extract address from the page."""
    # Look for address tag
    addr_tag = soup.find('address')
    if addr_tag:
        return addr_tag.get_text(strip=True)

    # Look for common address patterns in text
    text = soup.get_text()
    # Match street address patterns
    addr_match = re.search(r'\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Lane|Ln|Road|Rd|Drive|Dr|Boulevard|Blvd)[^,]*,\s*[A-Z][a-zA-Z\s]+,?\s*[A-Z]{2}\s+\d{5}', text)
    if addr_match:
        return addr_match.group(0).strip()

    return None


def extract_page(url, domain):
    """Extract all content from a single page."""
    print(f'  Extracting: {url}')

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            print(f'    ERROR: HTTP {resp.status_code}')
            return {'error': f'HTTP {resp.status_code}'}

        soup = BeautifulSoup(resp.text, 'html.parser')

        headings = extract_headings(soup)
        body_copy = extract_body_copy(soup)
        external_links = extract_external_links(soup, domain)
        emails, phones = extract_mailto_tel(soup)
        images = extract_images(soup, url)
        social = extract_social_links(soup)
        hours = extract_hours(soup)
        ctas = extract_cta_buttons(soup)
        address = extract_address(soup)

        # Calculate content depth
        total_text = ' '.join(body_copy)
        word_count = len(total_text.split())

        result = {
            'headings': headings if headings else None,
            'body_copy': body_copy if body_copy else None,
            'word_count': word_count,
            'external_links': external_links if external_links else None,
            'emails': emails if emails else None,
            'phones': phones if phones else None,
            'images': images if images else None,
            'image_count': len(images),
            'social': social if social else None,
            'hours': hours,
            'cta_buttons': ctas if ctas else None,
            'address': address,
        }

        # Flag thin content
        if word_count < 50:
            result['thin_content_flag'] = True
            print(f'    ⚠ THIN CONTENT: {word_count} words')
        else:
            print(f'    ✓ {word_count} words, {len(headings)} headings, {len(images)} images')

        return result

    except Exception as e:
        print(f'    ERROR: {e}')
        return {'error': str(e)}


def run(page_tree_path):
    """Run content extraction on all included pages."""
    with open(page_tree_path) as f:
        tree = json.load(f)

    domain = tree['domain']
    root = tree['root']

    print(f'\n{"="*50}')
    print(f'  CHOWDOWN CONTENT EXTRACTOR — Module 2')
    print(f'{"="*50}')
    print(f'Site: {root}')
    print(f'Domain: {domain}\n')

    # Filter to included pages only
    included = [p for p in tree['pages'] if p.get('human_review') == 'include']
    excluded = [p for p in tree['pages'] if p.get('human_review') == 'exclude']

    print(f'Pages to extract: {len(included)}')
    print(f'Pages excluded: {len(excluded)}\n')

    # Extract site-wide data from homepage first
    print('[Phase 1] Extracting site-wide data from homepage...')
    homepage_url = f'{root}/'
    try:
        resp = requests.get(homepage_url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        site_emails, site_phones = extract_mailto_tel(soup)
        site_social = extract_social_links(soup)
        site_address = extract_address(soup)
        site_hours = extract_hours(soup)
    except Exception as e:
        print(f'  ERROR on homepage: {e}')
        site_emails = site_phones = site_social = site_address = site_hours = None

    site_data = {
        'name': 'Westfield Collective',
        'domain': domain,
        'address': site_address,
        'emails': site_emails if site_emails else None,
        'phones': site_phones if site_phones else None,
        'social': site_social if site_social else None,
        'hours': site_hours,
    }

    print(f'  Address: {site_address}')
    print(f'  Emails: {site_emails}')
    print(f'  Phones: {site_phones}')
    print(f'  Social: {list(site_social.keys()) if site_social else "none"}')
    print(f'  Hours blocks: {len(site_hours) if site_hours else 0}')

    # Extract each page
    print(f'\n[Phase 2] Extracting content from {len(included)} pages...')
    pages_data = {}
    thin_pages = []

    for page in included:
        path = page['url']
        url = f'{root}{path}'
        page_content = extract_page(url, domain)
        pages_data[path] = page_content

        if page_content.get('thin_content_flag'):
            thin_pages.append(path)

    # Build output
    output = {
        'site': site_data,
        'pages': pages_data,
        'redirects': [
            {'from': p['url'], 'to': p.get('redirect_to', '/')}
            for p in excluded
        ],
        'extraction_summary': {
            'total_extracted': len(pages_data),
            'thin_content_flags': thin_pages,
            'thin_content_count': len(thin_pages),
        }
    }

    # Write output
    output_dir = os.path.dirname(page_tree_path)
    output_path = os.path.join(output_dir, 'content-brief.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    print(f'\n{"="*50}')
    print(f'  EXTRACTION COMPLETE')
    print(f'{"="*50}')
    print(f'Pages extracted: {len(pages_data)}')

    if thin_pages:
        print(f'\n⚠ THIN CONTENT FLAGS ({len(thin_pages)}):')
        for p in thin_pages:
            wc = pages_data[p].get('word_count', 0)
            print(f'  {p} — {wc} words')
        print(f'\nThese pages may be placeholders the sitemap review missed.')
        print(f'Review before proceeding to Module 3.')

    total_images = sum(p.get('image_count', 0) for p in pages_data.values())
    total_words = sum(p.get('word_count', 0) for p in pages_data.values())
    print(f'\nTotal words across all pages: {total_words}')
    print(f'Total images across all pages: {total_images}')
    print(f'Redirects to generate: {len(output["redirects"])}')
    print(f'\nOutput: {output_path}')

    return output


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 extract.py <page-tree.json>')
        print('Example: python3 extract.py output/westfield-collective.com/page-tree.json')
        sys.exit(1)

    run(sys.argv[1])
