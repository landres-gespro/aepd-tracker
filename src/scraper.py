import os
import sys
import csv
import urllib.parse
import pymupdf
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import requests

BASE_URL = "https://www.aepd.es/informes-y-resoluciones/resoluciones"
DATA_FILE = "data/resultados.csv"
DEBUG_HTML = "data/debug.html"
DEBUG_PNG = "data/debug.png"

def get_latest_pdfs(limit=2):
    url = f"{BASE_URL}?page=1"
    pdf_urls = []
    
    try:
        print(f"🚀 Lanzando navegador invisible (Playwright)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            print(f"🔍 Navegando a: {url}")
            # Cambiamos la espera: domcontentloaded es más rápido, luego añadimos espera manual
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # ⏱️ Esperamos 5 segundos extra por si hay scripts de seguridad cargando
            print("⏱️ Esperando 5 segundos a que termine de cargar el JS...")
            page.wait_for_timeout(5000) 
            
            html = page.content()
            
            # 📸 CAPTURA DE PANTALLA FORENSE
            os.makedirs("data", exist_ok=True)
            page.screenshot(path=DEBUG_PNG)
            print(f"📸 Captura de pantalla guardada en {DEBUG_PNG}")
            
            browser.close()
            
        print(f"📡 Navegación completada. Analizando HTML...")
        
        # 💾 GUARDAR HTML FORENSE
        with open(DEBUG_HTML, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"📄 HTML guardado en {DEBUG_HTML}")
        print(f"👀 Primeros 500 caracteres del HTML recibido:\n{html[:500]}...")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscamos CUALQUIER enlace, no solo los .pdf
        all_links = soup.find_all('a')
        print(f"🔗 Analizando {len(all_links)} enlaces totales <a> en el HTML.")
        
        for a in all_links:
            href = a.get('href', '')
            if href.lower().endswith('.pdf'):
                pdf_urls.append(urllib.parse.urljoin(BASE_URL, href))
                if len(pdf_urls) >= limit:
                    break
                    
        print(f"📄 ¡Éxito! Encontrados {len(pdf_urls)} PDFs válidos.")
        return pdf_urls
    except Exception as e:
        print(f"❌ Error en el navegador: {e}")
        return []

def extract_text_from_memory(pdf_url):
    pdf_bytes = None
    try:
        print(f"⬇️ Descargando PDF (vía rápida)...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(pdf_url, headers=headers, timeout=30)
        response.raise_for_status()
        pdf_bytes = response.content
    except Exception as e:
        print(f"⚠️ Descarga rápida falló ({e}). Usando navegador...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                response = page.request.get(pdf_url)
                pdf_bytes = response.body()
                browser.close()
        except Exception as e2:
            print(f"❌ Error total leyendo PDF: {e2}")
            return ""

    if not pdf_bytes:
        return ""

    try:
        print(f"📖 Extrayendo texto del PDF...")
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page_num in doc:
            text += page_num.get_text()
        return text
    except Exception as e:
        print(f"❌ Error procesando el PDF: {e}")
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
