import requests

headers = {"Api-Key": "gz8snlIu--mUbwcNBlW7n3BxhyWJNnP3kTvVHCOFA9ln3L9E5fMsiXoPUIis47wpfpIy_hCArxyuG57LmTCT0-"}

all_units = []
offset = 0
while True:
    r = requests.get(f"https://o.applovin.com/mediation/v1/ad_units?fields=ad_network_settings&limit=100&offset={offset}", headers=headers)
    data = r.json()
    if not data:
        break
    all_units.extend(data)
    if len(data) < 100:
        break
    offset += 100

for unit in all_units:
    if "MJP" in unit["name"] and ("Int" in unit["name"] or "RV" in unit["name"] or "int" in unit["name"] or "rv" in unit["name"]):
        print(f"\n=== {unit['name']} ===")
        for n in unit.get("ad_network_settings", []):
            for key, val in n.items():
                units = val.get("ad_network_ad_units", [])
                if units:
                    print(f"  {key}: {len(units)} entry")