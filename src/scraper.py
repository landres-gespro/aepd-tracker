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
BASE_COLUMNS = ["Titulo", "Link_PDF", "Resumen_AEPD", "Texto_Completo"]
FECHA_COL = "Fecha_Registro"

def hoy():
    return datetime.now().strftime("%Y-%m-%d")

def leer_csv_completo():
    """Lee el CSV manteniendo TODAS las columnas existentes."""
    if not os.path.exists(DATA_FILE):
        return [], []
    with open(DATA_FILE, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    return fieldnames, rows

def get_processed_links(rows):
    return {row.get('Link_PDF', '') for row in rows if row.get('Link_PDF')}

def migrate_csv(fieldnames, rows):
    """Añade Fecha_Registro al final si no existe, preservando todas las columnas."""
    if FECHA_COL in fieldnames:
        return fieldnames, rows  # ya existe, no tocamos nada

    nuevos_fieldnames = list(fieldnames) + [FECHA_COL]
    for row in rows:
        row[FECHA_COL] = ""  # filas antiguas sin fecha conocida
    print(f"🔄 CSV migrado: columna {FECHA_COL} añadida al final ({len(rows)} filas preservadas).")
    return nuevos_fieldnames, rows

def download_pdf_text(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        doc = pymupdf.open(stream=response.content, filetype="pdf")
        text = "".join([page.get_text() for page in doc])
        return text.replace('\n', ' ').replace('\r', ' ').strip()
    except Exception as e:
        return f"Error extrayendo PDF: {e}"

def guardar_csv_completo(fieldnames, rows):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main():
    print("🤖 Conectando al canal RSS oficial de la AEPD...")
    feed = feedparser.parse(RSS_URL)

    if not feed.entries:
        print("⚠️ No se pudieron leer entradas del RSS.")
        sys.exit(0)

    print(f"📡 Encontradas {len(feed.entries)} resoluciones recientes en el RSS.")

    # Leemos el CSV con TODAS sus columnas
    fieldnames, rows = leer_csv_completo()

    # Si el CSV aún no existe, creamos la estructura base + fecha
    if not fieldnames:
        fieldnames = BASE_COLUMNS + [FECHA_COL]
        rows = []

    # Migración única: añadir Fecha_Registro preservando todo lo existente
    fieldnames, rows = migrate_csv(fieldnames, rows)

    processed_links = get_processed_links(rows)
    new_entries = [entry for entry in feed.entries if entry.link not in processed_links]

    if not new_entries:
        print("✅ No hay resoluciones nuevas.")
        # Aun así, guardamos por si se hizo la migración
        if FECHA_COL in fieldnames:
            guardar_csv_completo(fieldnames, rows)
        sys.exit(0)

    print(f"🚀 Procesando {len(new_entries)} resoluciones NUEVAS...")
    fecha = hoy()

    for entry in new_entries:
        titulo = entry.get('title', 'Sin Titulo')
        link = entry.get('link', '')
        resumen = entry.get('summary', '').replace('\n', ' ').replace('\r', ' ')
        print(f"📄 Procesando {titulo}...")
        texto = download_pdf_text(link)

        # Construimos la nueva fila respetando el orden de fieldnames
        nueva_fila = {col: "" for col in fieldnames}
        nueva_fila["Titulo"] = titulo
        nueva_fila["Link_PDF"] = link
        nueva_fila["Resumen_AEPD"] = resumen
        nueva_fila["Texto_Completo"] = texto[:3000] + "..."
        nueva_fila[FECHA_COL] = fecha

        # Si existen columnas de IA, las dejamos vacías para que el analyzer las rellene
        # (no hace falta asignar nada: ya están en "" por defecto)

        rows.append(nueva_fila)
        print(f"💾 Guardado con fecha de registro {fecha}.")

    guardar_csv_completo(fieldnames, rows)
    print("✅ Ciclo completado con éxito.")

if __name__ == "__main__":
    main()
