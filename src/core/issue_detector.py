"""SEO issue detection and reporting"""
import re
import threading
from fnmatch import fnmatch
from urllib.parse import urlparse
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta


def _get_json_ld_types(json_ld):
    """Extract all @type values from JSON-LD nodes as a lowercase set."""
    types = set()
    for node in (json_ld or []):
        if not isinstance(node, dict):
            continue
        raw = node.get('@type', '')
        for t in ([raw] if isinstance(raw, str) else (raw or [])):
            types.add(str(t).lower())
    return types


def classify_page(result):
    """
    Full multi-signal page type classifier.

    Returns a dict with:
      - page_type: 'article' | 'product' | 'collection' | 'organization' |
                   'event' | 'faq' | 'profile' | 'structural' | 'unknown'
      - scores: {type: score} for all types evaluated
      - signals: {type: [signal strings]} detected per type
      - expected_schema: schema type(s) expected for this page type
      - needs_author: bool
      - needs_schema: bool
      - is_content: bool (True for article type)
      - is_structural: bool
    """
    url = (result.get('url') or '').lower()
    word_count = result.get('word_count') or 0
    json_ld = result.get('json_ld') or []
    og_tags = result.get('og_tags') or {}
    meta_tags = result.get('meta_tags') or {}
    ld_types = _get_json_ld_types(json_ld)

    scores = {t: 0 for t in ['article', 'product', 'collection', 'organization', 'event', 'faq', 'profile', 'structural']}
    signals = {t: [] for t in scores}

    def add(page_type, points, signal):
        scores[page_type] += points
        signals[page_type].append(signal)

    # ── STRUCTURAL ────────────────────────────────────────────────────────────
    if re.match(r'^https?://[^/]+(/?$|\?)', url):
        add('structural', 5, 'homepage URL')
    if re.search(r'/(login|logout|register|signup|sign-in|checkout|cart|basket|404|403|500|sitemap)(s)?(\/|$|\?)', url):
        add('structural', 5, 'utility URL pattern')
    if re.search(r'/(search|results)(\/|$|\?)', url) or '?s=' in url or '?q=' in url:
        add('structural', 5, 'search URL')
    if re.search(r'/feed(\/|$|\?)', url):
        add('structural', 5, 'feed URL')
    # Tag and category pages are always structural
    if re.search(r'/(tag|tags|category|categories)(\/|$|\?)', url):
        add('structural', 5, 'tag/category URL')

    # ── ARTICLE ───────────────────────────────────────────────────────────────
    article_ld = {'article', 'blogposting', 'newsarticle', 'techarticle', 'report', 'scholarlyarticle'}
    if ld_types & article_ld:
        add('article', 5, f'JSON-LD {", ".join(ld_types & article_ld)}')
    # og:type=article is +2 only — WordPress/Yoast sets it on ALL pages by default
    if og_tags.get('type', '').lower() == 'article':
        add('article', 2, 'og:type=article')
    # article:published_time is a strong signal — CMS only adds it to real articles
    if og_tags.get('published_time') or meta_tags.get('article:published_time'):
        add('article', 4, 'article:published_time')
    if og_tags.get('author') or meta_tags.get('article:author'):
        add('article', 3, 'article:author meta')
    if re.search(r'/(blog|article|post|news|guide|tutorial|review|story|insight|learn|knowledge)(s)?(\/|$|\?)', url):
        add('article', 4, 'content URL pattern')
    if re.search(r'/\d{4}/\d{2}/', url):
        add('article', 3, 'date-based URL')
    if word_count >= 600:
        add('article', 3, f'{word_count} words')
    elif word_count >= 300:
        add('article', 2, f'{word_count} words')

    # ── PRODUCT ───────────────────────────────────────────────────────────────
    if 'product' in ld_types:
        add('product', 5, 'JSON-LD Product')
    if og_tags.get('type', '').lower() in ('product', 'og:product'):
        add('product', 4, 'og:type=product')
    if og_tags.get('price:amount') or og_tags.get('price'):
        add('product', 4, 'og:price meta')
    if re.search(r'/(product|item|p|buy|pd)(s)?(\/|$|\?|/\w)', url):
        add('product', 4, 'product URL pattern')
    if re.search(r'/(shop|store)(\/[^/]+){1,2}$', url):
        add('product', 3, 'shop sub-page URL')
    if result.get('meta_tags', {}).get('product:price:amount'):
        add('product', 4, 'product:price meta')

    # ── COLLECTION ────────────────────────────────────────────────────────────
    collection_ld = {'collectionpage', 'itemlist', 'productcollection', 'offerscatalog'}
    if ld_types & collection_ld:
        add('collection', 5, f'JSON-LD {", ".join(ld_types & collection_ld)}')
    if re.search(r'/(category|collection|catalog|listing|department|tag|archive)(s)?(\/|$|\?)', url):
        add('collection', 4, 'collection URL pattern')
    if re.search(r'/(shop|store)(\/|$|\?)$', url):
        add('collection', 3, 'shop root URL')
    if re.search(r'/page/\d+', url) or re.search(r'[?&]page=\d+', url) or re.search(r'[?&]p=\d+', url):
        add('collection', 3, 'pagination URL')

    # ── ORGANIZATION ──────────────────────────────────────────────────────────
    org_ld = {'organization', 'localbusiness', 'corporation', 'nonprofit', 'restaurant', 'hotel', 'store'}
    if ld_types & org_ld:
        add('organization', 5, f'JSON-LD {", ".join(ld_types & org_ld)}')
    if re.search(r'/(about|about-us|our-story|contact|contact-us|privacy|terms|services|pricing)(\/|$|\?)', url):
        add('organization', 4, 'organization page URL')

    # ── EVENT ─────────────────────────────────────────────────────────────────
    if 'event' in ld_types:
        add('event', 5, 'JSON-LD Event')
    if og_tags.get('type', '').lower() == 'event':
        add('event', 4, 'og:type=event')
    if re.search(r'/(event|events|webinar|conference|meetup|workshop)(\/|$|\?)', url):
        add('event', 4, 'event URL pattern')

    # ── FAQ ───────────────────────────────────────────────────────────────────
    if 'faqpage' in ld_types:
        add('faq', 5, 'JSON-LD FAQPage')
    if re.search(r'/(faq|faqs|help|frequently-asked|questions)(\/|$|\?)', url):
        add('faq', 4, 'FAQ URL pattern')

    # ── PROFILE ───────────────────────────────────────────────────────────────
    if 'person' in ld_types or 'profilepage' in ld_types:
        add('profile', 5, 'JSON-LD Person/ProfilePage')
    if re.search(r'/(author|team|staff|member|people|person|bio|profile)(s)?(\/[^/]+)?(\/|$|\?)', url):
        add('profile', 4, 'profile URL pattern')

    # ── DETERMINE WINNER ──────────────────────────────────────────────────────
    # Structural overrides if score >= 5
    if scores['structural'] >= 5:
        page_type = 'structural'
    else:
        # Remove structural from competition for best type
        non_structural = {k: v for k, v in scores.items() if k != 'structural'}
        best_type = max(non_structural, key=lambda k: non_structural[k])
        best_score = non_structural[best_type]
        page_type = best_type if best_score >= 5 else 'unknown'

    # ── EXPECTED SCHEMA AND REQUIREMENTS PER TYPE ─────────────────────────────
    type_config = {
        'article':      {'schema': 'Article / BlogPosting',        'needs_author': True,  'needs_schema': True},
        'product':      {'schema': 'Product',                       'needs_author': False, 'needs_schema': True},
        'collection':   {'schema': 'CollectionPage / ItemList',     'needs_author': False, 'needs_schema': False},
        'organization': {'schema': 'Organization / LocalBusiness',  'needs_author': False, 'needs_schema': False},
        'event':        {'schema': 'Event',                         'needs_author': False, 'needs_schema': True},
        'faq':          {'schema': 'FAQPage',                       'needs_author': False, 'needs_schema': True},
        'profile':      {'schema': 'Person',                        'needs_author': False, 'needs_schema': False},
        'structural':   {'schema': None,                            'needs_author': False, 'needs_schema': False},
        'unknown':      {'schema': None,                            'needs_author': False, 'needs_schema': False},
    }
    cfg = type_config[page_type]

    return {
        'page_type': page_type,
        'scores': scores,
        'signals': signals[page_type] if page_type != 'unknown' else [],
        'all_signals': signals,
        'expected_schema': cfg['schema'],
        'needs_author': cfg['needs_author'],
        'needs_schema': cfg['needs_schema'],
        # backward compat
        'is_content': page_type == 'article',
        'is_structural': page_type == 'structural',
        'content_score': scores.get('article', 0),
    }


class IssueDetector:
    """Detects SEO and technical issues in crawled pages"""

    def __init__(self, exclusion_patterns=None):
        self.exclusion_patterns = exclusion_patterns or []
        self.detected_issues = []
        self.issues_lock = threading.Lock()

    def detect_issues(self, result):
        """Detect SEO issues for a crawled URL"""
        url = result.get('url', '')
        issues = []

        # Skip if URL matches exclusion patterns
        if self._should_exclude(url):
            return

        # Critical SEO Issues
        self._check_title_issues(result, issues)
        self._check_meta_description_issues(result, issues)
        self._check_heading_issues(result, issues)
        self._check_content_issues(result, issues)
        self._check_technical_issues(result, issues)
        self._check_mobile_issues(result, issues)
        self._check_accessibility_issues(result, issues)
        self._check_social_media_issues(result, issues)
        self._check_structured_data_issues(result, issues)
        self._check_performance_issues(result, issues)
        self._check_indexability_issues(result, issues)
        self._check_broken_image_issues(result, issues)
        self._check_content_freshness(result, issues)
        self._check_redirect_chain(result, issues)
        self._check_cookie_consent(result, issues)
        self._check_readability(result, issues)
        self._check_schema_completeness(result, issues)

        # Add all detected issues
        with self.issues_lock:
            self.detected_issues.extend(issues)

    def _check_title_issues(self, result, issues):
        """Check for title-related issues"""
        url = result.get('url', '')
        title = result.get('title', '')

        if not title:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'SEO',
                'issue': 'Missing Title Tag',
                'details': 'Page has no title tag'
            })
        elif len(title) > 60:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'SEO',
                'issue': 'Title Too Long',
                'details': f"Title is {len(title)} characters (recommended: ≤60)"
            })
        elif len(title) < 30:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'SEO',
                'issue': 'Title Too Short',
                'details': f"Title is {len(title)} characters (recommended: 30-60)"
            })

    def _check_meta_description_issues(self, result, issues):
        """Check for meta description issues"""
        url = result.get('url', '')
        meta_desc = result.get('meta_description', '')

        if not meta_desc:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'SEO',
                'issue': 'Missing Meta Description',
                'details': 'Page has no meta description'
            })
        elif len(meta_desc) > 160:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'SEO',
                'issue': 'Meta Description Too Long',
                'details': f"Description is {len(meta_desc)} characters (recommended: ≤160)"
            })
        elif len(meta_desc) < 120:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'SEO',
                'issue': 'Meta Description Too Short',
                'details': f"Description is {len(meta_desc)} characters (recommended: 120-160)"
            })

    def _check_heading_issues(self, result, issues):
        """Check for heading-related issues"""
        url = result.get('url', '')
        h1_list = result.get('h1_list', [result.get('h1')] if result.get('h1') else [])
        h2 = result.get('h2', [])
        h3 = result.get('h3', [])
        title = result.get('title', '').strip()

        # Missing H1
        if not h1_list:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'SEO',
                'issue': 'Missing H1 Tag',
                'details': 'Page has no H1 heading'
            })
        else:
            # Multiple H1s
            if len(h1_list) > 1:
                issues.append({
                    'url': url,
                    'type': 'error',
                    'category': 'SEO',
                    'issue': f'Multiple H1 Tags ({len(h1_list)})',
                    'details': f'Page has {len(h1_list)} H1 tags. Only one H1 is recommended. Found: {" | ".join(h1_list[:5])}'
                })

            # Title vs H1 mismatch
            h1 = h1_list[0].strip()
            if title and h1:
                sim = self._text_similarity(title.lower(), h1.lower())
                if sim < 0.3:
                    issues.append({
                        'url': url,
                        'type': 'warning',
                        'category': 'SEO',
                        'issue': 'Title vs H1 Mismatch',
                        'details': f'Title: "{title[:80]}" vs H1: "{h1[:80]}" — low similarity ({sim*100:.0f}%). May confuse search engines.'
                    })

        # Heading hierarchy — flag skipped levels
        if h3 and not h2:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'SEO',
                'issue': 'Skipped Heading Level (H3 without H2)',
                'details': f'Page uses H3 tags but has no H2 tags, breaking heading hierarchy'
            })
        if h2 and not h1_list:
            # H2 without H1 already covered by missing H1 above
            pass

    def _check_content_issues(self, result, issues):
        """Check for content-related issues"""
        url = result.get('url', '')
        word_count = result.get('word_count', 0)

        if word_count < 300:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Content',
                'issue': 'Thin Content',
                'details': f'Page has only {word_count} words (recommended: ≥300)'
            })

    def _check_technical_issues(self, result, issues):
        """Check for technical SEO issues"""
        url = result.get('url', '')
        status_code = result.get('status_code', 0)

        # No HTTP response at all (DNS failure, connection refused, timeout, etc.)
        if status_code == 0:
            error_type = result.get('error_type')
            error_label_map = {
                'dns_not_found': ('DNS Not Found',
                                  'Domain does not resolve. The site may be expired or misconfigured.'),
                'connection_refused': ('Connection Refused',
                                       'Server actively refused the connection.'),
                'timeout': ('Request Timeout',
                            'Server did not respond before the request timed out.'),
                'ssl_error': ('SSL/TLS Error',
                              'Could not establish a secure connection (certificate or TLS issue).'),
                'connection_error': ('Connection Error',
                                     'Could not connect to the server.'),
            }
            if error_type and error_type != 'file_too_large':
                title, default_details = error_label_map.get(
                    error_type, ('No Response', 'No HTTP response received.')
                )
                issues.append({
                    'url': url,
                    'type': 'error',
                    'category': 'Technical',
                    'issue': title,
                    'details': result.get('error') or default_details
                })

        if status_code >= 400 and status_code < 500:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'Technical',
                'issue': f'{status_code} Client Error',
                'details': self._get_status_code_message(status_code)
            })
        elif status_code >= 500:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'Technical',
                'issue': f'{status_code} Server Error',
                'details': self._get_status_code_message(status_code)
            })
        elif status_code >= 300 and status_code < 400:
            issues.append({
                'url': url,
                'type': 'info',
                'category': 'Technical',
                'issue': f'{status_code} Redirect',
                'details': 'URL redirects to another location'
            })

        # Canonical URL checks
        canonical_url = result.get('canonical_url', '')
        if not canonical_url:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Technical',
                'issue': 'Missing Canonical URL',
                'details': 'Page has no canonical URL specified'
            })
        elif canonical_url != url:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Technical',
                'issue': 'Canonical URL Different',
                'details': f"Canonical points to: {canonical_url}"
            })

    def _check_mobile_issues(self, result, issues):
        """Check for mobile optimization issues"""
        url = result.get('url', '')

        if not result.get('viewport'):
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'Mobile',
                'issue': 'Missing Viewport Meta Tag',
                'details': 'Page is not mobile-optimized'
            })

    def _check_accessibility_issues(self, result, issues):
        """Check for accessibility issues"""
        url = result.get('url', '')

        if not result.get('lang'):
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Accessibility',
                'issue': 'Missing Language Attribute',
                'details': 'HTML tag has no lang attribute'
            })

        # Image alt text
        images = result.get('images', [])
        images_without_alt = [img for img in images if not img.get('alt')]
        if images_without_alt:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Accessibility',
                'issue': 'Images Without Alt Text',
                'details': f'{len(images_without_alt)} of {len(images)} images lack alt text'
            })

    def _check_social_media_issues(self, result, issues):
        """Check for social media optimization issues"""
        url = result.get('url', '')

        if not result.get('og_tags'):
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Social',
                'issue': 'Missing OpenGraph Tags',
                'details': 'Page has no OpenGraph tags for social sharing'
            })

        if not result.get('twitter_tags'):
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Social',
                'issue': 'Missing Twitter Card Tags',
                'details': 'Page has no Twitter Card tags'
            })

    def _check_structured_data_issues(self, result, issues):
        """Check for structured data issues based on detected page type."""
        url = result.get('url', '')
        has_schema = bool(result.get('json_ld') or result.get('schema_org'))
        page = classify_page(result)
        page_type = page['page_type']

        if page_type in ('structural', 'unknown'):
            return

        if has_schema:
            # Schema present — check if it matches the expected type
            ld_types = _get_json_ld_types(result.get('json_ld'))
            expected = page.get('expected_schema', '')
            if not expected:
                return
            # Type-specific schema validation
            type_ld_map = {
                'article':      {'article', 'blogposting', 'newsarticle', 'techarticle', 'report'},
                'product':      {'product'},
                'event':        {'event'},
                'faq':          {'faqpage'},
                'profile':      {'person', 'profilepage'},
                'collection':   {'collectionpage', 'itemlist'},
                'organization': {'organization', 'localbusiness', 'corporation'},
            }
            expected_types = type_ld_map.get(page_type, set())
            if expected_types and not (ld_types & expected_types):
                issues.append({
                    'url': url,
                    'type': 'warning',
                    'category': 'Structured Data',
                    'issue': f'Wrong Schema Type for {page_type.title()} Page',
                    'details': f'Page detected as {page_type} (signals: {", ".join(page["signals"])}) but schema type is {", ".join(ld_types) or "unknown"}. Expected: {expected}.'
                })
            return

        # No schema at all
        if page['needs_schema']:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'Structured Data',
                'issue': f'Missing Schema: {page["expected_schema"]}',
                'details': f'Page detected as {page_type} (signals: {", ".join(page["signals"])}) but has no structured data. Add {page["expected_schema"]} schema.'
            })
        elif page_type == 'collection':
            issues.append({
                'url': url,
                'type': 'info',
                'category': 'Structured Data',
                'issue': 'No Structured Data on Collection Page',
                'details': f'Collection/category page has no schema. Consider adding CollectionPage or ItemList schema to improve visibility in search.'
            })

    def _check_performance_issues(self, result, issues):
        """Check for performance issues"""
        url = result.get('url', '')
        response_time = result.get('response_time', 0)
        page_size = result.get('size', 0)

        if response_time > 3000:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'Performance',
                'issue': 'Slow Response Time',
                'details': f'Page took {response_time}ms to respond (recommended: <3000ms)'
            })
        elif response_time > 1000:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Performance',
                'issue': 'Moderate Response Time',
                'details': f'Page took {response_time}ms to respond (recommended: <1000ms)'
            })

        if page_size > 3 * 1024 * 1024:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'Performance',
                'issue': 'Large Page Size',
                'details': f'Page size is {page_size / 1024 / 1024:.1f}MB (recommended: <3MB)'
            })
        elif page_size > 1 * 1024 * 1024:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Performance',
                'issue': 'Moderate Page Size',
                'details': f'Page size is {page_size / 1024 / 1024:.1f}MB (recommended: <1MB)'
            })

    def _check_indexability_issues(self, result, issues):
        """Check for indexability issues"""
        url = result.get('url', '')
        robots = result.get('robots', '').lower()

        if 'noindex' in robots:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'Indexability',
                'issue': 'Noindex Tag Present',
                'details': 'Page is BLOCKED from search engines - has noindex directive'
            })

        if 'nofollow' in robots:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'Indexability',
                'issue': 'Nofollow Tag Present',
                'details': 'Links on this page are NOT followed by search engines - has nofollow directive'
            })

    def _check_broken_image_issues(self, result, issues):
        """Check for broken image URLs on the page"""
        url = result.get('url', '')
        broken_images = result.get('broken_images', [])
        for img in broken_images:
            status = img.get('status', 0)
            img_url = img.get('url', '')
            if status == 0:
                issues.append({
                    'url': url,
                    'type': 'error',
                    'category': 'Content',
                    'issue': 'Broken Image (No Response)',
                    'details': f'Image does not respond: {img_url}'
                })
            elif status >= 400:
                issues.append({
                    'url': url,
                    'type': 'error',
                    'category': 'Content',
                    'issue': f'Broken Image ({status})',
                    'details': f'Image returned {status}: {img_url}'
                })

    def _check_content_freshness(self, result, issues):
        """Flag articles not updated in over 12 months using og:article:published_time"""
        url = result.get('url', '')
        og = result.get('og_tags', {})
        published = og.get('article:published_time', '') or og.get('published_time', '')
        if not published:
            return
        try:
            pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - pub_date).days
            if age_days > 365:
                issues.append({
                    'url': url,
                    'type': 'warning',
                    'category': 'Content',
                    'issue': 'Stale Content',
                    'details': f'Published {age_days} days ago ({pub_date.strftime("%Y-%m-%d")}). Content over 12 months old may lose ranking freshness.'
                })
        except (ValueError, TypeError):
            pass

    def _check_redirect_chain(self, result, issues):
        """Flag redirect chains of 3+ hops."""
        depth = result.get('redirect_depth', 0)
        if depth >= 3:
            chain = result.get('redirect_chain', [])
            preview = ' → '.join(chain[:5]) + ('…' if len(chain) > 5 else '')
            issues.append({
                'url': result.get('url', ''),
                'type': 'warning',
                'category': 'Technical',
                'issue': f'Redirect Chain ({depth} hops)',
                'details': f'URL passes through {depth} redirects before reaching destination: {preview}'
            })

    def _check_cookie_consent(self, result, issues):
        """Flag pages with no detectable cookie consent platform."""
        url = result.get('url', '')
        # Only flag HTML pages that loaded successfully
        if result.get('status_code', 0) != 200:
            return
        if result.get('content_type', '') and 'text/html' not in result.get('content_type', ''):
            return
        consent = result.get('cookie_consent')
        if consent is None:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Compliance',
                'issue': 'No Cookie Consent Detected',
                'details': 'No cookie consent platform found (Cookiebot, OneTrust, CookieYes, etc.). May violate GDPR/CCPA.'
            })

    def _check_readability(self, result, issues):
        """Flag pages with poor readability score (English content pages only)."""
        url = result.get('url', '')
        score = result.get('readability_score')
        if score is None:
            return
        # Flesch reading ease is English-only — skip non-English pages
        lang = (result.get('lang') or '').lower().split('-')[0]
        if lang and lang != 'en':
            return
        # Only flag content pages — readability on contact/about pages is irrelevant
        page = classify_page(result)
        if not page['is_content']:
            return
        if score < 30:
            issues.append({
                'url': url,
                'type': 'error',
                'category': 'Content',
                'issue': f'Very Difficult to Read (Flesch {score})',
                'details': f'Flesch Reading Ease score of {score} — very hard to read. Target 60+ for general audience, 70+ for consumer content.'
            })
        elif score < 50:
            issues.append({
                'url': url,
                'type': 'warning',
                'category': 'Content',
                'issue': f'Difficult to Read (Flesch {score})',
                'details': f'Flesch Reading Ease score of {score} — difficult to read. Target 60+ for general audience.'
            })

    def _check_schema_completeness(self, result, issues):
        """Flag schema blocks that are missing required fields for their page type."""
        url = result.get('url', '')
        missing = result.get('schema_missing_fields', [])
        if not missing:
            return
        page = classify_page(result)
        if page['page_type'] not in ('article', 'product', 'event'):
            return
        issues.append({
            'url': url,
            'type': 'warning',
            'category': 'Structured Data',
            'issue': 'Incomplete Schema Markup',
            'details': f'{page["page_type"].title()} page schema is missing required fields: {", ".join(missing)}. Add these to improve search visibility and E-E-A-T signals.'
        })

    def detect_domain_checks(self, base_url, session):
        """
        One-time per-domain checks: llms.txt presence, AI bot robots.txt rules.
        Call once per crawl with the base URL and requests session.
        """
        import re as _re
        from urllib.parse import urljoin
        issues = []

        try:
            parsed = __import__('urllib.parse', fromlist=['urlparse']).urlparse(base_url)
            base = f"{parsed.scheme}://{parsed.netloc}"

            # ── llms.txt check ──────────────────────────────────────
            try:
                r = session.get(urljoin(base, '/llms.txt'), timeout=10, allow_redirects=True)
                if r.status_code == 200:
                    pass  # present — no issue
                else:
                    issues.append({
                        'url': base_url,
                        'type': 'info',
                        'category': 'AI Optimization',
                        'issue': 'llms.txt Not Found',
                        'details': 'No /llms.txt file detected. Adding one helps LLMs (ChatGPT, Claude, Perplexity) understand and cite your content correctly.'
                    })
            except Exception:
                pass

            # ── robots.txt AI bot check ──────────────────────────────
            try:
                r = session.get(urljoin(base, '/robots.txt'), timeout=10, allow_redirects=True)
                if r.status_code == 200:
                    content = r.text
                    ai_bots = {
                        'GPTBot': 'OpenAI / ChatGPT',
                        'ClaudeBot': 'Anthropic / Claude',
                        'PerplexityBot': 'Perplexity AI',
                        'Google-Extended': 'Google Bard/Gemini',
                        'CCBot': 'Common Crawl (training data)',
                    }
                    blocked = []
                    # Crude but effective: check if each bot appears in a Disallow block
                    for bot, label in ai_bots.items():
                        pattern = rf'User-agent:\s*{_re.escape(bot)}'
                        if _re.search(pattern, content, _re.IGNORECASE):
                            # Check if followed by Disallow: /
                            idx = _re.search(pattern, content, _re.IGNORECASE).start()
                            snippet = content[idx:idx+200]
                            if _re.search(r'Disallow:\s*/', snippet):
                                blocked.append(label)
                    if blocked:
                        issues.append({
                            'url': base_url,
                            'type': 'warning',
                            'category': 'AI Optimization',
                            'issue': f'AI Bots Blocked in robots.txt ({len(blocked)})',
                            'details': f'The following AI crawlers are blocked: {", ".join(blocked)}. This prevents LLM training and citation of your content.'
                        })
            except Exception:
                pass

        except Exception:
            pass

        with self.issues_lock:
            self.detected_issues.extend(issues)

    def detect_broken_link_source_issues(self, all_results, all_links):
        """Flag source pages that contain broken outbound internal links (4xx/0)."""
        broken_urls = {
            r.get('url', '')
            for r in all_results
            if r.get('status_code', 200) == 0 or r.get('status_code', 200) >= 400
        }
        if not broken_urls:
            return

        source_broken = {}
        for link in all_links:
            if not link.get('is_internal'):
                continue
            target = link.get('target_url', '')
            if target in broken_urls:
                src = link.get('source_url', '')
                source_broken.setdefault(src, []).append(target)

        issues = []
        for src_url, targets in source_broken.items():
            if self._should_exclude(src_url):
                continue
            preview = ', '.join(targets[:3]) + ('…' if len(targets) > 3 else '')
            issues.append({
                'url': src_url,
                'type': 'error',
                'category': 'Links',
                'issue': f'Links to {len(targets)} Broken Page(s)',
                'details': f'This page links to {len(targets)} broken URL(s): {preview}'
            })
        with self.issues_lock:
            self.detected_issues.extend(issues)

    def detect_orphan_pages(self, all_results, all_links):
        """Flag internal pages with zero inbound internal links."""
        linked_to = {lk.get('target_url', '') for lk in all_links if lk.get('is_internal')}

        issues = []
        for r in all_results:
            url = r.get('url', '')
            if r.get('depth', 0) == 0:
                continue  # start URL is never an orphan
            if self._should_exclude(url):
                continue
            if url not in linked_to:
                issues.append({
                    'url': url,
                    'type': 'warning',
                    'category': 'Links',
                    'issue': 'Orphan Page',
                    'details': 'No internal pages link to this URL — risk to crawlability and link equity'
                })
        with self.issues_lock:
            self.detected_issues.extend(issues)

    def detect_duplicate_titles_and_meta(self, all_results):
        """Flag exact duplicate title tags, meta descriptions, and H1s across pages."""
        title_map = {}
        meta_map = {}
        h1_map = {}

        for r in all_results:
            url = r.get('url', '')
            if self._should_exclude(url):
                continue
            t = r.get('title', '').strip()
            m = r.get('meta_description', '').strip()
            h = r.get('h1', '').strip()
            if t:
                title_map.setdefault(t, []).append(url)
            if m:
                meta_map.setdefault(m, []).append(url)
            if h:
                h1_map.setdefault(h, []).append(url)

        issues = []

        for title, urls in title_map.items():
            if len(urls) > 1:
                for url in urls:
                    others = [u for u in urls if u != url]
                    issues.append({
                        'url': url,
                        'type': 'warning',
                        'category': 'Duplication',
                        'issue': f'Duplicate Title Tag ({len(urls)} pages)',
                        'details': f'Title "{title[:80]}" is shared with: {others[0]}' + (f' and {len(others)-1} more' if len(others) > 1 else '')
                    })

        for meta, urls in meta_map.items():
            if len(urls) > 1:
                for url in urls:
                    others = [u for u in urls if u != url]
                    issues.append({
                        'url': url,
                        'type': 'warning',
                        'category': 'Duplication',
                        'issue': f'Duplicate Meta Description ({len(urls)} pages)',
                        'details': f'Meta description "{meta[:80]}" shared with: {others[0]}' + (f' and {len(others)-1} more' if len(others) > 1 else '')
                    })

        for h1, urls in h1_map.items():
            if len(urls) > 1:
                for url in urls:
                    others = [u for u in urls if u != url]
                    issues.append({
                        'url': url,
                        'type': 'warning',
                        'category': 'Duplication',
                        'issue': f'Duplicate H1 Tag ({len(urls)} pages)',
                        'details': f'H1 "{h1[:80]}" is shared with: {others[0]}' + (f' and {len(others)-1} more' if len(others) > 1 else '')
                    })

        with self.issues_lock:
            self.detected_issues.extend(issues)

    def detect_duplication_issues(self, all_results, similarity_threshold=0.85):
        """
        Detect content duplication across all crawled pages.

        Args:
            all_results: List of all crawled result dictionaries
            similarity_threshold: Minimum similarity ratio to flag as duplicate (0.0-1.0)
        """
        issues = []
        processed_pairs = set()

        # Compare each result with all others
        for i, result1 in enumerate(all_results):
            url1 = result1.get('url', '')

            # Skip if URL should be excluded
            if self._should_exclude(url1):
                continue

            for j, result2 in enumerate(all_results):
                # Skip same URL or already processed pairs
                if i >= j:
                    continue

                url2 = result2.get('url', '')

                # Skip if URL should be excluded
                if self._should_exclude(url2):
                    continue

                # Create unique pair identifier
                pair_key = tuple(sorted([url1, url2]))
                if pair_key in processed_pairs:
                    continue

                processed_pairs.add(pair_key)

                # Calculate similarity
                similarity = self._calculate_content_similarity(result1, result2)

                # Flag as duplicate if above threshold
                if similarity >= similarity_threshold:
                    # Add issue for both URLs
                    issues.append({
                        'url': url1,
                        'type': 'warning',
                        'category': 'Duplication',
                        'issue': 'Duplicate Content Detected',
                        'details': f'Content is {similarity*100:.1f}% similar to {url2}'
                    })
                    issues.append({
                        'url': url2,
                        'type': 'warning',
                        'category': 'Duplication',
                        'issue': 'Duplicate Content Detected',
                        'details': f'Content is {similarity*100:.1f}% similar to {url1}'
                    })

        # Add all detected duplication issues
        with self.issues_lock:
            self.detected_issues.extend(issues)

    def _calculate_content_similarity(self, result1, result2):
        """
        Calculate similarity between two page results.

        Compares title, meta description, h1, and content length.
        Returns a similarity ratio between 0.0 and 1.0.
        """
        # Extract content fields
        title1 = result1.get('title', '').lower().strip()
        title2 = result2.get('title', '').lower().strip()

        desc1 = result1.get('meta_description', '').lower().strip()
        desc2 = result2.get('meta_description', '').lower().strip()

        h1_1 = result1.get('h1', '').lower().strip()
        h1_2 = result2.get('h1', '').lower().strip()

        word_count1 = result1.get('word_count', 0)
        word_count2 = result2.get('word_count', 0)

        # Calculate individual similarities
        title_sim = self._text_similarity(title1, title2) if title1 and title2 else 0
        desc_sim = self._text_similarity(desc1, desc2) if desc1 and desc2 else 0
        h1_sim = self._text_similarity(h1_1, h1_2) if h1_1 and h1_2 else 0

        # Word count similarity (1.0 if within 10% of each other)
        if word_count1 and word_count2:
            max_count = max(word_count1, word_count2)
            min_count = min(word_count1, word_count2)
            word_count_sim = min_count / max_count if max_count > 0 else 0
        else:
            word_count_sim = 0

        # Weighted average (title and description are most important)
        weights = {
            'title': 0.35,
            'desc': 0.35,
            'h1': 0.20,
            'word_count': 0.10
        }

        overall_similarity = (
            title_sim * weights['title'] +
            desc_sim * weights['desc'] +
            h1_sim * weights['h1'] +
            word_count_sim * weights['word_count']
        )

        return overall_similarity

    def _text_similarity(self, text1, text2):
        """Calculate similarity ratio between two text strings using SequenceMatcher"""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()

    def _should_exclude(self, url):
        """Check if URL should be excluded from issue detection"""
        parsed = urlparse(url)
        path = parsed.path

        for pattern in self.exclusion_patterns:
            if '*' in pattern:
                if fnmatch(path, pattern):
                    return True
            elif path == pattern or path.startswith(pattern.rstrip('*')):
                return True

        return False

    def _get_status_code_message(self, status_code):
        """Get descriptive message for HTTP status codes"""
        messages = {
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            405: 'Method Not Allowed',
            406: 'Not Acceptable',
            408: 'Request Timeout',
            410: 'Gone',
            429: 'Too Many Requests',
            500: 'Internal Server Error',
            501: 'Not Implemented',
            502: 'Bad Gateway',
            503: 'Service Unavailable',
            504: 'Gateway Timeout',
            505: 'HTTP Version Not Supported'
        }
        return messages.get(status_code, f'HTTP {status_code} Error')

    def get_issues(self):
        """Get all detected issues"""
        with self.issues_lock:
            return self.detected_issues.copy()

    def reset(self):
        """Reset detected issues"""
        with self.issues_lock:
            self.detected_issues.clear()
