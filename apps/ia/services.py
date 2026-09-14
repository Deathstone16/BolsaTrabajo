import json
import time
import pdfplumber
from groq import Groq



def extraer_texto_por_bloques(ruta_pdf, paginas_por_bloque=4):
    """Lee el PDF y genera bloques pequeños para no superar los 8,000 tokens."""
    bloques = []
    with pdfplumber.open(ruta_pdf) as pdf:
        total_paginas = len(pdf.pages)
        for i in range(0, total_paginas, paginas_por_bloque):
            texto_bloque = ""
            for j, pagina in enumerate(pdf.pages[i:i + paginas_por_bloque]):
                num_pagina = i + j + 1
                texto_bloque += f"\n--- PÁGINA {num_pagina} ---\n" + (pagina.extract_text() or "")
            bloques.append(texto_bloque)
    return bloques

def procesar_bloque_groq(texto_bloque, client):
    """Extrae las habilidades de un bloque individual con su ubicación exacta."""
    prompt = f"""
    Lee exhaustivamente este fragmento de un CV y extrae TODAS las tecnologías, herramientas, lenguajes o conocimientos mencionados.
    
    REGLA: Registra con precisión la sección o proyecto donde aparece (ej. 'Proyecto SysTUP', 'Proyecto Bienal', 'Habilidades Técnicas', 'Educación').
    
    Fragmento del CV:
    {texto_bloque}
    
    Responde ÚNICAMENTE en JSON con este formato:
    {{
      "hallazgos": [
        {{
          "tecnologia": "Nombre de la herramienta/lenguaje",
          "ubicacion_o_proyecto": "Lugar exacto del CV donde se menciona"
        }}
      ]
    }}
    """
    
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": "Extrae datos técnicos sin modificar ni asumir nada. Responde siempre en JSON válido."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=950,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content).get("hallazgos", [])
def consolidar_evaluacion_final(todos_los_hallazgos, client):
    """Combina todos los hallazgos y aplica la matriz de evaluación estricta cuidando el OTPM."""
    prompt = f"""
    Eres un auditor técnico de recursos humanos basado ESTRICTAMENTE en evidencias. 
    A continuación tienes la lista completa de hallazgos extraídos de un CV:

    {json.dumps(todos_los_hallazgos, ensure_ascii=False, indent=2)}

    REGLAS OBLIGATORIAS DE EVALUACIÓN:
    1. SOLO evalúa lo que está explícitamente listado en los hallazgos. NO asumas años de experiencia si no están indicados.
    2. NO menciones stacks tecnológicos no listados (ej. NO inventes Express, Angular, MERN o MEAN).
    3. Aplica esta escala ESTRICTA para 'nivel_evaluado':
       - 'Teórico': Solo figura en 'Habilidades Técnicas' o cursos, pero NO en proyectos concretos.
       - 'Principiante': Utilizado en UN solo proyecto académico, personal o de investigación.
       - 'Intermedio': Utilizado en DOS O MÁS proyectos concretos, o respaldado por becas de investigación/desarrollo activas.
       - 'Avanzado': Experiencia profesional formal continuada con liderazgo técnico explícito.

    IMPORTANTE: Mantén las respuestas de 'justificacion_evidencia' breves y al punto (máximo 15 palabras por habilidad) para no exceder los límites de respuesta.

    DEBES responder ÚNICAMENTE con un objeto JSON con la siguiente estructura:
    {{
      "resumen_ejecutivo": "Síntesis objetiva breve del perfil.",
      "habilidades_analizadas": [
        {{
          "tecnologia": "Nombre de la habilidad",
          "nivel_evaluado": "Teórico / Principiante / Intermedio / Avanzado",
          "justificacion_evidencia": "Cita breve de los proyectos, becas o secciones."
        }}
      ]
    }}
    """
    
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": "Eres un auditor estricto de CVs. Responde siempre en JSON válido sin inventar datos."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=950,  # <-- LÍMITE FÍSICO DE SALIDA PARA NO VIOLAR EL OTPM (1000)
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
def pipeline_cv_completo(ruta_pdf):
    client = Groq()
    print("1. Dividiendo PDF en bloques de 4 páginas...")
    bloques = extraer_texto_por_bloques(ruta_pdf, paginas_por_bloque=4)
    
    hallazgos_totales = []
    
    print(f"2. Procesando {len(bloques)} bloques secuencialmente...")
    for idx, bloque in enumerate(bloques):
        print(f"   -> Procesando bloque {idx + 1} de {len(bloques)}...")
        
        # Procesar bloque
        hallazgos = procesar_bloque_groq(bloque, client)
        hallazgos_totales.extend(hallazgos)
        
        # Pausa de 12 segundos para garantizar no superar los 8,000 tokens/minuto
        if idx < len(bloques) - 1:
            print("   -> Pausa respetando la cuota de TPM (12 segundos)...")
            time.sleep(12)
            
    print("3. Consolidando análisis final...")
    resultado_final = consolidar_evaluacion_final(hallazgos_totales, client)
    return resultado_final


def call():
    archivo = "CV.pdf"  # Reemplaza con el nombre de tu archivo PDF
    resultado = pipeline_cv_completo(archivo)
    
    print("\n=== RESULTADO FINAL CONSOLIDADO ===")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
   