"""Resumen visible a partir de hechos ya guardados del perfil."""


def visible_profile_summary(content, legacy_summary=None):
    if isinstance(content, dict):
        summary = content.get('summary')
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
    if isinstance(legacy_summary, str) and legacy_summary.strip():
        return legacy_summary.strip()
    if not isinstance(content, dict):
        return 'No hay información suficiente para resumir este perfil.'

    titles = list(dict.fromkeys(
        row['job_title'].strip() for row in content.get('work_experience', [])
        if isinstance(row, dict) and isinstance(row.get('job_title'), str) and row['job_title'].strip()
    ))[:2]
    skills = list(dict.fromkeys(
        row['name'].strip() for row in content.get('skills', [])
        if isinstance(row, dict) and isinstance(row.get('name'), str) and row['name'].strip()
        and row.get('kind') != 'soft'
    ))[:4]
    projects = list(dict.fromkeys(
        row['name'].strip() for row in content.get('projects', [])
        if isinstance(row, dict) and isinstance(row.get('name'), str) and row['name'].strip()
    ))[:2]
    parts = []
    if titles:
        parts.append('Experiencia registrada como ' + ', '.join(titles) + '.')
    if skills:
        parts.append('Habilidades detectadas: ' + ', '.join(skills) + '.')
    if projects:
        parts.append('Proyectos registrados: ' + ', '.join(projects) + '.')
    return ' '.join(parts) or 'No hay información suficiente para resumir este perfil.'
