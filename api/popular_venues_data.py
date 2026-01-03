"""
Popüler Mekanlar Instagram Veritabanı

Bu dosya, tüm kategorilerdeki popüler mekanların
Instagram bilgilerini içerir.

Kategoriler:
- Meyhane
- 3. Nesil Kahveci
- Balıkçı
- Ocakbaşı / Kebapçı
- Bar / Kokteyl
- Kahvaltı & Brunch
- Fine Dining
- Sokak Lezzeti
- Tatlıcı / Pastane
"""

from typing import Dict, List, Optional
import sys


# Popüler mekanlar veritabanı
# Key: Mekan adı (küçük harf, normalize edilmiş)
# Value: {instagram: str, city: str, category: str}

POPULAR_VENUES: Dict[str, Dict] = {
    # =====================================================
    # MEYHANE
    # =====================================================
    "asmali cavit": {
        "instagram": "asmalicavit",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "asmalı cavit": {
        "instagram": "asmalicavit",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "iki deniz balık evi": {
        "instagram": "ikidenizbey",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "refik": {
        "instagram": "refikrestaurant",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "yakup 2": {
        "instagram": "yakup2restoran",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "imroz": {
        "instagram": "imrozrestaurant",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "krependeki imroz": {
        "instagram": "imrozrestaurant",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "boncuk": {
        "instagram": "boncukrestaurant",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "boncuk restaurant": {
        "instagram": "boncukrestaurant",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "nevizade": {
        "instagram": "nevizadesokagiresmi",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "cumhuriyet meyhanesi": {
        "instagram": "cumhuriyetmeyhanesi",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "sofyali 9": {
        "instagram": "sofyali9",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "sofyalı 9": {
        "instagram": "sofyali9",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "hala meyhanesi": {
        "instagram": "halameyhanesi",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "meze by lemon tree": {
        "instagram": "mezebylemontree",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "agora meyhanesi": {
        "instagram": "agorameyhanesi",
        "city": "Istanbul",
        "category": "Meyhane"
    },
    "privato cafe": {
        "instagram": "privatocafebistro",
        "city": "Istanbul",
        "category": "Meyhane"
    },

    # =====================================================
    # 3. NESİL KAHVECİ
    # =====================================================
    "kronotrop": {
        "instagram": "kronotropcoffee",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "kronotrop coffee": {
        "instagram": "kronotropcoffee",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "petra roasting co": {
        "instagram": "petraroastingco",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "petra coffee": {
        "instagram": "petraroastingco",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "mitte": {
        "instagram": "mittekahve",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "mitte kahve": {
        "instagram": "mittekahve",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "coffeetopia": {
        "instagram": "coffeetopia",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "coffee sapiens": {
        "instagram": "coffeesapiens",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "mandabatmaz": {
        "instagram": "mandabatmaz",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "brew coffeeworks": {
        "instagram": "brewcoffeeworks",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "form coffee": {
        "instagram": "formcoffee",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "montag coffee roasters": {
        "instagram": "montagcoffee",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "montag": {
        "instagram": "montagcoffee",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "walter's coffee roastery": {
        "instagram": "walterscoffeeroastery",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "walters coffee": {
        "instagram": "walterscoffeeroastery",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "espressolab": {
        "instagram": "espressolab",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "cuppa": {
        "instagram": "cuppacoffee",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "story coffee": {
        "instagram": "storycoffeetr",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "federal coffee": {
        "instagram": "federalcoffee",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "noir coffee": {
        "instagram": "noircoffeetr",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    "twins coffee": {
        "instagram": "twinscoffeeist",
        "city": "Istanbul",
        "category": "3. Nesil Kahveci"
    },
    # İzmir kahveciler
    "dukkan coffee roasters": {
        "instagram": "dukkancoffeeroasters",
        "city": "Izmir",
        "category": "3. Nesil Kahveci"
    },
    "dukkan coffee": {
        "instagram": "dukkancoffeeroasters",
        "city": "Izmir",
        "category": "3. Nesil Kahveci"
    },
    "intro coffee": {
        "instagram": "introcoffeeizmir",
        "city": "Izmir",
        "category": "3. Nesil Kahveci"
    },
    "elk coffee": {
        "instagram": "elkcoffeeroasters",
        "city": "Izmir",
        "category": "3. Nesil Kahveci"
    },
    "elk coffee roasters": {
        "instagram": "elkcoffeeroasters",
        "city": "Izmir",
        "category": "3. Nesil Kahveci"
    },
    # Ankara kahveciler
    "dos amigos": {
        "instagram": "dosamigoscoffee",
        "city": "Ankara",
        "category": "3. Nesil Kahveci"
    },
    "dos amigos coffee": {
        "instagram": "dosamigoscoffee",
        "city": "Ankara",
        "category": "3. Nesil Kahveci"
    },
    "lokum coffee": {
        "instagram": "lokumcoffee",
        "city": "Ankara",
        "category": "3. Nesil Kahveci"
    },

    # =====================================================
    # BALIKÇI
    # =====================================================
    "balikci sabahattin": {
        "instagram": "balikcisabahattin",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "balıkçı sabahattin": {
        "instagram": "balikcisabahattin",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "ismet baba": {
        "instagram": "ismetbabarestaurant",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "kiyi": {
        "instagram": "kiyirestorani",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "kıyı": {
        "instagram": "kiyirestorani",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "kiyi restaurant": {
        "instagram": "kiyirestorani",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "poseidon": {
        "instagram": "poseidonbebek",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "poseidon bebek": {
        "instagram": "poseidonbebek",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "lacivert": {
        "instagram": "lacivertrestaurant",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "sur balik": {
        "instagram": "surbalikrestaurant",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "sur balık": {
        "instagram": "surbalikrestaurant",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "balikci lokantasi": {
        "instagram": "balikcilokantas",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "balıkçı lokantası": {
        "instagram": "balikcilokantas",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "adem baba": {
        "instagram": "adembabarestaurant",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "yosun": {
        "instagram": "yosunrestaurant",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "giritli": {
        "instagram": "giritlirestaurant",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "eftalya balik": {
        "instagram": "eftalyabalik",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "eftalya balık": {
        "instagram": "eftalyabalik",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "feriye": {
        "instagram": "feriyerestaurant",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    "feriye lokantasi": {
        "instagram": "feriyerestaurant",
        "city": "Istanbul",
        "category": "Balıkçı"
    },
    # İzmir balıkçılar
    "deniz restaurant": {
        "instagram": "denizrestaurantizmir",
        "city": "Izmir",
        "category": "Balıkçı"
    },
    "birinci kordon balik": {
        "instagram": "birincikordonbalik",
        "city": "Izmir",
        "category": "Balıkçı"
    },
    "veli usta": {
        "instagram": "veliustabalik",
        "city": "Izmir",
        "category": "Balıkçı"
    },

    # =====================================================
    # OCAKBAŞI / KEBAPÇI
    # =====================================================
    "zubeyir ocakbasi": {
        "instagram": "zubeyirocakbasi",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "zübeyir ocakbaşı": {
        "instagram": "zubeyirocakbasi",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "develi": {
        "instagram": "develirestaurant",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "develi restaurant": {
        "instagram": "develirestaurant",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "hamdi restaurant": {
        "instagram": "hamdirestaurant",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "hamdi": {
        "instagram": "hamdirestaurant",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "kosebasi": {
        "instagram": "kosebasiresmi",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "köşebaşı": {
        "instagram": "kosebasiresmi",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "gunaydin": {
        "instagram": "gunaydintr",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "günaydın": {
        "instagram": "gunaydintr",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "gunaydin kasap steakhouse": {
        "instagram": "gunaydintr",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "beyti": {
        "instagram": "beytirestaurant",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "adana ocakbasi": {
        "instagram": "adanaocakbasi",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "ali ocakbasi": {
        "instagram": "aliocakbasitr",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "ali ocakbaşı": {
        "instagram": "aliocakbasitr",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "haci baba": {
        "instagram": "hacibabakebap",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "hacı baba": {
        "instagram": "hacibabakebap",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "nusr-et": {
        "instagram": "nuaborj",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "nusret": {
        "instagram": "nuaborj",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },
    "nusr-et steakhouse": {
        "instagram": "nuaborj",
        "city": "Istanbul",
        "category": "Ocakbaşı"
    },

    # =====================================================
    # BAR / KOKTEYL
    # =====================================================
    "balkon bar": {
        "instagram": "balkon.bar",
        "city": "Istanbul",
        "category": "Bar"
    },
    "under": {
        "instagram": "underkarakoy",
        "city": "Istanbul",
        "category": "Bar"
    },
    "under karakoy": {
        "instagram": "underkarakoy",
        "city": "Istanbul",
        "category": "Bar"
    },
    "lucca": {
        "instagram": "luccaistanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "lucca bebek": {
        "instagram": "luccaistanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "360 istanbul": {
        "instagram": "360istanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "360": {
        "instagram": "360istanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "anjelique": {
        "instagram": "anjeliqueistanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "reina": {
        "instagram": "reinaistanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "sortie": {
        "instagram": "sortieclub",
        "city": "Istanbul",
        "category": "Bar"
    },
    "alexandra cocktail bar": {
        "instagram": "alexandracocktailbar",
        "city": "Istanbul",
        "category": "Bar"
    },
    "frankie istanbul": {
        "instagram": "frankieistanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "frankie": {
        "instagram": "frankieistanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "mikla bar": {
        "instagram": "miklaistanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "5.kat": {
        "instagram": "5katcihangir",
        "city": "Istanbul",
        "category": "Bar"
    },
    "5. kat": {
        "instagram": "5katcihangir",
        "city": "Istanbul",
        "category": "Bar"
    },
    "gizli kalsın": {
        "instagram": "gizlikalsinbar",
        "city": "Istanbul",
        "category": "Bar"
    },
    "gizli kalsin": {
        "instagram": "gizlikalsinbar",
        "city": "Istanbul",
        "category": "Bar"
    },
    "babylon": {
        "instagram": "babylonistanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "kiki karakoy": {
        "instagram": "kikikarakoy",
        "city": "Istanbul",
        "category": "Bar"
    },
    "kiki": {
        "instagram": "kikikarakoy",
        "city": "Istanbul",
        "category": "Bar"
    },
    "ritim istanbul": {
        "instagram": "ritim.istanbul",
        "city": "Istanbul",
        "category": "Bar"
    },
    "nuteras": {
        "instagram": "nuterasbebek",
        "city": "Istanbul",
        "category": "Bar"
    },
    "nu teras": {
        "instagram": "nuterasbebek",
        "city": "Istanbul",
        "category": "Bar"
    },

    # =====================================================
    # KAHVALTI & BRUNCH
    # =====================================================
    "van kahvalti evi": {
        "instagram": "vankahvaltievi",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "van kahvaltı evi": {
        "instagram": "vankahvaltievi",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "namlı gurme": {
        "instagram": "namligurme",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "namli gurme": {
        "instagram": "namligurme",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "cafe privato": {
        "instagram": "cafeprivato",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "fenerbahce kahvaltisi": {
        "instagram": "fenerbahcekahvaltisi",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "vogue restaurant": {
        "instagram": "vogueistanbul",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "journey cihangir": {
        "instagram": "journeycihangir",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "journey": {
        "instagram": "journeycihangir",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "sade kahve": {
        "instagram": "sadekahve",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "suada": {
        "instagram": "suadaclub",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "sait halim pasa yalisi": {
        "instagram": "saithalimp",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "sait halim paşa yalısı": {
        "instagram": "saithalimp",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "the house cafe": {
        "instagram": "thehousecafe",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "house cafe": {
        "instagram": "thehousecafe",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "gram": {
        "instagram": "gramistanbul",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "kahve dunyasi": {
        "instagram": "kahvedunyasitr",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },
    "kahve dünyası": {
        "instagram": "kahvedunyasitr",
        "city": "Istanbul",
        "category": "Kahvaltı"
    },

    # =====================================================
    # FINE DINING
    # =====================================================
    "mikla": {
        "instagram": "miklaistanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "neolokal": {
        "instagram": "neolokal",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "turk fatih tutak": {
        "instagram": "turkfatihtutak",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "türk fatih tutak": {
        "instagram": "turkfatihtutak",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "turk": {
        "instagram": "turkfatihtutak",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "türk": {
        "instagram": "turkfatihtutak",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "nicole": {
        "instagram": "nicoleistanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "nicole restaurant": {
        "instagram": "nicoleistanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "sunset grill & bar": {
        "instagram": "sunsetgrillbar",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "sunset grill": {
        "instagram": "sunsetgrillbar",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "araka": {
        "instagram": "arakabogazici",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "topaz": {
        "instagram": "topazistanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "paper moon": {
        "instagram": "papermoonistanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "ulus 29": {
        "instagram": "ulus29",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "spago": {
        "instagram": "spago.istanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "zuma istanbul": {
        "instagram": "zumaistanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "zuma": {
        "instagram": "zumaistanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "murver": {
        "instagram": "murveristanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "mürver": {
        "instagram": "murveristanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "arkestra": {
        "instagram": "arkestra_istanbul",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "esme": {
        "instagram": "esmerestaurant",
        "city": "Istanbul",
        "category": "Fine Dining"
    },
    "esmae": {
        "instagram": "esmerestaurant",
        "city": "Istanbul",
        "category": "Fine Dining"
    },

    # =====================================================
    # SOKAK LEZZETİ
    # =====================================================
    "sultanahmet koftecisi": {
        "instagram": "sultanahmetkoftecisi1920",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "sultanahmet köftecisi": {
        "instagram": "sultanahmetkoftecisi1920",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "tarihi sultanahmet koftecisi": {
        "instagram": "sultanahmetkoftecisi1920",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "tarihi sultanahmet köftecisi": {
        "instagram": "sultanahmetkoftecisi1920",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "durumcu emmi": {
        "instagram": "durumcuemmi",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "meşhur dondurmacı ali usta": {
        "instagram": "meshurdondurmaciali",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "meshur dondurmaci ali usta": {
        "instagram": "meshurdondurmaciali",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "karakoy gulluoglu": {
        "instagram": "karakoygulluoglu",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "karaköy güllüoğlu": {
        "instagram": "karakoygulluoglu",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "ciya sofrasi": {
        "instagram": "caborestaurants",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "çiya sofrası": {
        "instagram": "caborestaurants",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "balık ekmek eminonu": {
        "instagram": "balikekmekkoprusu",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "balik ekmek eminonu": {
        "instagram": "balikekmekkoprusu",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "kumpir besiktas": {
        "instagram": "kumpirbesiktas",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "ortakoy kumpir": {
        "instagram": "ortakoykumpir",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "ortaköy kumpir": {
        "instagram": "ortakoykumpir",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },
    "midyeci ahmet": {
        "instagram": "midyeciahmet",
        "city": "Istanbul",
        "category": "Sokak Lezzeti"
    },

    # =====================================================
    # TATLICI / PASTANE
    # =====================================================
    "hafiz mustafa": {
        "instagram": "hafizmustafa1864",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "hafız mustafa": {
        "instagram": "hafizmustafa1864",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "gulluoglu": {
        "instagram": "karakoygulluoglu",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "güllüoğlu": {
        "instagram": "karakoygulluoglu",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "faruk gulluoglu": {
        "instagram": "farukgulluoglu",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "mado": {
        "instagram": "madotr",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "saray muhallebicisi": {
        "instagram": "saraymuhallebicisi",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "vefa bozacisi": {
        "instagram": "vefabozacisi1876",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "vefa bozacısı": {
        "instagram": "vefabozacisi1876",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "saray": {
        "instagram": "saraymuhallebicisi",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "baylan pastanesi": {
        "instagram": "baylanpastanesi",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "baylan": {
        "instagram": "baylanpastanesi",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "inci pastanesi": {
        "instagram": "incipastanesi",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "inci": {
        "instagram": "incipastanesi",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "pelit": {
        "instagram": "pelitpastaneleri",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "pelit pastanesi": {
        "instagram": "pelitpastaneleri",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "sutis": {
        "instagram": "sutis",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "sütis": {
        "instagram": "sutis",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "sekerci cafer erol": {
        "instagram": "sekercicafererol",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },
    "şekerci cafer erol": {
        "instagram": "sekercicafererol",
        "city": "Istanbul",
        "category": "Tatlıcı"
    },

    # =====================================================
    # GELENEKSEL / EV YEMEKLERİ
    # =====================================================
    "lokanta maya": {
        "instagram": "lokantamaya",
        "city": "Istanbul",
        "category": "Ev Yemekleri"
    },
    "kantin": {
        "instagram": "kantinistanbul",
        "city": "Istanbul",
        "category": "Ev Yemekleri"
    },
    "karakoy lokantasi": {
        "instagram": "karakoylokantasi",
        "city": "Istanbul",
        "category": "Ev Yemekleri"
    },
    "karaköy lokantası": {
        "instagram": "karakoylokantasi",
        "city": "Istanbul",
        "category": "Ev Yemekleri"
    },
    "pandeli": {
        "instagram": "pandeli1901",
        "city": "Istanbul",
        "category": "Ev Yemekleri"
    },
    "yeni lokanta": {
        "instagram": "yenilokanta",
        "city": "Istanbul",
        "category": "Ev Yemekleri"
    },
    "aheste": {
        "instagram": "ahesteistanbul",
        "city": "Istanbul",
        "category": "Ev Yemekleri"
    },
    "ficcin": {
        "instagram": "ficcinistanbul",
        "city": "Istanbul",
        "category": "Ev Yemekleri"
    },
    "fiççin": {
        "instagram": "ficcinistanbul",
        "city": "Istanbul",
        "category": "Ev Yemekleri"
    },
    "datca sofrasi": {
        "instagram": "datcasofrasi",
        "city": "Datca",
        "category": "Ev Yemekleri"
    },
    "datça sofrası": {
        "instagram": "datcasofrasi",
        "city": "Datca",
        "category": "Ev Yemekleri"
    },
}


def normalize_venue_name(name: str) -> str:
    """Mekan adını normalize et (küçük harf, özel karakterler temizle)."""
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


def get_venue_instagram(venue_name: str) -> Optional[str]:
    """
    Mekan adına göre Instagram username'i döndür.

    Args:
        venue_name: Mekan adı

    Returns:
        Instagram username veya None
    """
    if not venue_name:
        return None

    normalized = normalize_venue_name(venue_name)

    # Tam eşleşme
    if normalized in POPULAR_VENUES:
        return POPULAR_VENUES[normalized].get("instagram")

    # Kısmi eşleşme (mekan adı içinde arama)
    for key, info in POPULAR_VENUES.items():
        # Hem key'in normalized name içinde olup olmadığını
        # hem de normalized name'in key içinde olup olmadığını kontrol et
        if key in normalized or normalized in key:
            # Minimum 4 karakter eşleşmesi olmalı
            if len(key) >= 4:
                return info.get("instagram")

    return None


def enrich_venue_with_instagram(
    venue: Dict,
    city: str = None,
    district: str = None,
    neighborhood: str = None
) -> Dict:
    """
    Venue verisine Instagram URL'si ekle (eğer yoksa).
    Önce statik sözlükten bakar, bulamazsa Google CSE ile arar.

    Args:
        venue: Venue dictionary
        city: Şehir adı (Google CSE için)
        district: İlçe adı (Google CSE için)
        neighborhood: Mahalle adı (Google CSE için)

    Returns:
        Güncellenmiş venue dictionary
    """
    if not venue:
        return venue

    # Zaten Instagram URL'si varsa dokunma
    existing_instagram = venue.get("instagramUrl", "")
    if existing_instagram and "instagram.com/" in existing_instagram:
        return venue

    name = venue.get("name", "")

    # 1. Önce statik sözlükten kontrol et (hızlı)
    instagram_handle = get_venue_instagram(name)
    if instagram_handle:
        venue["instagramUrl"] = f"https://instagram.com/{instagram_handle}"
        return venue

    # 2. Statik sözlükte yoksa Google CSE ile ara
    if city:
        try:
            from .instagram_service import discover_instagram_url
            instagram_url = discover_instagram_url(
                venue_name=name,
                city=city,
                website=venue.get("website"),
                existing_instagram=existing_instagram if existing_instagram else None,
                district=district,
                neighborhood=neighborhood
            )
            if instagram_url:
                venue["instagramUrl"] = instagram_url
                print(f"🔗 INSTAGRAM ENRICH (Google CSE) - {name}: {instagram_url}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"⚠️ INSTAGRAM ENRICH error for {name}: {e}", file=sys.stderr, flush=True)

    return venue


def enrich_venues_with_instagram(
    venues: List[Dict],
    city: str = None,
    district: str = None,
    neighborhood: str = None
) -> List[Dict]:
    """
    Birden fazla venue'ya Instagram URL'si ekle.
    Google CSE ile arama yapar.

    Args:
        venues: Venue listesi
        city: Şehir adı
        district: İlçe adı
        neighborhood: Mahalle adı

    Returns:
        Güncellenmiş venue listesi
    """
    enriched_count = 0
    for venue in venues:
        old_instagram = venue.get("instagramUrl", "")
        enrich_venue_with_instagram(venue, city, district, neighborhood)
        if venue.get("instagramUrl") and venue.get("instagramUrl") != old_instagram:
            enriched_count += 1

    if enriched_count > 0:
        print(f"✨ INSTAGRAM BATCH ENRICH - {enriched_count}/{len(venues)} venue zenginleştirildi", file=sys.stderr, flush=True)

    return venues
