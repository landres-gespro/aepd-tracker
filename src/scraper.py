import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
import fitz
import csv
import sys

BASE_URL = "https://www.aepd.es/informes-y-resoluciones/resoluciones"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.5",
}
DATA_FILE = "data/resultados.csv"

def get_latest_pdfs(limit=2):
    url = f"{BASE_URL}?page=1"
    try:
        print(f"🔍 Conectando a: {url}")
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"📡 Código de respuesta HTTP: {response.status_code}")
        
        # Si la web nos bloquea (403) o falla, guardamos el HTML para investigar
        if response.status_code != 200:
            print(f"❌ La web respondió con código: {response.status_code}")
            os.makedirs("data", exist_ok=True)
            with open("data/error.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        pdf_urls = []
        
        # Contamos cuántos enlaces <a> hay en total en la página
        links = soup.find_all('a', href=True)
        print(f"🔗 Encontrados {len(links)} enlaces totales en el HTML recibido.")
        
        for a in links:
            href = a['href']
            if href.lower().endswith('.pdf'):
                pdf_urls.append(urllib.parse.urljoin(BASE_URL, href))
                if len(pdf_urls) >= limit:
                    break
                    
        print(f"📄 Encontrados {len(pdf_urls)} PDFs válidos.")
        return pdf_urls
    except Exception as e:
        print(f"❌ Error buscando PDFs: {e}")
        return []

def extract_text_from_memory(pdf_url):
    try:
        print(f"⬇️ Descargando PDF...")
        response = requests.get(pdf_url, headers=HEADERS, stream=True, timeout=30)
        response.raise_for_status()
        
        print(f"📖 Extrayendo texto del PDF...")
        doc = fitz.open(stream=response.content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"❌ Error leyendo PDF: {e}")
        return ""

def save_to_csv(filename, text):
    if not text:
        print("⚠️ No hay texto para guardar.")
        return
        
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    file_exists = os.path.isfile(DATA_FILE)
    
    with open(DATA_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Archivo", "Texto_Extraido"])
        
        clean_text = text.replace('\n', ' ').replace('\r', ' ')
        writer.writerow([filename, clean_text[:1000] + "... [RESTO OMITIDO]"])
    print(f"💾 Guardado en {DATA_FILE}")

def main():
    print("🤖 Iniciando batida rápida en AEPD...")
    
    pdfs = get_latest_pdfs(limit=2)
    
    if not pdfs:
        print("🛑 No se encontraron PDFs. El script termina sin crear el CSV.")
        sys.exit(0) # Terminamos el script con éxito (exit code 0) pero sin archivo
    
    for pdf_url in pdfs:
        filename = pdf_url.split('/')[-1]
        print(f"Procesando {filename}...")
        text = extract_text_from_memory(pdf_url)
        save_to_csv(filename, text)
        
    print("✅ Extracción completada.")

if __name__ == "__main__":
    main()
