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

# Kategori ID eşleştirmeleri (constants.ts'deki ID'ler)
CATEGORY_FINE_DINING = "2"       # Fine Dining
CATEGORY_MEYHANE = "24"          # Meyhane
CATEGORY_BALIKCI = "26"          # Balıkçı
CATEGORY_OCAKBASI = "ocakbasi"   # Ocakbaşı
CATEGORY_KAHVALTI = "4"          # Kahvaltı
CATEGORY_BRUNCH = "25"           # Brunch
CATEGORY_TATLICI = "11"          # Tatlıcı
CATEGORY_ROMANTIK = "1"          # Romantik Akşam
CATEGORY_KEBAP = "14"            # Kebapçı
CATEGORY_SOKAK = "sokak-lezzeti" # Sokak Lezzeti
CATEGORY_BAR = "bar"             # Bar
CATEGORY_LOKANTA = "lokanta"     # Geleneksel Lokanta

# Gault & Millau ödüllü restoranlar
# Her restoran için: name, toques, award, city, chef, instagram, categories
GAULT_MILLAU_RESTAURANTS_LIST: List[Dict] = [
    # ============ 4 TOQUE - EN ÜST SEVİYE ============
    {
        "name": "TURK Fatih Tutak",
        "toques": 4,
        "award": "Yılın Şefi & En İyi Restoran Tasarımı",
        "city": "Istanbul",
        "chef": "Fatih Tutak",
        "instagram": "turkfatihtutak",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_ROMANTIK]
    },
    {
        "name": "Neolokal",
        "toques": 4,
        "award": "En İyi Uluslararası Başarı",
        "city": "Istanbul",
        "chef": "Maksut Aşkar",
        "instagram": "neolokal",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_ROMANTIK]
    },

    # ============ 3 TOQUE - MÜKEMMEL ============
    {
        "name": "Mikla",
        "toques": 3,
        "award": "En İyi Servis",
        "city": "Istanbul",
        "chef": "Mehmet Gürs",
        "instagram": "miklaistanbul",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_ROMANTIK]
    },
    {
        "name": "Nicole",
        "toques": 3,
        "award": "En İyi Tabak Tasarımı",
        "city": "Istanbul",
        "chef": "Serkan Aksoy",
        "instagram": "nicoleistanbul",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_ROMANTIK]
    },
    {
        "name": "Sunset Grill & Bar",
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "sunsetgrillbar",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_ROMANTIK, CATEGORY_BALIKCI]
    },
    {
        "name": "Topaz",
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "topazistanbul",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_ROMANTIK]
    },
    {
        "name": "Araka",
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "arakabogazici",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_ROMANTIK, CATEGORY_BALIKCI]
    },
    {
        "name": "Nusr-Et Steakhouse",
        "toques": 3,
        "award": None,
        "city": "Istanbul",
        "chef": "Nusret Gökçe",
        "instagram": "nusr_et",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_OCAKBASI]
    },
    {
        "name": "OD Urla",
        "toques": 3,
        "award": "Farm to Table (Tarladan Sofraya)",
        "city": "Izmir",
        "chef": "Osman Sezener",
        "instagram": "odurla",
        "categories": [CATEGORY_FINE_DINING]
    },
    {
        "name": "Vino Locale",
        "toques": 3,
        "award": "En İyi Tabak Tasarımı",
        "city": "Istanbul",
        "chef": "Ozan Kumbasar",
        "instagram": "vinolocale",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_ROMANTIK]
    },
    {
        "name": "The Peninsula Istanbul",
        "toques": 3,
        "award": "En İyi Pasta Şefi",
        "city": "Istanbul",
        "chef": "Malte Rohmann",
        "instagram": "thelobbypeninsula",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_BRUNCH]
    },

    # ============ 2 TOQUE - ÇOK İYİ ============
    {
        "name": "Balıkçı Sabahattin",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "balikcisabahattin",
        "categories": [CATEGORY_BALIKCI, CATEGORY_FINE_DINING]
    },
    {
        "name": "Balıkçı Kahraman",
        "toques": 2,
        "award": "En İyi Deniz Restoranı",
        "city": "Muğla",
        "chef": "Kahraman Altun",
        "instagram": "balikcikahraman",
        "categories": [CATEGORY_BALIKCI]
    },
    {
        "name": "Çiya Sofrası",
        "toques": 2,
        "award": "En İyi Geleneksel Mutfak",
        "city": "Istanbul",
        "chef": "Musa Dağdeviren",
        "instagram": "caborestaurants",
        "categories": [CATEGORY_KEBAP, CATEGORY_KAHVALTI, CATEGORY_LOKANTA]
    },
    {
        "name": "Asmalı Cavit",
        "toques": 2,
        "award": "En İyi Meyhane",
        "city": "Istanbul",
        "chef": None,
        "instagram": "asmalicavit",
        "categories": [CATEGORY_MEYHANE]
    },
    {
        "name": "Lokanta Maya",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": "Didem Şenol",
        "instagram": "lokantamaya",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_BRUNCH]
    },
    {
        "name": "Kantin",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": "Şemsa Denizsel",
        "instagram": "kantinistanbul",
        "categories": [CATEGORY_KAHVALTI, CATEGORY_BRUNCH]
    },
    {
        "name": "Pandeli",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "pandeli1901",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_LOKANTA]
    },
    {
        "name": "Develi",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "develirestaurant",
        "categories": [CATEGORY_KEBAP, CATEGORY_OCAKBASI]
    },
    {
        "name": "Hamdi Restaurant",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "hamdirestaurant",
        "categories": [CATEGORY_KEBAP, CATEGORY_OCAKBASI]
    },
    {
        "name": "Karaköy Lokantası",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "karakoylokantasi",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_MEYHANE, CATEGORY_LOKANTA]
    },
    {
        "name": "Beyti",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "beytirestaurant",
        "categories": [CATEGORY_KEBAP, CATEGORY_OCAKBASI]
    },
    {
        "name": "Köşebaşı",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "kosebasiresmi",
        "categories": [CATEGORY_KEBAP, CATEGORY_OCAKBASI]
    },
    {
        "name": "Günaydın",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "gunaydintr",
        "categories": [CATEGORY_KEBAP, CATEGORY_OCAKBASI, CATEGORY_KAHVALTI]
    },
    {
        "name": "Zübeyir Ocakbaşı",
        "toques": 2,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "zubeyirocakbasi",
        "categories": [CATEGORY_OCAKBASI, CATEGORY_KEBAP]
    },
    {
        "name": "Seraf Restaurant",
        "toques": 2,
        "award": "En İyi Geleneksel Lokanta",
        "city": "Istanbul",
        "chef": "Sinem Özler",
        "instagram": "serafrestaurant",
        "categories": [CATEGORY_LOKANTA, CATEGORY_FINE_DINING]
    },
    {
        "name": "Töngül Pide",
        "toques": 2,
        "award": "En İyi Geleneksel Lokanta",
        "city": "Izmir",
        "chef": "Nedime Töngül Akçay",
        "instagram": "tongulpide",
        "categories": [CATEGORY_LOKANTA]
    },
    {
        "name": "Trilye Restaurant",
        "toques": 2,
        "award": "Yılın Lezzet Elçisi",
        "city": "Istanbul",
        "chef": "Süreyya Üzmez",
        "instagram": "trilyerestaurant",
        "categories": [CATEGORY_BALIKCI, CATEGORY_FINE_DINING]
    },
    {
        "name": "Fauna",
        "toques": 2,
        "award": "Yılın Lezzet Elçisi",
        "city": "Istanbul",
        "chef": "İbrahim Tuna",
        "instagram": "faunaistanbul",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_LOKANTA]
    },
    {
        "name": "Teruar Urla",
        "toques": 2,
        "award": "En İyi Sürdürülebilirlik Ödülü",
        "city": "Izmir",
        "chef": "Osman Serdaroğlu",
        "instagram": "teruarurla",
        "categories": [CATEGORY_FINE_DINING]
    },
    {
        "name": "Apartıman Yeniköy",
        "toques": 2,
        "award": "En İyi Sürdürülebilirlik Ödülü",
        "city": "Istanbul",
        "chef": "Burçak Kazdal",
        "instagram": "apartimanyenikoy",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_BRUNCH]
    },
    {
        "name": "Casa Lavanda",
        "toques": 2,
        "award": "En İyi Sürdürülebilirlik Ödülü",
        "city": "Istanbul",
        "chef": "Emre Şen",
        "instagram": "casalavandatr",
        "categories": [CATEGORY_FINE_DINING]
    },
    {
        "name": "Hiç Lokanta",
        "toques": 2,
        "award": "En İyi Sürdürülebilirlik Ödülü",
        "city": "Izmir",
        "chef": "Duygu Özerson Elekdar",
        "instagram": "hiclokanta",
        "categories": [CATEGORY_LOKANTA, CATEGORY_FINE_DINING]
    },
    {
        "name": "Telezzüz",
        "toques": 2,
        "award": "En İyi Sürdürülebilirlik Ödülü",
        "city": "Istanbul",
        "chef": "Bahtiyar Büyükduman",
        "instagram": "telezzuz",
        "categories": [CATEGORY_FINE_DINING]
    },
    {
        "name": "Alaf",
        "toques": 2,
        "award": "Mutfak Kültürü Ödülü",
        "city": "Gaziantep",
        "chef": "Murat Deniz Temel",
        "instagram": "alafgaziantep",
        "categories": [CATEGORY_LOKANTA, CATEGORY_FINE_DINING]
    },
    {
        "name": "Sakhalin İstanbul",
        "toques": 2,
        "award": "Uluslararası Marka Ödülü",
        "city": "Istanbul",
        "chef": "Vladimir Mukhin",
        "instagram": "sakhalinistanbul",
        "categories": [CATEGORY_FINE_DINING]
    },
    # Brunch ödülleri
    {
        "name": "Swissôtel The Bosphorus",
        "toques": 2,
        "award": "En İyi Brunch",
        "city": "Istanbul",
        "chef": "Soner Kesgin",
        "instagram": "swissotelthebosphorus",
        "categories": [CATEGORY_BRUNCH, CATEGORY_FINE_DINING]
    },
    {
        "name": "Four Seasons Bosphorus",
        "toques": 2,
        "award": "En İyi Brunch",
        "city": "Istanbul",
        "chef": "Görkem Özkan",
        "instagram": "fsbosphorus",
        "categories": [CATEGORY_BRUNCH, CATEGORY_FINE_DINING]
    },
    {
        "name": "Çırağan Palace Kempinski",
        "toques": 2,
        "award": "En İyi Brunch & En İyi Banket",
        "city": "Istanbul",
        "chef": "Davut Kutlugün",
        "instagram": "caborestaurants",
        "categories": [CATEGORY_BRUNCH, CATEGORY_FINE_DINING]
    },
    {
        "name": "Hodan",
        "toques": 2,
        "award": "En İyi Brunch",
        "city": "Istanbul",
        "chef": "Çiğdem Seferoğlu",
        "instagram": "hodanistanbul",
        "categories": [CATEGORY_BRUNCH, CATEGORY_KAHVALTI]
    },
    {
        "name": "Çiy Restoran",
        "toques": 2,
        "award": "En İyi Brunch",
        "city": "Izmir",
        "chef": "Damla Uğurtaş",
        "instagram": "ciyrestoran",
        "categories": [CATEGORY_BRUNCH, CATEGORY_KAHVALTI]
    },
    {
        "name": "Lacivert Restoran",
        "toques": 2,
        "award": "En İyi Brunch",
        "city": "Istanbul",
        "chef": "Aslı Günver",
        "instagram": "lacivertrestaurant",
        "categories": [CATEGORY_BRUNCH, CATEGORY_BALIKCI]
    },
    {
        "name": "Divan Kuruçeşme",
        "toques": 2,
        "award": "En İyi Brunch",
        "city": "Istanbul",
        "chef": "Serpil Toptaş",
        "instagram": "divankurucesme",
        "categories": [CATEGORY_BRUNCH]
    },
    {
        "name": "Beca Mutfak",
        "toques": 2,
        "award": "En İyi Brunch",
        "city": "Istanbul",
        "chef": "Cüneyt Açık",
        "instagram": "becamutfak",
        "categories": [CATEGORY_BRUNCH, CATEGORY_KAHVALTI]
    },
    # Yüzyıllık İşletmeler (Onur Ödülü)
    {
        "name": "Hacı Abdullah Lokantası",
        "toques": 2,
        "award": "Yüzyıllık İşletme (Onur Ödülü)",
        "city": "Istanbul",
        "chef": "Abdullah Korun",
        "instagram": "haciabdullah",
        "categories": [CATEGORY_LOKANTA]
    },
    {
        "name": "Şekerci Cafer Erol",
        "toques": 2,
        "award": "Yüzyıllık İşletme (Onur Ödülü)",
        "city": "Istanbul",
        "chef": "Hakan Erol",
        "instagram": "sekercicafererol",
        "categories": [CATEGORY_TATLICI]
    },
    {
        "name": "Beyaz Fırın",
        "toques": 2,
        "award": "Yüzyıllık İşletme (Onur Ödülü)",
        "city": "Istanbul",
        "chef": "Nathalie Stoyanof",
        "instagram": "beyazfirin",
        "categories": [CATEGORY_TATLICI, CATEGORY_KAHVALTI]
    },
    {
        "name": "Yanyalı Fehmi",
        "toques": 2,
        "award": "Yüzyıllık İşletme (Onur Ödülü)",
        "city": "Istanbul",
        "chef": None,
        "instagram": "yanaylifehmi",
        "categories": [CATEGORY_LOKANTA]
    },
    {
        "name": "İmam Çağdaş",
        "toques": 2,
        "award": "Yüzyıllık İşletme (Onur Ödülü)",
        "city": "Gaziantep",
        "chef": "Burhan Çağdaş",
        "instagram": "imamcagdas",
        "categories": [CATEGORY_LOKANTA, CATEGORY_TATLICI]
    },
    # Lezzet Elçileri
    {
        "name": "Nazende",
        "toques": 2,
        "award": "Yılın Lezzet Elçisi",
        "city": "Istanbul",
        "chef": "Uluç Sakarya",
        "instagram": "nazenderestaurant",
        "categories": [CATEGORY_LOKANTA]
    },
    {
        "name": "Yalova Restaurant",
        "toques": 2,
        "award": "Yılın Lezzet Elçisi",
        "city": "Çanakkale",
        "chef": "Ertuğrul Sürgit",
        "instagram": "yalovarestaurant",
        "categories": [CATEGORY_BALIKCI, CATEGORY_LOKANTA]
    },
    # Bar & Miksoloji
    {
        "name": "Frankie",
        "toques": 2,
        "award": "En İyi Bar",
        "city": "Istanbul",
        "chef": "Hakan Özkul",
        "instagram": "frankieistanbul",
        "categories": [CATEGORY_BAR]
    },
    {
        "name": "Maçakızı",
        "toques": 2,
        "award": "En İyi Sommelier",
        "city": "Muğla",
        "chef": "Vincent Lopresto",
        "instagram": "macakizi",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_BAR]
    },
    {
        "name": "Fahri Konsolos",
        "toques": 2,
        "award": "En İyi Miksoloji Mekanı",
        "city": "Istanbul",
        "chef": "Emir Ali Enç",
        "instagram": "fahrikonsolos",
        "categories": [CATEGORY_BAR]
    },
    # Resort & Otel
    {
        "name": "Hillside Beach Club",
        "toques": 2,
        "award": "En İyi Resort Oteli",
        "city": "Muğla",
        "chef": None,
        "instagram": "hillsidebeachclub",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_BRUNCH]
    },
    {
        "name": "Museum Hotel",
        "toques": 2,
        "award": "En İyi Butik Otel",
        "city": "Nevşehir",
        "chef": "Tolga Tosun",
        "instagram": "museumhotelcappadocia",
        "categories": [CATEGORY_FINE_DINING, CATEGORY_BRUNCH]
    },
    {
        "name": "Akra Hotels",
        "toques": 2,
        "award": "En İyi Şehir Oteli F&B",
        "city": "Antalya",
        "chef": "Gökhan Polat",
        "instagram": "akrahotels",
        "categories": [CATEGORY_FINE_DINING]
    },
    {
        "name": "Maxx Royal Resorts",
        "toques": 2,
        "award": "En İyi Resort F&B",
        "city": "Antalya",
        "chef": "Naoki Katori",
        "instagram": "maxxroyalresorts",
        "categories": [CATEGORY_FINE_DINING]
    },

    # ============ 1 TOQUE - İYİ ============
    {
        "name": "Tarihi Sultanahmet Köftecisi",
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "sultanahmetkoftecisi1920",
        "categories": [CATEGORY_SOKAK, CATEGORY_KEBAP]
    },
    {
        "name": "Vefa Bozacısı",
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "vefabozacisi1876",
        "categories": [CATEGORY_TATLICI, CATEGORY_SOKAK]
    },
    {
        "name": "Karaköy Güllüoğlu",
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "karakoygulluoglu",
        "categories": [CATEGORY_TATLICI]
    },
    {
        "name": "Hafız Mustafa",
        "toques": 1,
        "award": None,
        "city": "Istanbul",
        "chef": None,
        "instagram": "hafizmustafa1864",
        "categories": [CATEGORY_TATLICI, CATEGORY_KAHVALTI]
    },
    {
        "name": "Datça Sofrası",
        "toques": 1,
        "award": None,
        "city": "Datça",
        "chef": None,
        "instagram": "datcasofrasi",
        "categories": [CATEGORY_KAHVALTI, CATEGORY_MEYHANE]
    },
    # Sokak Lezzetleri Ödülleri
    {
        "name": "Basta! Street Food Bar",
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Istanbul",
        "chef": "Derin Arıbaş",
        "instagram": "bastastreetfood",
        "categories": [CATEGORY_SOKAK]
    },
    {
        "name": "Kokoreççi Asım Usta",
        "toques": 1,
        "award": "En İyi Sokak Lezzeti",
        "city": "Izmir",
        "chef": "Cihan Yılmaz",
        "instagram": "kokorecciasimusta",
        "categories": [CATEGORY_SOKAK]
    },
    # Patisserie
    {
        "name": "Five O'Clock",
        "toques": 1,
        "award": "En İyi Patisserie Mekanı",
        "city": "Istanbul",
        "chef": "Sinem Ekşioğlu",
        "instagram": "fiveoclockpastry",
        "categories": [CATEGORY_TATLICI, CATEGORY_KAHVALTI]
    },
]

# Türkçe karakter dönüşüm tablosu
TR_CHAR_MAP = {
    'ı': 'i', 'İ': 'i', 'ğ': 'g', 'Ğ': 'g',
    'ü': 'u', 'Ü': 'u', 'ş': 's', 'Ş': 's',
    'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c',
    'â': 'a', 'Â': 'a', 'î': 'i', 'Î': 'i',
}


def normalize_name(name: str) -> str:
    """Restoran adını normalize et (küçük harf, özel karakterler temizle)."""
    if not name:
        return ""

    result = name.lower().strip()
    for tr_char, ascii_char in TR_CHAR_MAP.items():
        result = result.replace(tr_char, ascii_char)

    return result


def get_gault_millau_info(venue_name: str) -> Optional[Dict]:
    """
    Mekan adına göre Gault & Millau bilgisi döndür.

    Args:
        venue_name: Mekan adı

    Returns:
        {toques: int, award: str | None, instagram: str | None, categories: list} veya None
    """
    if not venue_name:
        return None

    normalized = normalize_name(venue_name)

    for restaurant in GAULT_MILLAU_RESTAURANTS_LIST:
        restaurant_normalized = normalize_name(restaurant["name"])

        # Tam eşleşme
        if restaurant_normalized == normalized:
            return {
                "toques": restaurant["toques"],
                "award": restaurant.get("award"),
                "instagram": restaurant.get("instagram"),
                "categories": restaurant.get("categories", [])
            }

        # Kısmi eşleşme (mekan adı içinde arama)
        if len(restaurant_normalized) >= 4:
            if restaurant_normalized in normalized or normalized in restaurant_normalized:
                return {
                    "toques": restaurant["toques"],
                    "award": restaurant.get("award"),
                    "instagram": restaurant.get("instagram"),
                    "categories": restaurant.get("categories", [])
                }

    return None


def get_gm_restaurants_for_category(category_id: str, city: str = None) -> List[Dict]:
    """
    Belirli bir kategori için G&M restoranlarını döndür.

    Args:
        category_id: Kategori ID'si (örn: "24" for Meyhane)
        city: Şehir filtresi (opsiyonel)

    Returns:
        G&M restoran listesi
    """
    results = []

    for restaurant in GAULT_MILLAU_RESTAURANTS_LIST:
        # Kategori eşleşmesi kontrol et
        if category_id in restaurant.get("categories", []):
            # Şehir filtresi varsa uygula
            if city and restaurant.get("city", "").lower() != city.lower():
                continue
            results.append(restaurant)

    # Toque sayısına göre sırala (yüksekten düşüğe)
    results.sort(key=lambda x: x["toques"], reverse=True)

    return results


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


def get_all_gm_restaurants() -> List[Dict]:
    """Tüm G&M restoranlarını döndür."""
    return GAULT_MILLAU_RESTAURANTS_LIST.copy()
