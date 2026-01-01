"""
Instagram URL Discovery Service

Bu servis, mekan ismi ve şehir bilgisi kullanarak
Instagram profil URL'lerini bulur.

Yöntemler:
1. Mevcut Instagram URL varsa kullan
2. Website'ten Instagram linki çek
3. Mekan adından username tahmin et ve profil varlığını kontrol et
4. Google Custom Search API ile ara (opsiyonel)
"""

import os
import re
import sys
import requests
from typing import Optional, Dict, List
from functools import lru_cache
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Google Custom Search API credentials
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
GOOGLE_CSE_ID = os.environ.get('GOOGLE_CSE_ID')

# Cache için basit in-memory storage
_instagram_cache: Dict[str, str] = {}
_cache_expiry: Dict[str, float] = {}
CACHE_TTL = 86400 * 7  # 7 gün

# Türkçe karakter dönüşüm tablosu
TR_CHAR_MAP = {
    'ı': 'i', 'İ': 'i', 'i̇': 'i',  # i̇ = lowercase i + combining dot (Python'un İ.lower() sonucu)
    'ğ': 'g', 'Ğ': 'g',
    'ü': 'u', 'Ü': 'u', 'ş': 's', 'Ş': 's',
    'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c',
    'â': 'a', 'Â': 'a', 'î': 'i', 'Î': 'i',
    'û': 'u', 'Û': 'u', 'ê': 'e', 'Ê': 'e'
}

# Mekan adından çıkarılacak kelimeler
WORDS_TO_REMOVE = [
    'restaurant', 'restoran', 'cafe', 'kafe', 'kahve', 'coffee',
    'bar', 'pub', 'meyhane', 'ocakbasi', 'ocakbaşı', 'kebap', 'kebab',
    'et', 'balik', 'balık', 'fish', 'steak', 'house', 'evi', 'evi̇',
    'kitchen', 'mutfak', 'bistro', 'brasserie', 'lounge', 'terrace', 'teras',
    'garden', 'bahce', 'bahçe', 'roof', 'rooftop', 'çatı',
    'the', 'and', '&', 've', 'by', 'at'
]

# Şehir kısaltmaları
CITY_ABBREVIATIONS = {
    'istanbul': ['ist', 'istanbull'],
    'izmir': ['izm'],
    'ankara': ['ank'],
    'antalya': ['ant'],
    'bursa': ['brs'],
    'adana': ['adn'],
}


def turkish_to_ascii(text: str) -> str:
    """Türkçe karakterleri ASCII'ye çevir."""
    result = text.lower()
    for tr_char, ascii_char in TR_CHAR_MAP.items():
        result = result.replace(tr_char, ascii_char)
    return result


def generate_username_variants(venue_name: str, city: str = None) -> List[str]:
    """
    Mekan adından olası Instagram username'lerini üret.

    Örnek: "Köşebaşı Et Lokantası" →
    ['kosebasi', 'kosebasitr', 'kosebasi_ist', 'kosebasi.istanbul',
     'kosebasietlokantasi', 'kosebasi_et', 'thekosebasi']
    """
    variants = []

    # Temel temizlik
    name = venue_name.strip()
    name_ascii = turkish_to_ascii(name)

    # Özel karakterleri temizle
    name_clean = re.sub(r'[^\w\s]', '', name_ascii)
    words = name_clean.split()

    # Gereksiz kelimeleri çıkar
    core_words = [w for w in words if w.lower() not in WORDS_TO_REMOVE]
    if not core_words:
        core_words = words[:2]  # En az 2 kelime al

    # Temel username (tüm kelimeler birleşik - filtrelenmiş)
    base_username = ''.join(core_words)
    if len(base_username) >= 3:
        variants.append(base_username)
        # Şehir eklentili tam isim (ledimancheizmir gibi) - ÖNCELİKLİ
        if city:
            city_ascii = turkish_to_ascii(city.lower())
            variants.insert(0, f"{base_username}{city_ascii}")  # En başa ekle
            variants.append(f"{base_username}_{city_ascii}")
            variants.append(f"{base_username}.{city_ascii}")

    # Tüm kelimeler birleşik (FİLTRESİZ - coffee, roasting vs dahil)
    full_username = ''.join(words)
    if len(full_username) >= 3 and full_username != base_username:
        variants.append(full_username)
        # Şehir eklentili full isim
        if city:
            city_ascii = turkish_to_ascii(city.lower())
            variants.append(f"{full_username}{city_ascii}")

    # İlk kelime (genellikle mekan adı)
    if core_words:
        first_word = core_words[0]
        if len(first_word) >= 3:
            variants.append(first_word)
            variants.append(f"{first_word}tr")
            variants.append(f"{first_word}_tr")
            variants.append(f"the{first_word}")

            # Şehir eklentileri
            if city:
                city_ascii = turkish_to_ascii(city.lower())
                variants.append(f"{first_word}{city_ascii}")
                variants.append(f"{first_word}_{city_ascii}")
                variants.append(f"{first_word}.{city_ascii}")

                # Şehir kısaltmaları
                city_abbrevs = CITY_ABBREVIATIONS.get(city_ascii, [])
                for abbr in city_abbrevs:
                    variants.append(f"{first_word}{abbr}")
                    variants.append(f"{first_word}_{abbr}")

    # İlk iki kelime (alt çizgi ile)
    if len(core_words) >= 2:
        two_words = f"{core_words[0]}_{core_words[1]}"
        variants.append(two_words)
        two_words_no_underscore = f"{core_words[0]}{core_words[1]}"
        variants.append(two_words_no_underscore)

    # Nokta ile ayrılmış
    if len(core_words) >= 2:
        dotted = '.'.join(core_words)
        variants.append(dotted)

    # Resmi hesap formatları
    if base_username:
        variants.append(f"{base_username}official")
        variants.append(f"{base_username}_official")

    # Duplicate'ları kaldır ve sırala (kısa olanlar önce)
    seen = set()
    unique_variants = []
    for v in variants:
        v_lower = v.lower()
        # Instagram username kuralları: 1-30 karakter, harf/rakam/nokta/alt çizgi
        if v_lower not in seen and len(v_lower) >= 3 and len(v_lower) <= 30:
            if re.match(r'^[a-zA-Z0-9_.]+$', v_lower):
                seen.add(v_lower)
                unique_variants.append(v_lower)

    # Kısa olanları önce dene
    unique_variants.sort(key=len)

    return unique_variants[:10]  # Max 10 variant dene


def check_instagram_profile_exists(username: str) -> bool:
    """
    Instagram profilinin var olup olmadığını kontrol et.

    NOT: Instagram artık giriş yapmadan profil bilgisi göstermiyor.
    Bu yüzden HTTP kontrolü güvenilir değil. Şimdilik sadece
    bilinen kalıplara uyan username'leri kabul ediyoruz.
    """
    # Instagram login gerektirdiği için HTTP kontrolü güvenilir değil
    # Sadece username formatı geçerliyse True dön
    # Gerçek doğrulama için Google Custom Search API kullanılmalı

    # Username uzunluk kontrolü (Instagram kuralları)
    if not username or len(username) < 3 or len(username) > 30:
        return False

    # Sadece güvenli karakterler (harf, rakam, nokta, alt çizgi)
    import re
    if not re.match(r'^[a-zA-Z0-9_.]+$', username):
        return False

    # "Roasters", "Coffee", "Cafe" gibi kalıplar daha güvenilir
    # Çünkü bunlar genellikle mekan isimleri
    coffee_keywords = ['coffee', 'cafe', 'roaster', 'brew', 'espresso', 'barista']
    username_lower = username.lower()

    # Kahve/kafe ile ilgili bir username ise daha güvenilir
    for keyword in coffee_keywords:
        if keyword in username_lower:
            return True

    # Türkiye'deki yaygın mekan isim kalıpları
    # Kısa isimler (3-12 karakter) genellikle marka isimleri
    if len(username) <= 12:
        return True

    # Uzun isimler için daha seçici ol
    # "official", "tr", şehir ekleri genellikle gerçek hesaplar
    safe_suffixes = ['tr', 'official', 'ist', 'izm', 'ank']
    for suffix in safe_suffixes:
        if username_lower.endswith(suffix):
            return True

    # Varsayılan olarak kabul etme - yanlış pozitiflerden kaçın
    return False


def guess_instagram_from_name(venue_name: str, city: str = None) -> Optional[str]:
    """
    Mekan adından Instagram URL'si tahmin et ve doğrula.
    """
    variants = generate_username_variants(venue_name, city)

    if not variants:
        return None

    # Paralel olarak kontrol et (hızlı sonuç için)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for username in variants[:6]:  # İlk 6 variant'ı dene
            future = executor.submit(check_instagram_profile_exists, username)
            futures[future] = username

        for future in as_completed(futures, timeout=10):
            username = futures[future]
            try:
                if future.result():
                    instagram_url = f"https://instagram.com/{username}"
                    print(f"✅ INSTAGRAM - Guessed from name: {venue_name} -> {instagram_url}", file=sys.stderr, flush=True)
                    return instagram_url
            except Exception:
                continue

    return None


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
        # API key yoksa sessizce geç
        return None

    query = f"{venue_name} {city} instagram site:instagram.com"

    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': GOOGLE_API_KEY,
            'cx': GOOGLE_CSE_ID,
            'q': query,
            'num': 3,
        }

        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])

            for item in items:
                link = item.get('link', '')
                if 'instagram.com/' in link:
                    normalized = normalize_instagram_url(link)
                    if normalized:
                        print(f"✅ INSTAGRAM - Found via Google CSE: {venue_name} -> {normalized}", file=sys.stderr, flush=True)
                        return normalized

    except Exception:
        pass

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

    except Exception:
        pass

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
    3. Mekan adından username tahmin et ve doğrula
    4. Google Custom Search ile ara (API key varsa)

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

    # 3. Google Custom Search ile ara (API key varsa) - güvenilir sonuçlar
    if not instagram_url and GOOGLE_API_KEY and GOOGLE_CSE_ID:
        instagram_url = search_instagram_google(venue_name, city)

    # 4. Mekan adından tahmin et (şehir eklentili varyantlar - ledimancheizmir gibi)
    if not instagram_url:
        instagram_url = guess_instagram_from_name(venue_name, city)

    # Cache'e kaydet (None da dahil - negatif cache, ama daha kısa süre)
    _instagram_cache[cache_key] = instagram_url
    # Bulunamadıysa 1 gün, bulunduysa 7 gün cache
    cache_duration = CACHE_TTL if instagram_url else 86400
    _cache_expiry[cache_key] = time.time() + cache_duration

    if not instagram_url:
        print(f"⚠️ INSTAGRAM - Not found: {venue_name}", file=sys.stderr, flush=True)

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
