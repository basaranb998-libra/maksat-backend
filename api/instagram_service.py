"""
Instagram URL Discovery Service

Bu servis, mekan ismi ve şehir bilgisi kullanarak
Google Custom Search API ile Instagram profil URL'lerini bulur.
"""

import os
import re
import sys
import requests
from typing import Optional, Dict, Any
from urllib.parse import quote_plus
from functools import lru_cache
import time

# Google Custom Search API credentials
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
GOOGLE_CSE_ID = os.environ.get('GOOGLE_CSE_ID')  # Custom Search Engine ID

# Cache için basit in-memory storage
_instagram_cache: Dict[str, str] = {}
_cache_expiry: Dict[str, float] = {}
CACHE_TTL = 86400 * 7  # 7 gün


def normalize_instagram_url(url: str) -> Optional[str]:
    """
    Instagram URL'sini normalize et.
    Geçerli bir Instagram profil URL'si dön veya None.
    """
    if not url:
        return None

    url = url.strip()

    # Zaten tam URL mi?
    if 'instagram.com/' in url:
        # URL'den username çıkar
        match = re.search(r'instagram\.com/([a-zA-Z0-9_\.]+)', url)
        if match:
            username = match.group(1)
            # Geçersiz path'leri filtrele
            if username.lower() in ['p', 'reel', 'reels', 'stories', 'explore', 'accounts', 'direct', 'tv']:
                return None
            return f"https://instagram.com/{username}"

    # Sadece username verilmişse
    if re.match(r'^[a-zA-Z0-9_\.]+$', url):
        return f"https://instagram.com/{url}"

    return None


def search_instagram_google(venue_name: str, city: str) -> Optional[str]:
    """
    Google Custom Search API kullanarak Instagram URL'si bul.
    """
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        print("⚠️ INSTAGRAM - Google CSE API keys not configured", file=sys.stderr, flush=True)
        return None

    # Search query: "venue_name city instagram"
    query = f"{venue_name} {city} instagram site:instagram.com"

    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': GOOGLE_API_KEY,
            'cx': GOOGLE_CSE_ID,
            'q': query,
            'num': 3,  # İlk 3 sonuç
        }

        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])

            for item in items:
                link = item.get('link', '')
                # Instagram profil sayfası mı?
                if 'instagram.com/' in link:
                    normalized = normalize_instagram_url(link)
                    if normalized:
                        print(f"✅ INSTAGRAM - Found via Google CSE: {venue_name} -> {normalized}", file=sys.stderr, flush=True)
                        return normalized
        elif response.status_code == 403:
            print(f"⚠️ INSTAGRAM - Google CSE API quota exceeded", file=sys.stderr, flush=True)
        else:
            print(f"⚠️ INSTAGRAM - Google CSE error: {response.status_code}", file=sys.stderr, flush=True)

    except requests.exceptions.Timeout:
        print(f"⚠️ INSTAGRAM - Google CSE timeout for: {venue_name}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"❌ INSTAGRAM - Google CSE error: {e}", file=sys.stderr, flush=True)

    return None


def find_instagram_from_website(website_url: str) -> Optional[str]:
    """
    İşletmenin web sitesinden Instagram linkini bul.
    """
    if not website_url:
        return None

    # Website URL'si zaten Instagram mı?
    if 'instagram.com/' in website_url:
        return normalize_instagram_url(website_url)

    try:
        # Web sitesini çek
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(website_url, headers=headers, timeout=5)

        if response.status_code == 200:
            html = response.text

            # Instagram linklerini bul
            patterns = [
                r'href=["\']?(https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_\.]+)["\']?',
                r'instagram\.com/([a-zA-Z0-9_\.]+)',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    normalized = normalize_instagram_url(match)
                    if normalized:
                        print(f"✅ INSTAGRAM - Found from website: {website_url} -> {normalized}", file=sys.stderr, flush=True)
                        return normalized

    except requests.exceptions.Timeout:
        pass  # Timeout, sessizce geç
    except Exception as e:
        pass  # Hata, sessizce geç

    return None


def discover_instagram_url(
    venue_name: str,
    city: str,
    website: str = None,
    existing_instagram: str = None
) -> Optional[str]:
    """
    Mekanın Instagram URL'sini keşfet.

    Öncelik sırası:
    1. Mevcut geçerli Instagram URL'si varsa kullan
    2. Website'ten Instagram linki bul
    3. Google Custom Search ile ara

    Args:
        venue_name: Mekan adı
        city: Şehir adı
        website: Mekanın web sitesi (opsiyonel)
        existing_instagram: Mevcut Instagram URL (Gemini'den gelen)

    Returns:
        Geçerli Instagram URL veya None
    """
    # Cache key
    cache_key = f"{venue_name.lower()}:{city.lower()}"

    # Cache'de var mı?
    if cache_key in _instagram_cache:
        expiry = _cache_expiry.get(cache_key, 0)
        if time.time() < expiry:
            cached = _instagram_cache[cache_key]
            if cached:
                print(f"📦 INSTAGRAM - Cache hit: {venue_name} -> {cached}", file=sys.stderr, flush=True)
            return cached

    instagram_url = None

    # 1. Mevcut Instagram URL geçerli mi?
    if existing_instagram:
        normalized = normalize_instagram_url(existing_instagram)
        if normalized:
            instagram_url = normalized
            print(f"✅ INSTAGRAM - Using existing: {venue_name} -> {instagram_url}", file=sys.stderr, flush=True)

    # 2. Website'ten Instagram linki bul
    if not instagram_url and website:
        instagram_url = find_instagram_from_website(website)

    # 3. Google Custom Search ile ara
    if not instagram_url:
        instagram_url = search_instagram_google(venue_name, city)

    # Cache'e kaydet (None da dahil - negatif cache)
    _instagram_cache[cache_key] = instagram_url
    _cache_expiry[cache_key] = time.time() + CACHE_TTL

    return instagram_url


def batch_discover_instagram(venues: list, city: str) -> Dict[str, str]:
    """
    Birden fazla mekan için Instagram URL'lerini toplu keşfet.

    Args:
        venues: Mekan listesi (her biri 'name', 'website', 'instagramUrl' içermeli)
        city: Şehir adı

    Returns:
        {venue_name: instagram_url} dictionary
    """
    results = {}

    for venue in venues:
        name = venue.get('name', '')
        if not name:
            continue

        instagram_url = discover_instagram_url(
            venue_name=name,
            city=city,
            website=venue.get('website'),
            existing_instagram=venue.get('instagramUrl')
        )

        if instagram_url:
            results[name] = instagram_url

    return results
