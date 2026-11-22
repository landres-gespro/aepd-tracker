import os
import sys
import csv
import feedparser
import requests
import pymupdf
from datetime import datetime

RSS_URL = "https://www.aepd.es/informes-y-resoluciones/resoluciones/feed.xml"
DATA_FILE = "data/resultados.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
CSV_COLUMNS = ["Titulo", "Link_PDF", "Resumen_AEPD", "Texto_Completo", "Fecha_Registro"]

def hoy():
    """Fecha de hoy en formato ISO (AAAA-MM-DD), perfecta para filtrar por rangos."""
    return datetime.now().strftime("%Y-%m-%d")

def get_processed_links():
    """Enlaces de PDF que ya tenemos en el CSV (para no duplicar)."""
    processed = set()
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                processed.add(row.get('Link_PDF', ''))
    return processed

def migrate_csv():
    """Si el CSV es antiguo (4 columnas), le añade Fecha_Registro vacía una sola vez."""
    if not os.path.exists(DATA_FILE):
        return
    with open(DATA_FILE, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if "Fecha_Registro" in fieldnames:
            return  # ya está migrado, no tocamos nada
        rows = list(reader)

    with open(DATA_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        for row in rows:
            writer.writerow([
                row.get("Titulo", ""),
                row.get("Link_PDF", ""),
                row.get("Resumen_AEPD", ""),
                row.get("Texto_Completo", ""),
                "",  # las filas antiguas no tienen fecha conocida
            ])
    print(f"🔄 CSV migrado: columna Fecha_Registro añadida ({len(rows)} filas antiguas quedan sin fecha).")

def download_pdf_text(url):
    """Descarga el PDF en memoria y extrae todo el texto."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        doc = pymupdf.open(stream=response.content, filetype="pdf")
        text = "".join([page.get_text() for page in doc])
        return text.replace('\n', ' ').replace('\r', ' ').strip()
    except Exception as e:
        return f"Error extrayendo PDF: {e}"

def main():
    print("🤖 Conectando al canal RSS oficial de la AEPD...")
    feed = feedparser.parse(RSS_URL)

    if not feed.entries:
        print("⚠️ No se pudieron leer entradas del RSS.")
        sys.exit(0)

    print(f"📡 Encontradas {len(feed.entries)} resoluciones recientes en el RSS.")

    # Aseguramos que el CSV tenga la columna de fecha (migración única)
    migrate_csv()

    processed_links = get_processed_links()
    new_entries = [entry for entry in feed.entries if entry.link not in processed_links]

    if not new_entries:
        print("✅ No hay resoluciones nuevas que no tengamos ya en nuestra base de datos.")
        sys.exit(0)

    print(f"🚀 Procesando {len(new_entries)} resoluciones NUEVAS...")

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    file_exists = os.path.isfile(DATA_FILE)
    fecha = hoy()  # todas las entradas de esta ejecución comparten la fecha del día

    with open(DATA_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(CSV_COLUMNS)

        for entry in new_entries:
            titulo = entry.get('title', 'Sin Titulo')
            link = entry.get('link', '')
            resumen = entry.get('summary', '').replace('\n', ' ').replace('\r', ' ')

            print(f"📄 Procesando {titulo}...")
            texto = download_pdf_text(link)

            writer.writerow([titulo, link, resumen, texto[:3000] + "...", fecha])
            print(f"💾 Guardado con fecha de registro {fecha}.")

    print("✅ Ciclo completado con éxito.")

if __name__ == "__main__":
    main()
