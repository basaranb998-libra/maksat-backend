"""
Istanbul, Izmir ve Muğla ilçe ve semt verileri.
Bu veriler venue aramalari icin lokasyon filtrelemede kullanilir.
"""

LOCATION_DATA = {
    "istanbul": {
        "ilceler": [
            {
                "isim": "Kadıköy",
                "semtler": ["Moda", "Caferağa", "Yeldeğirmeni", "Bahariye", "Rasimpaşa", "Osmanağa", "Fenerbahçe", "Caddebostan", "Suadiye", "Bostancı", "Kozyatağı", "Göztepe"]
            },
            {
                "isim": "Beşiktaş",
                "semtler": ["Bebek", "Arnavutköy", "Ortaköy", "Kuruçeşme", "Etiler", "Levent", "Akatlar", "Ulus", "Yıldız", "Sinanpaşa", "Abbasağa"]
            },
            {
                "isim": "Beyoğlu",
                "semtler": ["Taksim", "Cihangir", "Galata", "Karaköy", "Asmalımescit", "Çukurcuma", "Tophane", "Tarlabaşı", "Dolapdere", "Kasımpaşa"]
            },
            {
                "isim": "Sarıyer",
                "semtler": ["Emirgan", "İstinye", "Tarabya", "Yeniköy", "Rumelihisarı", "Baltalimanı", "Maslak", "Zekeriyaköy", "Bahçeköy"]
            },
            {
                "isim": "Şişli",
                "semtler": ["Nişantaşı", "Teşvikiye", "Harbiye", "Osmanbey", "Kurtuluş", "Bomonti", "Feriköy", "Mecidiyeköy", "Fulya", "Esentepe"]
            },
            {
                "isim": "Üsküdar",
                "semtler": ["Çengelköy", "Kuzguncuk", "Beylerbeyi", "Kandilli", "Vaniköy", "Salacak", "Üsküdar Merkez", "Acıbadem", "Altunizade", "Kısıklı"]
            },
            {
                "isim": "Beykoz",
                "semtler": ["Anadoluhisarı", "Kanlıca", "Paşabahçe", "Beykoz Merkez", "Çubuklu", "Riva", "Polonezköy"]
            },
            {
                "isim": "Fatih",
                "semtler": ["Sultanahmet", "Eminönü", "Sirkeci", "Balat", "Fener", "Cibali", "Kumkapı", "Aksaray", "Laleli", "Çarşamba", "Vefa"]
            },
            {
                "isim": "Bakırköy",
                "semtler": ["Ataköy", "Yeşilköy", "Florya", "Yeşilyurt", "Bakırköy Merkez", "Zuhuratbaba", "Osmaniye"]
            },
            {
                "isim": "Adalar",
                "semtler": ["Büyükada", "Heybeliada", "Burgazada", "Kınalıada"]
            },
            {
                "isim": "Ataşehir",
                "semtler": ["Barbaros", "İçerenköy", "Küçükbakkalköy", "Ataşehir Merkez", "Batı Ataşehir"]
            },
            {
                "isim": "Maltepe",
                "semtler": ["Bağlarbaşı", "Altıntepe", "Cevizli", "İdealtepe", "Küçükyalı", "Dragos"]
            },
            {
                "isim": "Kartal",
                "semtler": ["Kartal Merkez", "Soğanlık", "Uğur Mumcu", "Kordonboyu"]
            },
            {
                "isim": "Zeytinburnu",
                "semtler": ["Kazlıçeşme", "Veliefendi", "Merkezefendi", "Beştelsiz"]
            }
        ]
    },
    "izmir": {
        "ilceler": [
            {
                "isim": "Konak",
                "semtler": ["Alsancak", "Kordon", "Kemeraltı", "Göztepe", "Güzelyalı", "Hatay", "Basmane", "Konak Merkez", "Küçükyalı", "Eşrefpaşa", "Karantina", "Agora"]
            },
            {
                "isim": "Karşıyaka",
                "semtler": ["Bostanlı", "Mavişehir", "Alaybey", "Soğukkuyu", "Tersane", "Yalı", "Donanmacı", "Çarşı", "Nergiz"]
            },
            {
                "isim": "Bornova",
                "semtler": ["Merkez", "Küçükpark", "Altındağ", "Ergene", "Evka-3", "Kazımdirik"]
            },
            {
                "isim": "Bayraklı",
                "semtler": ["Manavkuyu", "Turan", "Salhane", "Bayraklı Merkez", "Adalet", "Mansuroğlu"]
            },
            {
                "isim": "Çeşme",
                "semtler": ["Alaçatı", "Dalyan", "Ilıca", "Çiftlikköy", "Ovacık", "Çeşme Merkez", "Reisdere"]
            },
            {
                "isim": "Urla",
                "semtler": ["Merkez", "İskele", "Zeytinalanı", "Özbek", "Barbaros", "Yağcılar", "Kuşçular"]
            },
            {
                "isim": "Seferihisar",
                "semtler": ["Sığacık", "Merkez", "Ürkmez", "Doğanbey", "Payamlı"]
            },
            {
                "isim": "Foça",
                "semtler": ["Eski Foça", "Yeni Foça", "Kozbeyli", "Bağarası"]
            },
            {
                "isim": "Güzelbahçe",
                "semtler": ["Kahramandere", "Yalı", "Yelki", "Güzelbahçe Merkez", "Çamlı"]
            },
            {
                "isim": "Narlıdere",
                "semtler": ["Sahil", "Merkez", "Çatalkaya", "Narlı"]
            },
            {
                "isim": "Balçova",
                "semtler": ["Merkez", "İnciraltı", "Onur", "Çetin Emeç", "Teleferik"]
            },
            {
                "isim": "Gaziemir",
                "semtler": ["Merkez", "Sarnıç", "Atıfbey", "Gazi", "Yeşil"]
            },
            {
                "isim": "Buca",
                "semtler": ["Şirinyer", "Merkez", "Adatepe", "Tinaztepe", "Kaynaklar", "Kozağaç"]
            },
            {
                "isim": "Çiğli",
                "semtler": ["Sasalı", "Merkez", "Evka-2", "Balatçık", "Köyiçi"]
            },
            {
                "isim": "Menderes",
                "semtler": ["Gümüldür", "Özdere", "Cumaovası", "Merkez", "Değirmendere"]
            },
            {
                "isim": "Dikili",
                "semtler": ["Merkez", "Bademli", "Çandarlı", "Salihleraltı", "Kabakum"]
            },
            {
                "isim": "Karaburun",
                "semtler": ["Mordoğan", "Merkez", "Küçükbahçe", "Saip", "Balıklıova"]
            }
        ]
    },
    "mugla": {
        "ilceler": [
            {
                "isim": "Bodrum",
                "semtler": ["Bodrum Merkez", "Gümbet", "Bitez", "Ortakent", "Yahşi", "Türkbükü", "Gölköy", "Yalıkavak", "Gündoğan", "Torba", "Güvercinlik", "Turgutreis"]
            },
            {
                "isim": "Marmaris",
                "semtler": ["Marmaris Merkez", "İçmeler", "Armutalan", "Siteler", "Beldibi", "Turunç", "Selimiye", "Bozburun", "Söğüt"]
            },
            {
                "isim": "Fethiye",
                "semtler": ["Fethiye Merkez", "Çalış", "Hisarönü", "Ölüdeniz", "Ovacık", "Kayaköy", "Karagözler", "Göcek", "Taşyaka"]
            },
            {
                "isim": "Datça",
                "semtler": ["Datça Merkez", "İskele", "Reşadiye", "Mesudiye", "Palamutbükü", "Kızlan"]
            },
            {
                "isim": "Köyceğiz",
                "semtler": ["Köyceğiz Merkez", "Dalyan", "Toparlar", "Ekincik", "Sultaniye"]
            },
            {
                "isim": "Dalaman",
                "semtler": ["Dalaman Merkez", "Sarıgerme", "Kapıkargın"]
            },
            {
                "isim": "Ortaca",
                "semtler": ["Ortaca Merkez", "Dalyan", "Okçular"]
            },
            {
                "isim": "Ula",
                "semtler": ["Ula Merkez", "Akyaka", "Gökova"]
            },
            {
                "isim": "Milas",
                "semtler": ["Milas Merkez", "Güllük", "Ören", "Bafa", "Kıyıkışlacık"]
            },
            {
                "isim": "Menteşe",
                "semtler": ["Muğla Merkez", "Karabağlar", "Yeşilyurt", "Akçaova", "Emirbeyazıt"]
            },
            {
                "isim": "Seydikemer",
                "semtler": ["Kemer", "Eşen", "Üzümlü", "Saklıkent"]
            }
        ]
    }
}


def get_districts_for_city(city: str) -> list:
    """Belirtilen şehir için ilçe listesini döndür."""
    city_key = city.lower().replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")

    # Şehir ismi eşleştirmesi
    city_mapping = {
        "istanbul": "istanbul",
        "izmir": "izmir",
        "mugla": "mugla",
        "muğla": "mugla",
        "bodrum": "mugla",
        "marmaris": "mugla",
        "fethiye": "mugla",
        "datca": "mugla",
        "datça": "mugla",
    }

    normalized_city = city_mapping.get(city_key, city_key)
    city_data = LOCATION_DATA.get(normalized_city)

    if city_data:
        return [ilce["isim"] for ilce in city_data["ilceler"]]
    return []


def get_neighborhoods_for_district(city: str, district: str) -> list:
    """Belirtilen ilçe için semt listesini döndür."""
    city_key = city.lower().replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")

    city_mapping = {
        "istanbul": "istanbul",
        "izmir": "izmir",
        "mugla": "mugla",
        "muğla": "mugla",
        "bodrum": "mugla",
        "marmaris": "mugla",
        "fethiye": "mugla",
        "datca": "mugla",
        "datça": "mugla",
    }

    normalized_city = city_mapping.get(city_key, city_key)
    city_data = LOCATION_DATA.get(normalized_city)

    if city_data:
        for ilce in city_data["ilceler"]:
            if ilce["isim"].lower() == district.lower():
                return ilce["semtler"]
    return []


def get_all_neighborhoods_for_city(city: str) -> list:
    """Belirtilen şehirdeki tüm semtleri döndür."""
    city_key = city.lower().replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")

    city_mapping = {
        "istanbul": "istanbul",
        "izmir": "izmir",
        "mugla": "mugla",
        "muğla": "mugla",
    }

    normalized_city = city_mapping.get(city_key, city_key)
    city_data = LOCATION_DATA.get(normalized_city)

    neighborhoods = []
    if city_data:
        for ilce in city_data["ilceler"]:
            neighborhoods.extend(ilce["semtler"])
    return neighborhoods


def find_district_by_neighborhood(city: str, neighborhood: str) -> str:
    """Semt adından ilçeyi bul."""
    city_key = city.lower().replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")

    city_mapping = {
        "istanbul": "istanbul",
        "izmir": "izmir",
        "mugla": "mugla",
        "muğla": "mugla",
    }

    normalized_city = city_mapping.get(city_key, city_key)
    city_data = LOCATION_DATA.get(normalized_city)

    if city_data:
        neighborhood_lower = neighborhood.lower()
        for ilce in city_data["ilceler"]:
            for semt in ilce["semtler"]:
                if semt.lower() == neighborhood_lower:
                    return ilce["isim"]
    return ""
