# IEN Trabajo — Integración del LLM (Llama) para análisis de CV y recomendación de cursos

**Guía de 0 a 100%** para el equipo técnico. Cubre: qué modelo usar, cómo montarlo en el VPS,
cómo se integra al código Django existente, cómo se "entrena" (spoiler: para el MVP no se
entrena, se *prompt-ea* — la sección 9 explica por qué y deja el camino de fine-tuning
documentado como fase 2), y cómo se testea y evalúa.

Documentos fuente: *MVP Proyecto IEN* y *Acta de Constitución — IEN Trabajo* (pv-v11.0-2026-06-09).

---

## 0. La decisión de diseño que ordena todo lo demás

**El LLM se usa SOLO para lo difuso. Todo lo que pueda ser determinístico, va en Django.**

| Tarea | ¿Quién la hace? | Por qué |
|---|---|---|
| Extraer texto del PDF del CV | Python (`pdfplumber`) | Determinístico, gratis, sin alucinaciones |
| Interpretar ese texto y sacar habilidades estructuradas | **LLM** | Es lenguaje natural desordenado — acá el LLM brilla |
| Normalizar habilidades (lowercase, sin acentos) | Python | Regla de negocio del MVP, trivial en código |
| Calcular el % de match contra una oferta | Python (query + conjuntos) | Matemática exacta, auditable, testeable |
| Detectar la brecha (habilidades faltantes) | Python (diferencia de conjuntos) | Ídem |
| Mapear brecha → cursos del IEN | Python (query al catálogo por tags) | **Nunca** dejar que el LLM "invente" cursos |
| Redactar la explicación amigable para el postulante | **LLM** (opcional) | Texto natural personalizado |

Esto neutraliza de entrada tres riesgos del Acta:

- *"El sistema podría recomendar cursos no relacionados"* → el LLM nunca elige cursos; solo
  extrae habilidades. Los cursos salen de una query al catálogo real.
- *"Riesgo de recomendar cursos que el postulante ya hizo"* → filtro determinístico en la query
  (`exclude(inscripciones__postulante=...)`).
- *"Algoritmos que fallen por mala definición de palabras clave"* → la normalización y el
  matching son código Python testeable, no una caja negra.

---

## 1. Elección del modelo

| Modelo | RAM necesaria (cuantizado Q4) | Calidad para extracción JSON en español | Veredicto |
|---|---|---|---|
| `llama3.1:8b-instruct` | ~6 GB | Muy buena | **Recomendado para el MVP** |
| `llama3.2:3b-instruct` | ~3 GB | Aceptable | Fallback si el VPS es chico |
| `llama3.3:70b` | ~40 GB | Excelente | Inviable self-host en VPS común |

- "Instruct" = versión afinada para seguir instrucciones (siempre usar esta variante).
- "Q4" = cuantización a 4 bits: el modelo ocupa ~4× menos RAM con pérdida de calidad mínima.
  Es el default de Ollama.
- El español rioplatense lo manejan bien de fábrica; no hace falta un modelo "en español".

## 2. Dimensionamiento del VPS

La pregunta clave: **¿CPU o GPU?**

| Opción | Specs mínimas | Latencia por CV (~300 tokens de salida) | Costo aprox/mes |
|---|---|---|---|
| VPS solo CPU | 8 GB RAM, 4-8 vCPU | 30–90 segundos | USD 20–40 |
| VPS con GPU | 16 GB RAM + GPU 8GB+ (ej. RTX A4000) | 2–5 segundos | USD 100–300 |

**Para el MVP (meta: 10 postulantes registrados) alcanza CPU**, con una condición de diseño:
el análisis del CV **no puede ser sincrónico** en el request HTTP (nadie espera 60 segundos
mirando un spinner). Ver sección 6.4 (procesamiento en segundo plano).

> **Alternativa que hay que dejar escrita aunque no se elija:** usar una API hosteada que sirva
> Llama (Groq, Together AI, etc.) — latencia de 1-2 segundos, costo por token, cero
> administración. El Acta lista como riesgo la *"dependencia de servicios LLM en la nube"*,
> y self-host elimina ese riesgo y el de privacidad (los CV tienen datos personales y nunca
> salen del VPS propio). Pero si el VPS-CPU resulta demasiado lento en la práctica, esta es
> la vía de escape sin reescribir código: la integración por HTTP (sección 6) es la misma,
> solo cambia la URL y el header de autenticación.

## 3. Instalación del servidor de inferencia (Ollama) en el VPS

Ollama es la opción más simple para servir Llama por HTTP. Asumimos VPS Ubuntu 22.04/24.04.

```bash
# 3.1 — Instalar
curl -fsSL https://ollama.com/install.sh | sh

# 3.2 — Descargar el modelo (una sola vez, ~5 GB)
ollama pull llama3.1:8b

# 3.3 — Probar en el momento
ollama run llama3.1:8b "Extraé las habilidades de: 'Sé Python y algo de Excel'. Respondé solo JSON."
```

Ollama queda corriendo como servicio systemd escuchando en `http://127.0.0.1:11434`.

### 3.4 — Seguridad (NO saltearse)

- **Nunca exponer el puerto 11434 a internet.** Ollama no tiene autenticación. Debe escuchar
  solo en `127.0.0.1` (es el default — verificar con `ss -tlnp | grep 11434`).
- Si Django corre en **el mismo VPS**: se conecta a `127.0.0.1:11434` directo. Fin.
- Si Django corre en **otro servidor**: NO abrir el puerto; hacer un túnel (WireGuard/tailscale)
  o poner un reverse proxy (nginx) con autenticación por token delante.
- Firewall básico del VPS: `ufw allow 22,80,443/tcp && ufw enable`.

### 3.5 — Ajustes de systemd útiles

```bash
sudo systemctl edit ollama
```
```ini
[Service]
# mantener el modelo cargado en RAM 1h tras el último uso (evita re-carga de ~30s)
Environment="OLLAMA_KEEP_ALIVE=1h"
# 1 request a la vez: en CPU, procesar en paralelo empeora TODO
Environment="OLLAMA_NUM_PARALLEL=1"
```
```bash
sudo systemctl restart ollama
```

## 4. El contrato JSON: qué le pedimos exactamente al LLM

Definir el schema ANTES de escribir prompts. El LLM recibe texto de CV y devuelve **solo esto**:

```json
{
  "habilidades": ["python", "excel", "atencion al cliente"],
  "nivel_educativo": "secundario completo",
  "anios_experiencia": 3,
  "areas_experiencia": ["administracion", "ventas"],
  "idiomas": ["espanol", "ingles basico"]
}
```

Reglas del contrato:
- `habilidades` ya normalizadas: minúsculas, sin acentos, singular. (El código Python
  re-normaliza igual después — defensa en profundidad, regla de "Unicidad de Habilidades" del MVP.)
- Si un dato no está en el CV: `null` o lista vacía. **Prohibido inventar.**
- Ningún campo de "cursos recomendados" — eso no es tarea del LLM (sección 0).

## 5. Los prompts (esto ES el "entrenamiento" del MVP)

### 5.1 — System prompt de extracción

```text
Sos un extractor de datos de currículums para una bolsa de trabajo del Chaco, Argentina.
Tu única tarea: leer el texto de un CV y devolver un JSON válido con este schema exacto:
{"habilidades": [...], "nivel_educativo": ..., "anios_experiencia": ..., "areas_experiencia": [...], "idiomas": [...]}

Reglas estrictas:
1. Respondé SOLO el JSON. Sin explicación, sin markdown, sin texto antes ni después.
2. habilidades: en minúsculas, sin acentos, términos simples ("python", no "Programación en Python 3").
3. Si el CV no menciona un dato, usá null (o lista vacía). NUNCA inventes información.
4. Incluí habilidades blandas solo si están explícitas en el CV.
```

### 5.2 — Few-shot: 2-3 ejemplos dentro del prompt

Agregar al prompt un par de pares (CV de ejemplo → JSON esperado) con casos difíciles reales
del dominio: un CV desordenado, uno con habilidades implícitas ("manejo de caja" → cajero),
uno gastronómico (el catálogo IEN incluye Gastronomía, no solo software). Esto sube la
precisión más que cualquier otro ajuste. Los ejemplos se guardan versionados en el repo
(p. ej. `apps/analisis_ia/prompts/`), no hardcodeados en un string perdido.

### 5.3 — Forzar JSON

Ollama soporta `"format": "json"` en el request — obliga sintaxis JSON válida. Igual el código
debe validar el *contenido* (schema) porque JSON válido ≠ schema correcto. Usar temperatura
baja (`0.1–0.2`): extracción quiere consistencia, no creatividad.

### 5.4 — Prompt secundario (opcional): redactar la devolución al postulante

Segundo prompt, separado, que recibe la brecha YA calculada por Python y los cursos YA
elegidos por la query, y solo redacta: *"Te faltan 2 de 5 habilidades para esta oferta:
atención al cliente y Excel. El curso 'Gestión Contable' del IEN cubre Excel..."*.
El LLM acá es un redactor, no un decisor. Si este paso falla, se muestra la versión
tabular sin texto — degradación elegante.

## 6. Cómo queda en el código Django (arquitectura propuesta)

> Ilustrativo — los nombres siguen las convenciones del repo: apps en `apps/`,
> capa de servicios en `services.py` (plural), imports sin prefijo `apps.`.

### 6.1 — Nueva app: `apps/analisis_ia/`

```
apps/analisis_ia/
├── models.py          # AnalisisCV (resultado persistido del análisis)
├── services.py        # lógica de negocio: analizar_cv, calcular_brecha, recomendar_cursos
├── llm_client.py      # ÚNICO archivo que sabe que Ollama existe (Adapter)
├── prompts/
│   ├── extraccion_system.txt
│   └── extraccion_ejemplos.json
└── tests.py
```

`llm_client.py` es un **Adapter**: si mañana cambian Ollama por Groq o por otra API, se toca
solo este archivo. Nadie más en el proyecto conoce URLs ni formatos del LLM.

### 6.2 — Configuración (settings + env)

```python
# ientrabajo/settings/base.py
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.1:8b')
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '120'))  # segundos; CPU es lento
```

### 6.3 — El cliente (esqueleto)

```python
# apps/analisis_ia/llm_client.py
import json, requests
from django.conf import settings

class LLMError(Exception):
    """El LLM no respondió o respondió algo inusable."""

def extraer_datos_cv(texto_cv: str) -> dict:
    system = _leer_prompt('extraccion_system.txt')
    respuesta = requests.post(
        f'{settings.OLLAMA_URL}/api/chat',
        json={
            'model': settings.OLLAMA_MODEL,
            'messages': [
                {'role': 'system', 'content': system},
                # ... few-shot ...
                {'role': 'user', 'content': texto_cv[:8000]},  # truncar: CVs gigantes rompen el contexto
            ],
            'format': 'json',
            'options': {'temperature': 0.1},
            'stream': False,
        },
        timeout=settings.OLLAMA_TIMEOUT,
    )
    respuesta.raise_for_status()
    datos = json.loads(respuesta.json()['message']['content'])
    _validar_schema(datos)   # KeyError/tipo incorrecto -> LLMError
    return datos
```

### 6.4 — El pipeline completo en `services.py`

```python
# apps/analisis_ia/services.py  (esqueleto conceptual)

def analizar_cv(postulante):
    texto = extraer_texto_pdf(postulante.cv.path)          # pdfplumber, sin LLM
    datos = llm_client.extraer_datos_cv(texto)             # LLM
    habilidades = {normalizar(h) for h in datos['habilidades']}  # regla del MVP
    return AnalisisCV.objects.create(postulante=postulante, habilidades=list(habilidades), ...)

def calcular_match(analisis, oferta):
    requeridas = {normalizar(h) for h in oferta.habilidades_lista()}
    tiene = requeridas & set(analisis.habilidades)
    brecha = requeridas - set(analisis.habilidades)
    porcentaje = round(100 * len(tiene) / len(requeridas)) if requeridas else 0
    return porcentaje, sorted(brecha)      # "Tenés 3 de 5 habilidades (60%)"

def recomendar_cursos(postulante, brecha):
    return (Curso.objects
            .filter(habilidades__nombre__in=brecha)        # cursos que enseñan lo que falta
            .exclude(inscripciones__postulante=postulante) # riesgo del Acta: ya lo hizo
            .distinct())
```

**Dependencia de datos clave:** para que `recomendar_cursos` funcione, cada `Curso` del
catálogo debe tener sus **habilidades/tags cargados** (M2M `Curso ↔ Habilidad` o equivalente).
Ese trabajo de carga es administrativo pero es EL cimiento del recomendador — sin tags en los
cursos, no hay recomendación posible, con o sin IA.

### 6.5 — Procesamiento en segundo plano (obligatorio en VPS-CPU)

60-90 segundos no pueden vivir dentro de un request. Opciones de menor a mayor complejidad:

1. **MVP pragmático:** al subir el CV, guardar `AnalisisCV(estado='pendiente')` y correr un
   **management command** en loop (o cron cada minuto) que procese pendientes:
   `python manage.py procesar_analisis_pendientes`. El front muestra "Analizando tu CV..."
   y consulta el estado. Cero dependencias nuevas.
2. **Fase 2:** Celery + Redis si el volumen crece. No para el MVP de 10 usuarios.

El modelo `AnalisisCV` con campo `estado` (`pendiente/procesando/completado/error`) — el mismo
patrón TextChoices que ya usa `Oferente.estado_validacion`.

### 6.6 — Manejo de fallos (riesgo del Acta: "caída del VPS/servicio")

- Timeout o Ollama caído → el análisis queda `pendiente`, se reintenta después (máx. N intentos,
  luego `error`).
- JSON inválido o schema roto → 1 reintento; si persiste, `error` + log del texto crudo para
  diagnóstico.
- **Fallback funcional:** con el LLM caído, la plataforma sigue viva — ofertas visibles,
  registro funciona, solo el score aparece como "pendiente". Nunca un 500 por culpa del LLM.

## 7. Extracción de texto del PDF (el paso que todos subestiman)

- `pdfplumber` para PDFs digitales (la mayoría de los CV de Canva/Word exportado).
- CVs escaneados (foto del papel) → necesitan OCR (`pytesseract`). Decisión de MVP razonable:
  **no soportar escaneados** y validar al subir: si `extract_text()` devuelve casi nada,
  mensaje al usuario "Subí un PDF de texto, no una foto". El Acta ya lo prevé como restricción
  (*"el análisis estará limitado por la calidad y formato del archivo"*).
- Límite de tamaño (ej. 5 MB) y de páginas (ej. 5) al subir.

## 8. Testing y evaluación (hito "testing del algoritmo" del Acta)

### 8.1 — Tests determinísticos (los baratos, escribir primero)
`normalizar()`, `calcular_match()`, `recomendar_cursos()` con datos fijos — unit tests Django
comunes. Acá vive la mayor parte de la lógica, por diseño (sección 0).

### 8.2 — Golden set para el LLM
- 15-20 CVs ficticios variados (el Acta dice que los datos de prueba son ficticios):
  distintos rubros del catálogo IEN, distintos formatos, uno desordenado, uno pobre.
- Para cada uno, el JSON esperado escrito a mano (el "gold").
- Script que corre los 20 contra el LLM y mide: % de habilidades esperadas encontradas
  (recall) y % de habilidades inventadas (precisión). **Meta razonable: >85% recall,
  <5% inventadas.**
- Se corre cada vez que se toca un prompt. Los prompts se versionan en git justamente
  para esto: un cambio de prompt es un cambio de comportamiento, se testea como el código.

### 8.3 — Test de integración con mock
Los tests de Django **no** llaman a Ollama: se mockea `llm_client.extraer_datos_cv` y se
prueba el pipeline completo (PDF → análisis → match → recomendación). El golden set (8.2)
es el único que toca el LLM real, y corre aparte.

## 9. "Entrenar" el modelo: qué significa de verdad acá

Hay tres niveles, y conviene tener claro cuál corresponde:

| Nivel | Qué es | ¿Para IEN Trabajo? |
|---|---|---|
| **Prompt engineering + few-shot** | Instrucciones y ejemplos en el prompt. Cambio en minutos, gratis. | ✅ **Es TODO lo que necesita el MVP** |
| **RAG** (retrieval) | Inyectar datos externos en el prompt (ej. catálogo de cursos). | ⚠️ No hace falta: el catálogo entra en una query SQL; no hay corpus grande que buscar |
| **Fine-tuning (LoRA)** | Re-entrenar pesos del modelo con dataset propio. | ❌ Para el MVP no — recién tiene sentido en fase 2, y solo si el golden set muestra techo |

**Por qué NO fine-tunear ahora:** (1) no hay dataset — se necesitan 500–1000+ ejemplos
CV→JSON de calidad, y el proyecto arranca con datos ficticios; (2) cuesta GPU y tiempo;
(3) congela el comportamiento: cada mejora exige re-entrenar, mientras que un prompt se
mejora en minutos; (4) Llama 3.1 8B ya hace extracción JSON en español muy bien con
few-shot. Fine-tunear un modelo para una tarea que resuelve el prompting es el error
clásico de sobre-ingeniería en proyectos con LLM.

### 9.1 — El camino de fine-tuning documentado (fase 2, si algún día hace falta)

Señal para activarlo: el golden set se estanca bajo la meta tras iterar prompts, o se
necesita un modelo más chico (3B) con calidad de 8B por costos de VPS.

1. **Dataset:** recolectar pares reales (texto de CV → JSON corregido a mano). Los análisis
   corregidos por el admin del IEN durante la operación son la fuente natural. Formato JSONL:
   `{"messages": [{"role":"system",...},{"role":"user","content":cv},{"role":"assistant","content":json_correcto}]}`.
   Mínimo útil: ~500 ejemplos. **Anonimizar** (los CV tienen datos personales).
2. **Método: LoRA/QLoRA** — entrena adaptadores chicos en vez del modelo entero. Herramientas:
   Unsloth (la más simple, corre en Colab con GPU T4 gratis para 8B QLoRA) o Axolotl.
3. **Entrenar:** 1-3 épocas, evaluando contra un split de validación (nunca entrenar con el
   golden set — es el examen, no el apunte).
4. **Exportar a GGUF** (formato de Ollama; Unsloth exporta directo) y cargarlo:
   `ollama create ien-extractor -f Modelfile` → cambiar `OLLAMA_MODEL=ien-extractor` en el
   `.env`. **Cero cambios de código** — para eso existe el Adapter de la sección 6.1.
5. **Regresión:** correr el golden set contra el modelo nuevo ANTES de pisar el viejo.

## 10. Privacidad y seguridad de datos (riesgo del Acta: filtración de datos sensibles)

- Self-host = los CV **nunca salen del VPS**. Es el argumento decisivo frente a APIs de
  terceros para datos personales — dejarlo escrito en la documentación del proyecto.
- El texto de CVs no se loguea completo (logs con los primeros N caracteres si hace falta debug).
- HTTPS en la plataforma (certbot/Let's Encrypt), backups del VPS, y `MEDIA_ROOT` (los PDF
  subidos) fuera del webroot público con acceso controlado por vista, no por URL directa.

## 11. Checklist de implementación (orden recomendado)

- [ ] 1. Cargar habilidades/tags en el catálogo de cursos (sin esto no hay recomendador — §6.4)
- [ ] 2. VPS: instalar Ollama + `llama3.1:8b`, verificar que responde por curl (§3)
- [ ] 3. Definir contrato JSON y escribir prompts + few-shot en `prompts/` (§4-5)
- [ ] 4. Probar los prompts a mano con 3-4 CVs ficticios (iterar acá es barato)
- [ ] 5. App `analisis_ia`: modelo `AnalisisCV` con estados + migración (§6.1)
- [ ] 6. `llm_client.py` con timeout, validación de schema y `LLMError` (§6.3)
- [ ] 7. Extracción de PDF con validación de "PDF de texto" (§7)
- [ ] 8. `services.py`: pipeline analizar → normalizar → match → brecha → cursos (§6.4)
- [ ] 9. Management command de procesamiento en background (§6.5)
- [ ] 10. Vistas/templates: subir CV, "analizando...", resultado con % y tarjetas de cursos
- [ ] 11. Tests unitarios del matching + integración con mock (§8.1, 8.3)
- [ ] 12. Golden set de 15-20 CVs y script de evaluación (§8.2)
- [ ] 13. Hardening: firewall, HTTPS, límites de subida, no exponer 11434 (§3.4, §10)
- [ ] 14. Prueba de carga realista: 10 CVs seguidos en el VPS real, medir tiempos
