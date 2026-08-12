import os
import re
import csv
import time
import requests
from collections import Counter

CDX_URL = "https://web.archive.org/cdx/search/cdx"
INDEX_FILE = "data/history/index.csv"

def main():
    # Si el censo ya existe, no lo volvemos a descargar (ahorra tiempo cada noche)
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, encoding="utf-8") as f:
            n = sum(1 for _ in f) - 1
        print(f"📚 El censo histórico ya existe ({n} resoluciones). Saltando descarga.")
        return

    print("🌍 Consultando el archivo histórico de Wayback Machine (gratis)...")
    params = {
        "url": "aepd.es/documento/*.pdf",
        "output": "json",
        "fl": "original,timestamp",
        "collapse": "urlkey",
        "filter": "statuscode:200",
    }

    rows = None
    for intento in range(2):  # Un reintento por si archive.org está perezoso
        try:
            r = requests.get(CDX_URL, params=params, timeout=600)
            r.raise_for_status()
            rows = r.json()
            break
        except Exception as e:
            print(f"⚠️ Intento {intento+1} falló: {e}. Esperando 10s...")
            time.sleep(10)

    if rows is None:
        print("❌ No se pudo consultar Wayback Machine.")
        return

    if rows and rows[0] == ["original", "timestamp"]:
        rows = rows[1:]
    print(f"🔎 Wayback conoce {len(rows)} URLs únicas de documentos AEPD.")

    # Deduplicar y extraer el año del nombre del archivo (ej. ps-00415-2024.pdf)
    seen = {}
    for original, timestamp in rows:
        original = original.strip()
        if not original.lower().endswith(".pdf"):
            continue
        m = re.search(r"(\d{4})\.pdf$", original)
        year = int(m.group(1)) if m else 0
        if year and (year < 2016 or year > 2100):
            continue  # Solo nos interesa 2016 en adelante
        key = original.lower()
        if key not in seen or timestamp > seen[key][0]:
            seen[key] = (timestamp, original, year)

    entries = []
    for timestamp, original, year in seen.values():
        filename = original.rstrip("/").split("/")[-1]
        entries.append({
            "id": filename[:-4],
            "year": year if year else 9999,
            "url_live": original,
            "url_wayback": f"https://web.archive.org/web/{timestamp}id_/{original}",
        })

    entries.sort(key=lambda e: (e["year"], e["id"]))

    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "year", "url_live", "url_wayback"])
        w.writeheader()
        w.writerows(entries)

    c = Counter(e["year"] for e in entries)
    print(f"✅ Censo guardado: {len(entries)} resoluciones únicas (2016 en adelante).")
    for y in sorted(c):
        print(f"   Año {y}: {c[y]} resoluciones")

if __name__ == "__main__":
    main()
