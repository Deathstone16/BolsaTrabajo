from django.shortcuts import render

def home(request):
    featured_jobs = [
        {"id": 1, "title": "Desarrollador Full Stack", "company": "TechSolutions SA", "location": "CABA", "modality": "Remoto"},
        {"id": 2, "title": "Analista de Datos", "company": "DataMetrics", "location": "CABA", "modality": "Híbrido"},
        {"id": 3, "title": "Diseñador UX/UI", "company": "CreativeLab", "location": "La Plata", "modality": "Presencial"},
    ]
    IAA()
    return render(request, 'home.html', {'featured_jobs': featured_jobs})


def IAA():
    # 1. Fragmentar PDF de 30 páginas en bloques de 5 páginas
    ruta_pdf = "RUTA CV.pdf"
    bloques_cv = extraer_texto_por_bloques("cv_extenso.pdf", paginas_por_bloque=5)

    # 2. Extraer todo sin filtrar bloque por bloque
    habilidades_acumuladas = []
    for i, bloque in enumerate(bloques_cv):
        print(f"Procesando bloque {i+1} de {len(bloques_cv)}...")
        hallazgos = extraer_detalles_bloque(bloque)
        habilidades_acumuladas.extend(hallazgos)

    # 3. Consolidar el resultado final
    resultado_final = consolidar_y_evaluar_cv(habilidades_acumuladas)

    # Visualizar resultado
    print(json.dumps(resultado_final, ensure_ascii=False, indent=2))

import pdfplumber

def extraer_texto_por_bloques(ruta_pdf, paginas_por_bloque=5):
    """Lee el PDF y agrupa el texto en bloques de N páginas."""
    bloques = []
    with pdfplumber.open(ruta_pdf) as pdf:
        total_paginas = len(pdf.pages)
        for i in range(0, total_paginas, paginas_por_bloque):
            texto_bloque = ""
            for pagina in pdf.pages[i:i + paginas_por_bloque]:
                texto_bloque += (pagina.extract_text() or "") + "\n"
            bloques.append(texto_bloque)
    return bloques

import json
from google import genai
from google.genai import types

def get_genai_client():
    """Crea el cliente de Gemini en el momento de usarlo.

    Antes se instanciaba a nivel de modulo. Como urls.py importa este
    archivo, `genai.Client()` corria en cada arranque y, sin GEMINI_API_KEY
    configurada, tiraba ValueError y el proyecto entero no levantaba.
    """
    return genai.Client()

def extraer_detalles_bloque(texto_bloque):
    """Extrae absolutamente TODAS las tecnologías y experiencias encontradas en la sección."""
    prompt = f"""
    Lee exhaustivamente este fragmento de un CV y extrae TODA la información técnica. 
    NO resumas. Extrae cada herramienta, lenguaje, marco de trabajo, base de datos, metodología o proyecto mencionado.

    Texto del fragmento:
    {texto_bloque}
    """
    
    response = get_genai_client().models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "habilidades_halladas": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "tecnologia": {"type": "STRING"},
                                "contexto_uso": {"type": "STRING", "description": "En qué proyecto, rol o curso se usó y qué hacía."}
                            },
                            "required": ["tecnologia", "contexto_uso"]
                        }
                    }
                },
                "required": ["habilidades_halladas"]
            }
        )
    )
    return json.loads(response.text).get("habilidades_halladas", [])

def consolidar_y_evaluar_cv(lista_habilidades_totales):
    prompt = f"""
    Eres un analista técnico sénior. A continuación tienes el volcado completo de habilidades y contextos extraídos de un CV extenso de 30 páginas.

    Tu tarea es consolidar y evaluar el perfil real del candidato:
    1. Agrupa las tecnologías repetidas.
    2. Suma la evidencia dispersa para determinar el nivel REAL:
       - Si una tecnología solo aparece en materias/cursos o menciones teóricas -> Nivel: 'Teórico'.
       - Si aparece aplicada en proyectos académicos o de prueba -> Nivel: 'Principiante'.
       - Si aparece en múltiples proyectos reales o experiencia laboral formal -> Nivel: 'Intermedio' o 'Avanzado'.
    3. Justifica detalladamente el nivel asignado citando los proyectos o roles donde apareció.

    Datos consolidados del CV:
    {json.dumps(lista_habilidades_totales, ensure_ascii=False, indent=2)}
    """

    response = get_genai_client().models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "resumen_ejecutivo": {"type": "STRING"},
                    "analisis_profundo": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "tecnologia": {"type": "STRING"},
                                "nivel_evaluado": {"type": "STRING"},
                                "justificacion_evidencia": {"type": "STRING"}
                            },
                            "required": ["tecnologia", "nivel_evaluado", "justificacion_evidencia"]
                        }
                    }
                },
                "required": ["resumen_ejecutivo", "analisis_profundo"]
            }
        )
    )
    return json.loads(response.text)

