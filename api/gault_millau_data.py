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
        "chef": "Fatih Tutak"
    },
    "turk": {
        "toques": 4,
        "award": "Yılın Şefi 2025",
        "city": "Istanbul",
        "chef": "Fatih Tutak"
    },
    "neolokal": {
        "toques": 4,
        "award": "Prestijli Masa",
        "city": "Istanbul",
        "chef": "Maksut Aşkar"
    },

    # 3 Toque
    "mikla": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": "Mehmet Gürs"
    },
    "nicole": {
        "toques": 3,
        "award": "Yılın Keşfi",
        "city": "Istanbul",
        "chef": None
    },
    "sunset grill & bar": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "sunset grill bar": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "topaz": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "araka": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "nusr-et steakhouse": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": "Nusret Gökçe"
    },
    "nusr-et": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": "Nusret Gökçe"
    },
    "nusret": {
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": "Nusret Gökçe"
    },

    # 2 Toque
    "balıkçı sabahattin": {
        "toques": 2,
        "award": "En İyi Balık Restoranı",
        "city": "Istanbul",
        "chef": None
    },
    "balikci sabahattin": {
        "toques": 2,
        "award": "En İyi Balık Restoranı",
        "city": "Istanbul",
        "chef": None
    },
    "çiya sofrası": {
        "toques": 2,
        "award": "En İyi Geleneksel Mutfak",
        "city": "Istanbul",
        "chef": "Musa Dağdeviren"
    },
    "ciya sofrasi": {
        "toques": 2,
        "award": "En İyi Geleneksel Mutfak",
        "city": "Istanbul",
        "chef": "Musa Dağdeviren"
    },
    "asmalı cavit": {
        "toques": 2,
        "award": "En İyi Meyhane",
        "city": "Istanbul",
        "chef": None
    },
    "asmali cavit": {
        "toques": 2,
        "award": "En İyi Meyhane",
        "city": "Istanbul",
        "chef": None
    },
    "lokanta maya": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": "Didem Şenol"
    },
    "kantin": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": "Şemsa Denizsel"
    },
    "pandeli": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "develi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "hamdi restaurant": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "hamdi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "karaköy lokantası": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "karakoy lokantasi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "beyti": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "köşebaşı": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "kosebasi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "günaydın": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "gunaydin": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "zübeyir ocakbaşı": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "zubeyir ocakbasi": {
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },

    # 1 Toque - Önerilen
    "tarihi sultanahmet köftecisi": {
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Istanbul",
        "chef": None
    },
    "tarihi sultanahmet koftecisi": {
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Istanbul",
        "chef": None
    },
    "sultanahmet köftecisi": {
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Istanbul",
        "chef": None
    },
    "sultanahmet koftecisi": {
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Istanbul",
        "chef": None
    },
    "vefa bozacısı": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "vefa bozacisi": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "karaköy güllüoğlu": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "karakoy gulluoglu": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "hafız mustafa": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "hafiz mustafa": {
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None
    },
    "datça sofrası": {
        "toques": 1,
        "award": None,
        "city": "Datça",
        "chef": None
    },
    "datca sofrasi": {
        "toques": 1,
        "award": None,
        "city": "Datça",
        "chef": None
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
        {toques: int, award: str | None} veya None
    """
    if not venue_name:
        return None

    normalized = normalize_name(venue_name)

    # Tam eşleşme
    if normalized in GAULT_MILLAU_RESTAURANTS:
        info = GAULT_MILLAU_RESTAURANTS[normalized]
        return {
            "toques": info["toques"],
            "award": info.get("award")
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
                    "award": info.get("award")
                }

    return None


def enrich_venue_with_gault_millau(venue: Dict) -> Dict:
    """
    Venue verisine Gault & Millau bilgisi ekle.

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
