// Own synthetic records only; credentials and browser artifacts stay outside Git.
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

const root = path.resolve(__dirname, '..');
const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:8000';
const target = new URL(baseURL);
if (!['127.0.0.1', 'localhost', '[::1]'].includes(target.hostname)) {
  throw new Error('E2E requiere un origen localhost; no atraviesa ni modifica Cloudflare Access.');
}
const live = process.argv.includes('--live-ai');
const runDir = path.join(root, '.test-artifacts', 'e2e', `${new Date().toISOString().replace(/[:.]/g, '-')}-${randomUUID().slice(0, 8)}`);
fs.mkdirSync(runDir, { recursive: true });
const state = path.join(runDir, 'state.json');
const python = process.env.E2E_PYTHON || path.join(root, '.venv', 'Scripts', 'python.exe');
const env = { ...process.env, PYTHONUTF8: '1', E2E_STATE_FILE: state, E2E_RUN_DIR: runDir, E2E_BASE_URL: baseURL, E2E_REAL_IA: live ? '1' : '0' };
function pythonStep(command, extra = []) {
  return spawnSync(python, ['scripts/e2e_fixture.py', command, '--state', state, ...extra], {
    cwd: root, env, stdio: 'inherit', timeout: 120_000,
  });
}
let exitCode = 1;
try {
  console.log(`E2E Chromium; IA real: ${live}; artefactos: ${runDir}`);
  const seeded = pythonStep('seed', live ? ['--live-ai'] : []);
  if (seeded.error || seeded.status !== 0) throw seeded.error || new Error('Falló la preparación de identidades sintéticas.');
  const tested = spawnSync(process.execPath, [require.resolve('@playwright/test/cli'), 'test'], {
    cwd: root, env, stdio: 'inherit', timeout: 1_800_000,
  });
  if (tested.error) throw tested.error;
  exitCode = tested.status ?? 1;
} catch (error) {
  console.error(error.message);
} finally {
  if (fs.existsSync(state)) {
    let cleaned;
    let cleanupState;
    const cleanupDeadline = Date.now() + 900_000;
    do {
      cleaned = spawnSync(python, ['scripts/e2e_fixture.py', 'cleanup', '--state', state], {
        cwd: root, env, encoding: 'utf8', timeout: 60_000,
      });
      try { cleanupState = JSON.parse((cleaned.stdout || '').trim()); } catch { cleanupState = null; }
      if (cleanupState?.status !== 'waiting_for_jobs') break;
      console.log('Limpieza: esperando que terminen los trabajos propios antes de borrar sus datos.');
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5000);
    } while (Date.now() < cleanupDeadline);
    if (cleanupState) console.log(JSON.stringify(cleanupState));
    if (cleaned.error || cleaned.status !== 0 || cleanupState?.status !== 'cleaned') {
      console.error(`Limpieza incompleta. Reejecutar e2e_fixture.py cleanup --state "${state}"`);
      exitCode = 1;
    }
  }
  console.log(`Reporte: ${path.join(runDir, 'html', 'index.html')}`);
}
process.exitCode = exitCode;
