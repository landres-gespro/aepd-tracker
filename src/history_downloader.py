import os
import csv
import time
import requests
import pymupdf

INDEX_FILE = "data/history/index.csv"
HISTORY_DIR = "data/history"
BATCH_SIZE = 30  # Resoluciones históricas por noche (lento, gratis y respetuoso)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def load_index():
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_processed():
    """IDs que ya tenemos guardados en los CSVs por año."""
    processed = set()
    if not os.path.exists(HISTORY_DIR):
        return processed
    for fname in os.listdir(HISTORY_DIR):
        if fname.startswith("textos_") and fname.endswith(".csv"):
            with open(os.path.join(HISTORY_DIR, fname), encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    processed.add(row["id"])
    return processed

def download_pdf(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        if r.content[:4] != b"%PDF":
            return None
        return r.content
    except Exception:
        return None

def extract_text(pdf_bytes):
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        text = "".join(p.get_text() for p in doc)
        return text.replace("\n", " ").replace("\r", " ").strip()
    except Exception:
        return ""

def append_row(year, row):
    path = os.path.join(HISTORY_DIR, f"textos_{year}.csv")
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "year", "url_live", "url_wayback", "texto"])
        if not exists:
            w.writeheader()
        w.writerow(row)

def main():
    index = load_index()
    if not index:
        print("❌ No hay censo histórico. Ejecuta primero el paso 4b.")
        return

    os.makedirs(HISTORY_DIR, exist_ok=True)
    processed = load_processed()
    pending = [e for e in index if e["id"] not in processed]

    print(f"📚 Censo: {len(index)} | Ya procesadas: {len(processed)} | Pendientes: {len(pending)}")
    if not pending:
        print("✅ Histórico completo. ¡Misión cumplida!")
        return

    batch = pending[:BATCH_SIZE]
    ok = fail = 0

    for i, e in enumerate(batch, 1):
        print(f"⬇️ [{i}/{len(batch)}] {e['id']} (año {e['year']})...", end=" ", flush=True)

        # Intento 1: AEPD viva. Intento 2: copia de Wayback.
        pdf = download_pdf(e["url_live"])
        fuente = "AEPD"
        if not pdf:
            time.sleep(1)
            pdf = download_pdf(e["url_wayback"])
            fuente = "Wayback"

        if not pdf:
            print("❌ sin PDF en ambas fuentes")
            fail += 1
            time.sleep(1)
            continue

        text = extract_text(pdf)
        if len(text) < 200:
            print(f"⚠️ texto demasiado corto ({len(text)} chars), omitido")
            fail += 1
            time.sleep(1)
            continue

        append_row(e["year"], {
            "id": e["id"],
            "year": e["year"],
            "url_live": e["url_live"],
            "url_wayback": e["url_wayback"],
            "texto": text[:3000],  # Recorte para mantener el repo ligero
        })
        ok += 1
        print(f"✅ OK ({fuente}, {len(text)} chars)")
        time.sleep(2)  # pausa de cortesía

    print(f"📊 Resumen de la noche: {ok} OK, {fail} fallos")
    print(f"🎯 Progreso total del histórico: {len(processed) + ok} / {len(index)}")

if __name__ == "__main__":
    main()
