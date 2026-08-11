import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
import fitz
import csv

BASE_URL = "https://www.aepd.es/informes-y-resoluciones/resoluciones"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
DATA_FILE = "data/resultados.csv"

def get_latest_pdfs(limit=2):
    url = f"{BASE_URL}?page=1"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        pdf_urls = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf'):
                pdf_urls.append(urllib.parse.urljoin(BASE_URL, href))
                if len(pdf_urls) >= limit:
                    break
        return pdf_urls
    except Exception as e:
        print(f"Error buscando PDFs: {e}")
        return []

def extract_text_from_memory(pdf_url):
    try:
        response = requests.get(pdf_url, headers=HEADERS, stream=True)
        doc = fitz.open(stream=response.content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        return f"Error leyendo PDF: {e}"

def save_to_csv(filename, text):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    file_exists = os.path.isfile(DATA_FILE)
    
    with open(DATA_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Archivo", "Texto_Extraido"])
        
        # Limpiamos saltos de línea múltiples para que el CSV no se rompa
        clean_text = text.replace('\n', ' ').replace('\r', ' ')
        writer.writerow([filename, clean_text[:1000] + "... [RESTO OMITIDO]"])

def main():
    print("🤖 Iniciando batida rápida en AEPD...")
    pdfs = get_latest_pdfs(limit=2)
    
    for pdf_url in pdfs:
        filename = pdf_url.split('/')[-1]
        print(f"Procesando {filename}...")
        text = extract_text_from_memory(pdf_url)
        save_to_csv(filename, text)
        
    print("✅ Extracción completada y guardada en data/resultados.csv")

if __name__ == "__main__":
    main()
