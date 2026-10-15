"""Una comparación real de datos sintéticos; consume una llamada Groq."""
import json
import time
from pathlib import Path
from uuid import uuid4

import requests
from dotenv import dotenv_values
from websockets.sync.client import connect

env = dotenv_values(Path(__file__).resolve().parents[1] / '.env')
request_id = str(uuid4())
headers = {'Authorization': f"Bearer {env['MATCH_API_TOKEN']}"}
payload = {
    'request_id': request_id,
    'candidate_profile': {'profile_id': 'synthetic-smoke', 'headline': 'Python developer',
                          'skills': [{'name': 'Python', 'level': 'advanced', 'years_experience': 4,
                                      'evidence': ['Built Python applications for four years.']}]},
    'job_offer': {'offer_id': 'synthetic-smoke', 'title': 'Python developer',
                  'requirements': [{'name': 'Python', 'minimum_level': 'intermediate', 'mandatory': True}]},
    'metadata': {'candidate_profile_hash': 'a' * 64, 'candidate_profile_version': 1,
                 'offer_profile_hash': 'b' * 64, 'offer_profile_version': 1,
                 'rubric_version': 'match-rubric.v1', 'matcher_prompt_version': 'match-rubric.v1',
                 'model': env['MATCH_MODEL_VERSION']},
}
with connect('ws://127.0.0.1:8002/api/v1/ws/v1/matches', additional_headers=headers, open_timeout=10) as socket:
    socket.send(json.dumps({'type': 'match.start', 'payload': payload}))
    socket.recv(timeout=15)
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    response = requests.get(f'http://127.0.0.1:8002/api/v1/matches/{request_id}', headers=headers, timeout=10)
    response.raise_for_status()
    job = response.json()
    if job['status'] == 'completed':
        result = job['result']
        print(json.dumps({'status': 'completed', 'match_percentage': result['match_percentage'],
                          'coverage_percentage': result['coverage_percentage'],
                          'confidence_percentage': result['confidence_percentage'],
                          'provider_model': job.get('provider_model')}, ensure_ascii=False))
        break
    if job['status'] == 'failed':
        raise SystemExit('La comparación sintética falló. Revisar el log del worker.')
    time.sleep(1)
else:
    raise SystemExit('La comparación sigue pendiente; se agotó el tiempo de comprobación.')
