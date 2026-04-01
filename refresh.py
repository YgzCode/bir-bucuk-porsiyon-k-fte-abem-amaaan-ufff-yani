import requests
import json
import re
from datetime import datetime

# ============================================================
# YAPILANDIRMA — sadece burası değişir
# ============================================================
MANAGEMENT_KEY = "e0757bd737fa69c9d7c8dea73f3e4d57bc403d2a557073180b8e3a938d773465e7759b6c89fb89297e66d2"
PUBLISHER_TAG  = "thegameops"   # AdsYield'e ait GAM entry'leri tanımlayan string
FIND_STRING    = "_v1_"       # değiştirilecek token
REPLACE_STRING =  "_v2_" # yeni token
DRY_RUN        = False         # True = sadece önizle, hiçbir şey yazma
# ============================================================

BASE_URL = "https://o.applovin.com/mediation/v1"
HEADERS  = {
    "Api-Key": MANAGEMENT_KEY,
    "Content-Type": "application/json"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_all_ad_units():
    """Tüm ad unit'leri çek (pagination ile)"""
    all_units = []
    limit  = 100
    offset = 0
    while True:
        url = f"{BASE_URL}/ad_units?fields=ad_network_settings&limit={limit}&offset={offset}"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            log(f"HATA: ad_units çekilemedi — {r.status_code} {r.text[:200]}")
            break
        data = r.json()
        if not data:
            break
        all_units.extend(data)
        log(f"{len(all_units)} ad unit çekildi...")
        if len(data) < limit:
            break
        offset += limit
    return all_units

def find_adsyield_gam_entries(ad_unit):
    """Bir ad unit içinde AdsYield'e ait GAM entry'lerini bul"""
    results = []
    for network_obj in ad_unit.get("ad_network_settings", []):
        for network_name, config in network_obj.items():
            if network_name != "GOOGLE_AD_MANAGER_NETWORK":
                continue
            for unit in config.get("ad_network_ad_units", []):
                unit_id = unit.get("ad_network_ad_unit_id", "")
                if PUBLISHER_TAG in unit_id:
                    match = re.search(re.escape(FIND_STRING), unit_id)
                    if match:
                        new_id = re.sub(re.escape(FIND_STRING), REPLACE_STRING, unit_id, count=1)
                        results.append({
                            "network_name": network_name,
                            "old_id": unit_id,
                            "new_id": new_id
                        })
    return results

def apply_refresh(ad_unit, matches):
    """Değişikliği uygula — sadece GAM entry'lerini güncelle"""
    # ad_network_settings içinde ilgili entry'leri değiştir
    for network_obj in ad_unit.get("ad_network_settings", []):
        for network_name, config in network_obj.items():
            if network_name != "GOOGLE_AD_MANAGER_NETWORK":
                continue
            for unit in config.get("ad_network_ad_units", []):
                unit_id = unit.get("ad_network_ad_unit_id", "")
                if PUBLISHER_TAG in unit_id and FIND_STRING in unit_id:
                    unit["ad_network_ad_unit_id"] = re.sub(re.escape(FIND_STRING), REPLACE_STRING, unit_id, count=1)

    # POST için gerekli body
    body = {
        "id":                   ad_unit["id"],
        "name":                 ad_unit["name"],
        "platform":             ad_unit["platform"],
        "ad_format":            ad_unit["ad_format"],
        "package_name":         ad_unit["package_name"],
        "has_active_experiment": ad_unit.get("has_active_experiment", False),
        "disabled":             ad_unit.get("disabled", False),
        "ad_network_settings":  ad_unit["ad_network_settings"]
    }

    url = f"{BASE_URL}/ad_unit/{ad_unit['id']}"
    r = requests.post(url, headers=HEADERS, json=body)
    return r.status_code, r.text

def verify(ad_unit_id, expected_new_id):
    """Write sonrası GET ile doğrula"""
    url = f"{BASE_URL}/ad_unit/{ad_unit_id}?fields=ad_network_settings"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return False
    data = r.json()
    for network_obj in data.get("ad_network_settings", []):
        for network_name, config in network_obj.items():
            if network_name != "GOOGLE_AD_MANAGER_NETWORK":
                continue
            for unit in config.get("ad_network_ad_units", []):
                if unit.get("ad_network_ad_unit_id") == expected_new_id:
                    return True
    return False

def main():
    mode = "DRY-RUN" if DRY_RUN else "CANLI"
    log(f"=== Adsyield Refresh Tool başladı [{mode}] ===")
    log(f"Publisher tag : {PUBLISHER_TAG}")
    log(f"Find          : {FIND_STRING}")
    log(f"Replace       : {REPLACE_STRING}")
    print()

    # 1. Tüm ad unit'leri çek
    ad_units = get_all_ad_units()
    log(f"Toplam {len(ad_units)} ad unit bulundu")
    print()

    # 2. Her ad unit'i tara
    total_found   = 0
    total_success = 0
    total_fail    = 0
    total_skip    = 0

    for ad_unit in ad_units:
        matches = find_adsyield_gam_entries(ad_unit)

        if not matches:
            total_skip += 1
            continue

        total_found += len(matches)
        log(f"AD UNIT: {ad_unit['name']} ({ad_unit['id']})")
        for m in matches:
            log(f"  BULUNDU → {m['old_id']}")
            log(f"  YENİ    → {m['new_id']}")

        if DRY_RUN:
            log(f"  [DRY-RUN] Yazılmadı — önizleme modu aktif")
            print()
            continue

        # 3. Uygula
        status_code, response_text = apply_refresh(ad_unit, matches)
        if status_code == 200:
            # 4. Doğrula
            verified = verify(ad_unit["id"], matches[0]["new_id"])
            if verified:
                log(f"  ✅ BAŞARILI + DOĞRULANDI")
                total_success += len(matches)
            else:
                log(f"  ⚠️  POST 200 ama doğrulama başarısız!")
                total_fail += len(matches)
        else:
            log(f"  ❌ HATA: {status_code} — {response_text[:200]}")
            total_fail += len(matches)
        print()

    # 5. Özet
    print()
    log("=== ÖZET ===")
    log(f"Taranan ad unit : {len(ad_units)}")
    log(f"Eşleşme bulundu : {total_found}")
    if not DRY_RUN:
        log(f"Başarılı        : {total_success}")
        log(f"Başarısız       : {total_fail}")
    log(f"Atlanan         : {total_skip} (AdsYield pattern yok)")

if __name__ == "__main__":
    main()