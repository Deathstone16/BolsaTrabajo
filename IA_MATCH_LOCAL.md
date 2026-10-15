# Rama ia-match: comparación CV–oferta con Groq

Las ramas anteriores se conservan. Django parte de `ia-aplicada`; la API integra
esa rama con `feature/habilidades-blandas-y-notificacion-cv` de Benja. La comparación vive dentro de la misma API de CV, en `api/ia_api/backend`. No se inicia un servicio de compatibilidad separado.

## Windows

Requiere Docker Desktop iniciado y los entornos `.venv` con sus requirements.
Cada repositorio incluye `ien_contracts/` con los modelos JSON versionados usados
por el protocolo; no hace falta copiar archivos desde `C:\IEN\contracts`.

```powershell
cd C:\IEN\repositorio\BolsaTrabajo
.\scripts\start_ia_match.ps1
# Detener los procesos iniciados por el script:
.\scripts\stop_ia_match.ps1
```

El inicio respalda SQLite, aplica migraciones, sincroniza tokens locales e inicia
Django ASGI, una API de CV y compatibilidad, un worker Celery compartido y dos despachadores.
Los workers usan `--pool=solo` para Windows. Redis queda en Docker al detener
los procesos. Logs en cada repositorio; no subir `.env`, PID ni bases de datos.

- Web: http://127.0.0.1:8000/
- API única de CV y compatibilidad: http://127.0.0.1:8001/docs

## Probar como postulante

1. Iniciar sesión, cargar un CV PDF y pulsar Analizar CV en Mi perfil.
2. Esperar el análisis. La API entrega un perfil estructurado y luego emite el
   aviso de Benja. El polling sigue disponible si se pierde el WebSocket.
3. Publicar/aprobar una oferta y esperar a que se estructuren sus requisitos.
4. Abrir el detalle y pulsar Calcular compatibilidad. Se muestra porcentaje,
   cobertura, confianza estimada y coincidencia por habilidad.

Para una oferta histórica sin perfil, solicitar su extracción desde el shell:

```python
from ofertas.models import Oferta
from ia.workflow import request_offer_extraction
request_offer_extraction(Oferta.objects.get(pk=ID_DE_LA_OFERTA))
```

El resultado se guarda por usuario, oferta, versiones, hashes y modelo. Recargar
retoma la consulta. Repetirla reutiliza el resultado; editar perfiles invalida su
visualización para la nueva versión. Los trabajos conservan snapshots inmutables.

Ponderación inicial: habilidades 45%, experiencia 25%, formación e idiomas 15%,
preferencias 15%. El porcentaje indica ajuste a requisitos, no probabilidad de
contratación. La confianza proviene del modelo y se presenta como estimación.

## Pruebas

```powershell
.\.venv\Scripts\python.exe manage.py test ia matching ofertas moderacion usuarios -v 1
```

Ejecutar también `python -m unittest discover -s tests -v` con el entorno de la
API unificada. Las pruebas no llaman a proveedores reales. Para una prueba real usar
datos sintéticos o un CV que el usuario decida analizar.
