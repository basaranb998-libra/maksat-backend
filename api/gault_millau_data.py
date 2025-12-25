"""
Gault & Millau Türkiye 2025 Ödüllü Restoranlar

Bu dosya Gault & Millau Türkiye rehberinde yer alan
ödüllü restoranların listesini içerir.

Toque Sistemi:
- 4 Toque: Olağanüstü (En yüksek derece)
- 3 Toque: Mükemmel
- 2 Toque: Çok İyi
- 1 Toque: İyi

Kaynak: Gault & Millau Turkey 2025
"""

from typing import Dict, List, Optional

# Gault & Millau ödüllü restoranlar
# Key: Restoran adı (küçük harf, normalize edilmiş)
# Value: {toques: int, award: str | None, city: str}

GAULT_MILLAU_RESTAURANTS: Dict[str, Dict] = {
    # 4 Toque - En Üst Seviye
    "türk": {
        "toques": 4,
        "award": "Yılın Şefi 2025",
        "city": "Istanbul",
        "chef": "Fatih Tutak",
        "instagram": "turkfatihtutak"
    },
    "turk": {
        "toques": 4,
        "award": "Yılın Şefi 2025",
        "city": "Istanbul",
        "chef": "Fatih Tutak",
        "instagram": "turkfatihtutak"
    },
    "neolokal": {
        "toques": 4,
        "award": "Prestijli Masa",
        "city": "Istanbul",
        "chef": "Maksut Aşkar",
        "instagram": "neolokal"
    },

    # 3 Toque
    "mikla": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": "Mehmet Gürs",
        "instagram": "miklaistanbul"
    },
    "nicole": {
        "toques": 3,
        "award": "Yılın Keşfi",
        "city": "Istanbul",
        "chef": None,
        "instagram": "nicoleistanbul"
    },
    "sunset grill & bar": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "sunsetgrillbar"
    },
    "sunset grill bar": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "sunsetgrillbar"
    },
    "topaz": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "topazistanbul"
    },
    "araka": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "arakabogazici"
    },
    "nusr-et steakhouse": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": "Nusret Gökçe",
        "instagram": "nuaborj"
    },
    "nusr-et": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": "Nusret Gökçe",
        "instagram": "nuaborj"
    },
    "nusret": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": "Nusret Gökçe",
        "instagram": "nuaborj"
    },

    # 2 Toque
    "balıkçı sabahattin": {
        "toques": 2,
        "award": "En İyi Balık Restoranı",
        "city": "Istanbul",
        "chef": None,
        "instagram": "balikcisabahattin"
    },
    "balikci sabahattin": {
        "toques": 2,
        "award": "En İyi Balık Restoranı",
        "city": "Istanbul",
        "chef": None,
        "instagram": "balikcisabahattin"
    },
    "çiya sofrası": {
        "toques": 2,
        "award": "En İyi Geleneksel Mutfak",
        "city": "Istanbul",
        "chef": "Musa Dağdeviren",
        "instagram": "caborestaurants"
    },
    "ciya sofrasi": {
        "toques": 2,
        "award": "En İyi Geleneksel Mutfak",
        "city": "Istanbul",
        "chef": "Musa Dağdeviren",
        "instagram": "caborestaurants"
    },
    "asmalı cavit": {
        "toques": 2,
        "award": "En İyi Meyhane",
        "city": "Istanbul",
        "chef": None,
        "instagram": "asmalicavit"
    },
    "asmali cavit": {
        "toques": 2,
        "award": "En İyi Meyhane",
        "city": "Istanbul",
        "chef": None,
        "instagram": "asmalicavit"
    },
    "lokanta maya": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": "Didem Şenol",
        "instagram": "lokantamaya"
    },
    "kantin": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": "Şemsa Denizsel",
        "instagram": "kantinistanbul"
    },
    "pandeli": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "pandeli1901"
    },
    "develi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "develirestaurant"
    },
    "hamdi restaurant": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "hamdirestaurant"
    },
    "hamdi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "hamdirestaurant"
    },
    "karaköy lokantası": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "karakoylokantasi"
    },
    "karakoy lokantasi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "karakoylokantasi"
    },
    "beyti": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "beytirestaurant"
    },
    "köşebaşı": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "kosebasiresmi"
    },
    "kosebasi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "kosebasiresmi"
    },
    "günaydın": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "gunaydintr"
    },
    "gunaydin": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "gunaydintr"
    },
    "zübeyir ocakbaşı": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "zubeyirocakbasi"
    },
    "zubeyir ocakbasi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "zubeyirocakbasi"
    },

    # 1 Toque - Önerilen
    "tarihi sultanahmet köftecisi": {
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Istanbul",
        "chef": None,
        "instagram": "sultanahmetkoftecisi1920"
    },
    "tarihi sultanahmet koftecisi": {
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Istanbul",
        "chef": None,
        "instagram": "sultanahmetkoftecisi1920"
    },
    "sultanahmet köftecisi": {
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Istanbul",
        "chef": None,
        "instagram": "sultanahmetkoftecisi1920"
    },
    "sultanahmet koftecisi": {
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Istanbul",
        "chef": None,
        "instagram": "sultanahmetkoftecisi1920"
    },
    "vefa bozacısı": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "vefabozacisi1876"
    },
    "vefa bozacisi": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "vefabozacisi1876"
    },
    "karaköy güllüoğlu": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "karakoygulluoglu"
    },
    "karakoy gulluoglu": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "karakoygulluoglu"
    },
    "hafız mustafa": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "hafizmustafa1864"
    },
    "hafiz mustafa": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "hafizmustafa1864"
    },
    "datça sofrası": {
        "toques": 1,
        "award": None,
        "city": "Datça",
        "chef": None,
        "instagram": "datcasofrasi"
    },
    "datca sofrasi": {
        "toques": 1,
        "award": None,
        "city": "Datça",
        "chef": None,
        "instagram": "datcasofrasi"
    },
}


def normalize_name(name: str) -> str:
    """Restoran adını normalize et (küçük harf, özel karakterler temizle)."""
    if not name:
        return ""

    # Türkçe karakter dönüşümü
    tr_map = {
        'ı': 'i', 'İ': 'i', 'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u', 'ş': 's', 'Ş': 's',
        'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c',
        'â': 'a', 'Â': 'a', 'î': 'i', 'Î': 'i',
    }

    result = name.lower().strip()
    for tr_char, ascii_char in tr_map.items():
        result = result.replace(tr_char, ascii_char)

    return result


def get_gault_millau_info(venue_name: str) -> Optional[Dict]:
    """
    Mekan adına göre Gault & Millau bilgisi döndür.

    Args:
        venue_name: Mekan adı

    Returns:
        {toques: int, award: str | None, instagram: str | None} veya None
    """
    if not venue_name:
        return None

    normalized = normalize_name(venue_name)

    # Tam eşleşme
    if normalized in GAULT_MILLAU_RESTAURANTS:
        info = GAULT_MILLAU_RESTAURANTS[normalized]
        return {
            "toques": info["toques"],
            "award": info.get("award"),
            "instagram": info.get("instagram")
        }

    # Kısmi eşleşme (mekan adı içinde arama)
    for key, info in GAULT_MILLAU_RESTAURANTS.items():
        # Hem key'in normalized name içinde olup olmadığını
        # hem de normalized name'in key içinde olup olmadığını kontrol et
        if key in normalized or normalized in key:
            # Minimum 4 karakter eşleşmesi olmalı
            if len(key) >= 4:
                return {
                    "toques": info["toques"],
                    "award": info.get("award"),
                    "instagram": info.get("instagram")
                }

    return None


def enrich_venue_with_gault_millau(venue: Dict) -> Dict:
    """
    Venue verisine Gault & Millau bilgisi ekle.
    Instagram URL'si yoksa ve G&M verisinde varsa onu da ekler.

    Args:
        venue: Venue dictionary

    Returns:
        Güncellenmiş venue dictionary
    """
    if not venue:
        return venue

    name = venue.get("name", "")
    gm_info = get_gault_millau_info(name)

    if gm_info:
        venue["gaultMillauToques"] = gm_info["toques"]
        if gm_info.get("award"):
            venue["gaultMillauAward"] = gm_info["award"]

        # Instagram URL yoksa G&M verisinden ekle
        if not venue.get("instagramUrl") and gm_info.get("instagram"):
            venue["instagramUrl"] = f"https://instagram.com/{gm_info['instagram']}"

    return venue


def enrich_venues_with_gault_millau(venues: List[Dict]) -> List[Dict]:
    """
    Birden fazla venue'ya Gault & Millau bilgisi ekle.

    Args:
        venues: Venue listesi

    Returns:
        Güncellenmiş venue listesi
    """
    return [enrich_venue_with_gault_millau(v) for v in venues]
