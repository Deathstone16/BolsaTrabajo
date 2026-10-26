"""Regenera el diagrama lógico en SVG y PNG sin servicios externos.

Uso: python scripts/generar_diagrama_arquitectura.py
Requiere Pillow, declarado en requirements.txt. No lee ni modifica la imagen guía.
"""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'arquitectura' / 'diagramas'
WIDTH, HEIGHT, SCALE = 1200, 1320, 2
NAVY, GRAY, BLUE, BORDER = '#16324f', '#526477', '#edf4fc', '#a6c6e6'


def font(size, bold=False):
    names = ([
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
    ] if bold else [
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'C:/Windows/Fonts/arial.ttf',
    ])
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size * SCALE)
    return ImageFont.load_default(size=size * SCALE)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    canvas = Image.new('RGB', (WIDTH * SCALE, HEIGHT * SCALE), 'white')
    draw = ImageDraw.Draw(canvas)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
           '<title id="title">Arquitectura lógica simplificada de Bolsa de Trabajo IEN</title>',
           '<desc id="desc">Usuarios se conectan a Django SSR y Channels. Django usa PostgreSQL y se integra con FastAPI mediante despachadores. FastAPI coordina Celery y Redis; los workers consultan al proveedor LLM. PostgreSQL no se conecta directamente al proveedor.</desc>',
           '<rect width="1200" height="1320" fill="white"/>']

    def text(x, y, value, size=22, bold=False, center=False, color=NAVY):
        draw.text((x*SCALE, y*SCALE), value, font=font(size, bold), fill=color, anchor='mt' if center else 'lt')
        anchor = 'middle' if center else 'start'
        weight = '700' if bold else '400'
        svg.append(f'<text x="{x}" y="{y+size*.84}" text-anchor="{anchor}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(value)}</text>')

    def box(x, y, w, h, title, lines, highlighted=False):
        fill = BLUE if highlighted else '#fbfcfe'
        draw.rounded_rectangle((x*SCALE,y*SCALE,(x+w)*SCALE,(y+h)*SCALE), radius=18*SCALE, fill=fill, outline=BORDER, width=2*SCALE)
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{fill}" stroke="{BORDER}" stroke-width="2"/>')
        text(x+w/2,y+24,title,27,True,True)
        for i,line in enumerate(lines):
            text(x+w/2,y+66+i*29,line,20,center=True,color=GRAY)

    def arrow(x1,y1,x2,y2,label,lx,ly):
        color='#6c8195'
        draw.line((x1*SCALE,y1*SCALE,x2*SCALE,y2*SCALE),fill=color,width=2*SCALE)
        svg.append(f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" stroke="{color}" stroke-width="2"/>')
        # All connectors are vertical and bidirectional.
        for y,direction in [(y1,1),(y2,-1)]:
            points=[(x1,y),(x1-7,y+direction*11),(x1+7,y+direction*11)]
            draw.polygon([(x*SCALE,yy*SCALE) for x,yy in points],fill=color)
            svg.append('<polygon points="'+' '.join(f'{x},{yy}' for x,yy in points)+f'" fill="{color}"/>')
        text(lx,ly,label,18,color=GRAY)

    text(72,52,'Arquitectura lógica simplificada',36,True)
    text(72,101,'Bolsa de Trabajo IEN · Interfaz, persistencia y procesamiento con IA',21,color=GRAY)
    box(72,160,1056,104,'Usuarios / Navegador',['Interfaz web'])
    box(72,350,1056,144,'Django SSR + Channels',[
        'Lógica de negocio, vistas, autenticación y comunicación en tiempo real',
        'Despachadores Django para extracción y compatibilidad',
    ],True)
    box(72,594,360,144,'PostgreSQL',['Persistencia del sistema','SQLite disponible en desarrollo'])
    box(610,594,518,144,'FastAPI',['Servicio de integración con LLM','Solicitudes, resultados y callbacks'])
    box(610,838,518,144,'Celery + Redis',['Cola de tareas y workers','Procesamiento asíncrono'])
    box(610,1082,518,144,'Proveedor / Modelo LLM',['Procesamiento mediante IA'])
    arrow(600,278,600,336,'HTTPS / WebSocket',620,301)
    arrow(252,508,252,580,'Lectura / escritura',272,535)
    arrow(869,508,869,580,'HTTP / WebSocket',888,535)
    arrow(869,752,869,824,'Cola / resultados',888,779)
    arrow(869,996,869,1068,'Consulta / respuesta',888,1023)
    text(72,846,'Cómo leer el esquema',23,True)
    for i,line in enumerate([
        'Django controla el acceso a los datos.',
        'FastAPI integra el procesamiento de IA.',
        'Celery ejecuta trabajos en segundo plano.',
        'Redis también se usa para Channels',
        'y caché, según la configuración.',
        '',
        'El detalle de transportes y límites',
        'está en arquitectura/general.md.',
    ]):
        text(72,892+i*30,line,18,color=GRAY)
    text(72,1274,'Vista simplificada. Los servicios de IA se mantienen en el repositorio externo.',18,color=GRAY)
    svg.append('</svg>')
    (OUT/'arquitectura-logica.svg').write_text('\n'.join(svg)+'\n',encoding='utf-8')
    canvas.save(OUT/'arquitectura-logica.png',optimize=True)
    print('Generados SVG y PNG en',OUT)


if __name__ == '__main__':
    main()
