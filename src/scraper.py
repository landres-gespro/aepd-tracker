  import os
  import requests
  from bs4 import BeautifulSoup
  import urllib.parse
  import fitz # Esto es PyMuPDF, sirve para leer PDFs
  import csv

  BASE_URL = "https://www.aepd.es/informes-y-resoluciones/resoluciones"
  HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
  DATA_FILE = "data/resultados.csv"

  def get_latest_pdfs(limit=2):
      """Descarga los enlaces de los últimos PDFs publicados."""
      url = f"{BASE_URL}?page=1"
      response = requests.get(url, headers=HEADERS)
      soup = BeautifulSoup(response.text, 'html.parser')
      pdf_urls = []
      for a in soup.find_all('a', href=True):
          href = a['href']
          if href.lower().endswith('.pdf'):
              pdf_urls.append(urllib.parse.urljoin(BASE_URL, href))
              if len(pdf_urls) >= limit:
                  break
      return pdf_urls

  def extract_text_from_memory(pdf_url):
      """Descarga el PDF en la RAM, extrae el texto y lo descarta."""
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
      """Guarda el texto extraído en nuestro archivo de base de datos."""
      os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
      file_exists = os.path.isfile(DATA_FILE)
      
      with open(DATA_FILE, mode='a', newline='', encoding='utf-8') as file:
          writer = csv.writer(file)
          if not file_exists:
              writer.writerow(["Archivo", "Texto_Extraido"])
          
          # Recortamos a los primeros 1000 caracteres para no llenar el repo
          writer.writerow([filename, text[:1000] + "... [RESTO OMITIDO]"])

  def main():
      print("🤖 Iniciando batida rápida en AEPD...")
      pdfs = get_latest_pdfs(limit=2) # Solo los 2 últimos por ahora
      
      for pdf_url in pdfs:
          filename = pdf_url.split('/')[-1]
          print(f"Procesando {filename}...")
          text = extract_text_from_memory(pdf_url)
          save_to_csv(filename, text)
          
      print("✅ Extracción completada y guardada en data/resultados.csv")

  if __name__ == "__main__":
      main()
