import os
import sys
import time
import pandas as pd
from groq import Groq
import json
from pydantic import BaseModel, Field, ValidationError

CSV_FILE = "data/resultados.csv"
# Procesaremos 15 resoluciones por ejecución para no reventar el límite diario de Groq
BATCH_SIZE = 25 

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class AnalisisResolucion(BaseModel):
    tematica: str = Field(description="Categoría principal (ej. Videovigilancia, RRHH, RGPD, Derechos ARSO)")
    resumen_ejecutivo: str = Field(description="Resumen del caso en 2-3 líneas.")
    hechos_principales: list[str] = Field(description="Lista de 3 a 5 puntos clave.")
    resolucion_final: str = Field(description="Conclusión: Sanción (y cuantía), Archivo, Apercibimiento.")
    normativas_infringidas: list[str] = Field(description="Artículos infringidos.")

def analyze_text(texto):
    if not texto or "Error" in str(texto):
        return None
        
    texto_input = str(texto)[:4000]
    
    # 🎯 PROMPT BLINDADO: Le damos un ejemplo exacto (Few-Shot) para que no improvise claves
    prompt = f"""Eres un asistente legal experto en la AEPD. Analiza el texto y extrae la información.
DEBES devolver EXCLUSIVAMENTE un objeto JSON con EXACTAMENTE estas 5 claves:
"tematica", "resumen_ejecutivo", "hechos_principales", "resolucion_final", "normativas_infringidas".
Si no encuentras información para una clave, usa el string "No especificado" o una lista vacía [].

EJEMPLO DE RESPUESTA OBLIGATORIA:
{{
  "tematica": "Videovigilancia",
  "resumen_ejecutivo": "Una comunidad de vecinos instaló cámaras que grababan la vía pública sin autorización.",
  "hechos_principales": ["Instalación de cámaras sin aviso", "Grabación de la calle", "Denuncia de un vecino"],
  "resolucion_final": "Sanción de 3.000 euros",
  "normativas_infringidas": ["Art. 5 RGPD", "Art. 6 RGPD"]
}}

TEXTO A ANALIZAR:
{texto_input}
"""
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres un asistente legal. Devuelve SOLO un JSON válido, sin texto adicional, sin markdown, sin explicaciones."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.1 # Temperatura baja para respuestas más estrictas y estructuradas
        )
        
        response_json = chat_completion.choices[0].message.content
        
        # A veces la IA añade ```json al principio. Lo limpiamos por si acaso.
        if response_json.startswith("```json"):
            response_json = response_json[7:-3].strip()
            
        data = json.loads(response_json)
        valid_data = AnalisisResolucion(**data)
        return valid_data.model_dump()
        
    except ValidationError as ve:
        print(f"   ⚠️ Error de formato: La IA intentó inventarse claves nuevas.")
        return None
    except Exception as e:
        if "429" in str(e):
            print("   🛑 LÍMITE DIARIO DE GROQ ALCANZADO (Rate Limit). Deteniendo el lote de hoy.")
            return "RATE_LIMIT"
        print(f"   ❌ Error inesperado: {e}")
        return None

def main():
    if not os.path.exists(CSV_FILE):
        print("No hay CSV para analizar.")
        return

    print("🤖 Cargando base de datos...")
    df = pd.read_csv(CSV_FILE)
    
    new_cols = ['Tematica_IA', 'Resumen_IA', 'Hechos_IA', 'Resolucion_IA', 'Normativa_IA']
    for col in new_cols:
        if col not in df.columns:
            df[col] = ""
        else:
            # Forzamos tipo TEXTO: convierte los huecos (NaN) en "" y evita el error float64
            df[col] = df[col].fillna("").astype(str)
            
    # Buscamos filas vacías o con error previo
    mask = (df['Tematica_IA'] == "") | (df['Tematica_IA'] == "Error de procesamiento")
    rows_to_process = df[mask]
    
    total_pending = len(rows_to_process)
    print(f"📊 Total de resoluciones pendientes: {total_pending}")
    
    if total_pending == 0:
        print("✅ Todo está analizado.")
        return

    # Limitamos el procesamiento al BATCH_SIZE
    limit = min(BATCH_SIZE, total_pending)
    print(f"🚀 Procesando lote de {limit} resoluciones (para no saturar la API de Groq)...")
    
    processed_count = 0
    
    for index, row in rows_to_process.head(limit).iterrows():
        titulo = row['Titulo']
        print(f"🧠 [{processed_count + 1}/{limit}] Analizando: {titulo}...")
        
        analisis = analyze_text(row['Texto_Completo'])
        
        if analisis == "RATE_LIMIT":
            print("🛑 Guardando progreso y deteniendo la ejecución hasta mañana.")
            break
            
        if analisis:
            df.loc[index, 'Tematica_IA'] = analisis['tematica']
            df.loc[index, 'Resumen_IA'] = analisis['resumen_ejecutivo']
            df.loc[index, 'Hechos_IA'] = " | ".join(analisis['hechos_principales'])
            df.loc[index, 'Resolucion_IA'] = analisis['resolucion_final']
            df.loc[index, 'Normativa_IA'] = ", ".join(analisis['normativas_infringidas'])
            print(f"   ✅ Éxito: '{analisis['tematica']}'")
            processed_count += 1
        else:
            df.loc[index, 'Tematica_IA'] = "Error de procesamiento"
            processed_count += 1
            
        # Pausa de cortesía para evitar bloqueos por peticiones por minuto (RPM)
        time.sleep(2) 
            
    print(f"💾 Guardando {processed_count} nuevos análisis en el CSV...")
    df.to_csv(CSV_FILE, index=False, encoding='utf-8')
    
    remaining = total_pending - processed_count
    print(f"✅ Lote completado. Quedan {remaining} resoluciones pendientes para futuras ejecuciones.")

if __name__ == "__main__":
    main()
