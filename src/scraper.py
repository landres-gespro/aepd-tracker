import os
import sys
import csv
import urllib.parse
import fitz # PyMuPDF
from bs4 import BeautifulSoup

# IMPORTANTE: Usamos curl_cffi en lugar de requests normal
# Esta librería imita el comportamiento de Chrome para saltar bloqueos 403
from curl_cffi import requests 

BASE_URL = "https://www.aepd.es/informes-y-resoluciones/resoluciones"
DATA_FILE = "data/resultados.csv"

def get_latest_pdfs(limit=2):
    url = f"{BASE_URL}?page=1"
    try:
        print(f"🔍 Conectando a la AEPD usando modo Stealth (Chrome)...")
        # impersonate="chrome" es la magia que engaña al firewall
        response = requests.get(url, impersonate="chrome", timeout=20)
        print(f"📡 Código de respuesta HTTP: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ La web respondió con código: {response.status_code}")
            os.makedirs("data", exist_ok=True)
            with open("data/error.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        pdf_urls = []
        
        links = soup.find_all('a', href=True)
        print(f"🔗 Analizando {len(links)} enlaces totales en el HTML recibido.")
        
        for a in links:
            href = a['href']
            if href.lower().endswith('.pdf'):
                pdf_urls.append(urllib.parse.urljoin(BASE_URL, href))
                if len(pdf_urls) >= limit:
                    break
                    
        print(f"📄 ¡Éxito! Encontrados {len(pdf_urls)} PDFs válidos.")
        return pdf_urls
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return []

def extract_text_from_memory(pdf_url):
    try:
        print(f"⬇️ Descargando PDF...")
        response = requests.get(pdf_url, impersonate="chrome", timeout=30)
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
        print("🛑 No se encontraron PDFs. El script termina.")
        sys.exit(0) 
    
    for pdf_url in pdfs:
        filename = pdf_url.split('/')[-1]
        print(f"Procesando {filename}...")
        text = extract_text_from_memory(pdf_url)
        save_to_csv(filename, text)
        
    print("✅ Extracción completada.")

if __name__ == "__main__":
    main()
