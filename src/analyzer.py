import os
import pandas as pd
from groq import Groq
import json
from pydantic import BaseModel, Field

# Configuración
CSV_FILE = "data/resultados.csv"
# La API Key la leerá automáticamente de los Secretos de GitHub
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# 📋 ESQUEMA OBLIGATORIO: Así forzamos a la IA a responder siempre con este formato
class AnalisisResolucion(BaseModel):
    tematica: str = Field(description="Categoría: Videovigilancia, RGPD, RRHH, Ficheros públicos, etc.")
    resumen_ejecutivo: str = Field(description="Resumen del caso en 2-3 líneas claras para un abogado.")
    hechos_principales: list[str] = Field(description="Lista de 3 a 5 puntos clave sobre qué pasó.")
    resolucion_final: str = Field(description="Conclusión: Sanción (y cuantía), Archivo, Apercibimiento, etc.")
    normativas_infringidas: list[str] = Field(description="Artículos del RGPD o LOPDGDD infringidos.")

def analyze_text(texto):
    if not texto or "Error" in str(texto):
        return None
        
    # Llama 3.1 tiene una ventana de contexto gigante, pero limitamos el texto por seguridad
    texto_input = str(texto)[:3000]
    
    prompt = f"""Eres un abogado experto en protección de datos y jurisprudencia de la AEPD.
Analiza el siguiente texto de una resolución y extrae la información en formato JSON estricto.
Si un campo no se menciona o no aplica, indícalo como 'No especificado'.

TEXTO DE LA RESOLUCIÓN:
{texto_input}
"""
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres un asistente legal experto. Devuelve SOLO un JSON válido."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile", # Modelo potentísimo y rápido
            response_format={"type": "json_object"} # Obliga a la IA a devolver JSON
        )
        
        response_json = chat_completion.choices[0].message.content
        data = json.loads(response_json)
        valid_data = AnalisisResolucion(**data)
        return valid_data.model_dump()
    except Exception as e:
        print(f"Error analizando con IA: {e}")
        return None

def main():
    if not os.path.exists(CSV_FILE):
        print("No hay CSV para analizar.")
        return

    print("🤖 Cargando base de datos para análisis con IA...")
    df = pd.read_csv(CSV_FILE)
    
    # Creamos las nuevas columnas "inteligentes" si no existen
    new_cols = ['Tematica_IA', 'Resumen_IA', 'Hechos_IA', 'Resolucion_IA', 'Normativa_IA']
    for col in new_cols:
        if col not in df.columns:
            df[col] = ""
            
    # Buscamos solo las filas que NO han sido analizadas aún
    mask = (df['Tematica_IA'] == "") | (df['Tematica_IA'] == "Error de procesamiento")
    rows_to_process = df[mask]
    
    print(f"🚀 Encontradas {len(rows_to_process)} resoluciones pendientes de análisis IA.")
    
    for index, row in rows_to_process.iterrows():
        titulo = row['Titulo']
        print(f"🧠 Analizando: {titulo}...")
        
        analisis = analyze_text(row['Texto_Completo'])
        
        if analisis:
            df.loc[index, 'Tematica_IA'] = analisis['tematica']
            df.loc[index, 'Resumen_IA'] = analisis['resumen_ejecutivo']
            # Unimos las listas con ' | ' para que se lean bien en Excel/CSV
            df.loc[index, 'Hechos_IA'] = " | ".join(analisis['hechos_principales'])
            df.loc[index, 'Resolucion_IA'] = analisis['resolucion_final']
            df.loc[index, 'Normativa_IA'] = ", ".join(analisis['normativas_infringidas'])
            print(f"   ✅ Éxito: Clasificado como '{analisis['tematica']}'")
        else:
            df.loc[index, 'Tematica_IA'] = "Error de procesamiento"
            
    print("💾 Guardando resultados enriquecidos en el CSV...")
    df.to_csv(CSV_FILE, index=False, encoding='utf-8')
    print("✅ Análisis completado.")

if __name__ == "__main__":
    main()
