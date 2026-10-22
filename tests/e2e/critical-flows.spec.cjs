const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const stateFile = process.env.E2E_STATE_FILE;
if (!stateFile) throw new Error('Ejecutar con npm run test:e2e para preparar y limpiar los datos sintéticos.');
const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
const root = path.resolve(__dirname, '../..');
const python = process.env.E2E_PYTHON || path.join(root, '.venv', 'Scripts', 'python.exe');
const cvText = 'CV sintético de pruebas. Usé Python y Django durante tres años. Expliqué procedimientos a clientes y coordiné entregas con colegas.';
function status() {
  const text = execFileSync(python, ['scripts/e2e_fixture.py', 'status', '--state', stateFile], {
    cwd: root, env: { ...process.env, PYTHONUTF8: '1' }, encoding: 'utf8', timeout: 30_000,
  });
  return JSON.parse(text.trim());
}
async function rememberSession(context) {
  const current = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
  const keys = (await context.cookies()).filter(cookie => cookie.name === 'sessionid').map(cookie => cookie.value);
  current.sessions = [...new Set([...(current.sessions || []), ...keys])];
  fs.writeFileSync(stateFile, JSON.stringify(current, null, 2));
}
async function login(page, role) {
  await page.goto('/usuarios/login/');
  await page.locator('input[name="email"]').fill(state.users[role].email);
  await page.locator('input[name="password"]').fill(state.password);
  await page.getByRole('button', { name: /Ingresar|Iniciar sesión/i }).click();
  await expect(page).not.toHaveURL(/\/usuarios\/login\//);
  await rememberSession(page.context());
}
async function snapshot(page, testInfo, name) {
  await testInfo.attach(name, { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' });
}
test('login, edición de requisitos y aislamiento entre empresas', async ({ page, browser }, testInfo) => {
  await login(page, 'company');
  await page.goto(`/ofertas/editar/${state.pending_offer_id}/`);
  await expect(page.getByRole('heading', { name: 'Editar oferta', exact: true })).toBeVisible();
  const title = `Oferta E2E ${state.run_id.slice(0, 8)} revisada`;
  await page.locator('input[name="titulo"]').fill(title);
  await page.getByLabel('Requisitos obligatorios', { exact: true }).fill('Python\nTrabajo en equipo');
  await page.getByLabel('Requisitos deseables', { exact: true }).fill('Django');
  await page.getByLabel('Categoría del requisito: Python', { exact: true }).selectOption('technical_skills');
  await page.getByLabel('Categoría del requisito: Trabajo en equipo', { exact: true }).selectOption('soft_skills');
  await expect(page.locator('#resumen-requisitos')).toContainText('Python');
  await snapshot(page, testInfo, 'requisitos-clasificados');
  await page.getByRole('button', { name: 'Guardar cambios', exact: true }).click();
  await expect(page).toHaveURL(/\/ofertas\/dashboard\//);
  await expect.poll(() => status().offer_title).toBe(title);
  const requirements = status().requirements;
  expect(requirements).toEqual(expect.arrayContaining([
    expect.objectContaining({ name: 'Python', category: 'technical_skills', mandatory: true }),
    expect.objectContaining({ name: 'Trabajo en equipo', category: 'soft_skills', mandatory: true }),
    expect.objectContaining({ name: 'Django', mandatory: false }),
  ]));
  const other = await browser.newContext();
  try {
    const otherPage = await other.newPage();
    await login(otherPage, 'other_company');
    await otherPage.goto(`/ofertas/editar/${state.pending_offer_id}/`);
    await expect(otherPage).toHaveURL(/\/ofertas\/dashboard\//);
    expect(status().offer_title).toBe(title);
  } finally { await other.close(); }
});

test('oferta legacy avisa que los requisitos deben revisarse y oculta el formulario de match', async ({ page }, testInfo) => {
  await login(page, 'candidate');
  await page.goto(`/ofertas/${state.legacy_offer_id}/`);

  await expect(page.locator('#match-requisitos-pendientes')).toBeVisible();
  await expect(page.locator('#match-requisitos-pendientes')).toContainText('La empresa debe actualizar los requisitos');
  await expect(page.locator('#match-form')).toBeHidden();
  await snapshot(page, testInfo, 'oferta-legacy-requiere-revision');
});

test('match completado se renderiza desde el servidor, conserva 0% y abre el detalle sin calcular otra vez', async ({ browser }, testInfo) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  try {
    const page = await context.newPage();
    await login(page, 'other');
    await page.goto(`/ofertas/${state.ui_completed_offer_id}/`);
    await expect(page.locator('#match-percentage')).toHaveText('0%');
    await expect(page.locator('#match-details-action')).toBeVisible();
    await expect(page.locator('#match-details-link')).toBeVisible();
    await expect(page.locator('#match-form')).toBeHidden();
    const href = await page.locator('#match-details-link').getAttribute('href');
    expect(href).toMatch(/^\/matching\/resultado\/[0-9a-f-]+\/$/i);
    expect(href).toContain(state.ui_match_request_id);

    const detail = await context.newPage();
    await detail.goto(href);
    await expect(detail.getByRole('heading', { name: 'Detalles del match', exact: true })).toBeVisible();
    await expect(detail.getByRole('heading', { name: 'Compatibilidad por área', exact: true })).toBeVisible();
    await expect(detail.getByText(state.course_skill_name, { exact: true }).first()).toBeVisible();
    const recommendations = detail.locator('#course-recommendations');
    await expect(recommendations).toBeVisible();
    const courseCards = recommendations.locator('.course-recommendation');
    await expect(courseCards).toHaveCount(2);
    await expect(courseCards.nth(0)).toHaveAttribute('data-course-id', String(state.course_excel_id));
    await expect(courseCards.nth(1)).toHaveAttribute('data-course-id', String(state.course_admin_id));
    await expect(courseCards.nth(0)).toContainText(/Excel/i);
    await expect(courseCards.nth(1)).toContainText(/Excel/i);
    await snapshot(detail, testInfo, 'cursos-recomendados-excel');
    await detail.setViewportSize({ width: 390, height: 844 });
    const recommendationsBox = await recommendations.boundingBox();
    expect(recommendationsBox.width).toBeLessThanOrEqual(390);
    await snapshot(detail, testInfo, 'cursos-recomendados-movil');
    const recommendedCourseLink = courseCards.nth(0).getByRole('link', { name: `Ver curso: ${state.course_excel_name}`, exact: true });
    await expect(recommendedCourseLink).toBeVisible();
    await recommendedCourseLink.click();
    await expect(detail).toHaveURL(`/cursos/${state.course_excel_id}/`);
    await expect(detail.getByRole('heading', { name: state.course_excel_name, exact: true })).toBeVisible();

    const anonymous = await browser.newContext({ javaScriptEnabled: false });
    try {
      const response = await anonymous.request.get(new URL(href, testInfo.project.use.baseURL).href, { maxRedirects: 0 });
      expect(response.status()).toBe(302);
    } finally { await anonymous.close(); }
    const wrongOwner = await browser.newContext({ javaScriptEnabled: false });
    try {
      const wrongPage = await wrongOwner.newPage();
      await login(wrongPage, 'candidate');
      const response = await wrongPage.request.get(href);
      expect(response.status()).toBe(404);
    } finally { await wrongOwner.close(); }
  } finally { await context.close(); }
});

test('carga de CV, validación de formato y privacidad entre cuentas', async ({ page, browser }, testInfo) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page, 'candidate');
  await page.goto('/usuarios/mi-perfil/');
  const uploadResponse = page.waitForResponse(response => response.url().endsWith('/usuarios/mi-perfil/') && response.request().method() === 'POST');
  await page.locator('#cv-input').setInputFiles({ name: 'cv-e2e-sintetico.txt', mimeType: 'text/plain', buffer: Buffer.from(cvText) });
  const uploaded = await uploadResponse;
  expect(uploaded.status()).toBe(200);
  // The upload immediately reloads the page; verify the rendered version and
  // persistence instead of reading a response body after its document unloads.
  await expect(page.locator('#form-analizar-cv')).toHaveAttribute('data-version-cv-id', /^[1-9]\d*$/);
  const uploadedVersion = Number(await page.locator('#form-analizar-cv').getAttribute('data-version-cv-id'));
  expect(status().cv_version_id).toBe(uploadedVersion);
  expect(status().new_analysis_count).toBe(0);
  const downloadURL = `/usuarios/cv/${uploadedVersion}/descargar/`;
  const own = await page.request.get(downloadURL);
  expect(own.status()).toBe(200);
  expect((await own.body()).toString()).toBe(cvText);
  const anonymous = await browser.newContext();
  const other = await browser.newContext();
  try {
    const anon = await anonymous.request.get(new URL(downloadURL, testInfo.project.use.baseURL).href, { maxRedirects: 0 });
    expect(anon.status()).toBe(302);
    const otherPage = await other.newPage();
    await login(otherPage, 'other');
    expect((await otherPage.request.get(downloadURL)).status()).toBe(404);
    const direct = await anonymous.request.get(new URL('/media/postulantes/cv/cv-e2e-sintetico.txt', testInfo.project.use.baseURL).href);
    expect(direct.status()).toBe(404);
  } finally { await anonymous.close(); await other.close(); }
  const versionBefore = status().cv_version_id;
  const rejectedResponse = page.waitForResponse(response => response.url().endsWith('/usuarios/mi-perfil/') && response.request().method() === 'POST');
  await page.locator('#cv-input').setInputFiles({ name: 'archivo-falso.pdf', mimeType: 'application/pdf', buffer: Buffer.from('Esto no es un documento PDF.') });
  const rejected = await rejectedResponse;
  const rejectedBody = await rejected.json();
  expect(rejectedBody.success).toBe(false);
  await expect(page.getByRole('alert').filter({ hasText: rejectedBody.mensaje })).toBeVisible();
  expect(status().cv_version_id).toBe(versionBefore);
  expect(errors).toEqual([]);
  await snapshot(page, testInfo, 'cv-privado-y-rechazo-de-formato');
});

test('E2E real: analizar CV, mostrar habilidades, calcular match y bloquear el CV obsoleto', async ({ page }, testInfo) => {
  test.skip(process.env.E2E_REAL_IA !== '1', 'Requiere npm run test:e2e:live: consume cuota del proveedor.');
  test.setTimeout(1_300_000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page, 'candidate');
  await page.goto('/usuarios/mi-perfil/');
  const analysisResponse = page.waitForResponse(response => response.url().includes('/ia/solicitar-analisis/') && response.request().method() === 'POST');
  await page.locator('#form-analizar-cv button[type="submit"]').click();
  const accepted = await analysisResponse;
  expect(accepted.status()).toBe(202);
  const acceptedBody = await accepted.json();
  const analysisId = acceptedBody.analisis_id;
  console.log('E2E IA real: análisis solicitado desde el navegador.');
  await expect(page.locator('#analisis-estado')).toBeVisible();
  await expect.poll(async () => {
    const response = await page.request.get(`/ia/analisis/${analysisId}/estado/`);
    expect(response.status()).toBe(200);
    return (await response.json()).estado;
  }, { timeout: 700_000, intervals: [2000, 4000, 8000] }).toBe('completado');
  console.log('E2E IA real: extracción de CV y callback completados.');
  await expect(page.locator('#boton-ver-resultado')).not.toHaveAttribute('aria-disabled', 'true', { timeout: 30_000 });
  await page.reload();
  await expect(page.locator('#habilidades-blandas-perfil')).toBeVisible();
  await expect(page.locator('#habilidades-blandas-perfil')).not.toContainText('Inferida');
  expect(status().soft_count).toBeGreaterThan(0);
  expect(status().cv_profile_schema).toBe('candidate-profile.v2');
  await snapshot(page, testInfo, 'perfil-analizado-real');
  await page.goto('/usuarios/mi-perfil/');
  await page.locator('#boton-ver-resultado').click();
  await expect(page.locator('#habilidades-blandas-cv')).toBeVisible();
  await expect(page.locator('#habilidades-blandas-cv')).not.toContainText('Inferida a partir');
  await expect.poll(() => status().offer_profile_state, { timeout: 400_000, intervals: [2000, 4000, 8000] }).toBe('ready');
  expect(status().offer_profile_schema).toBe('job-offer.v2');
  console.log('E2E IA real: oferta lista, calculando compatibilidad desde el navegador.');
  await page.goto(`/ofertas/${state.live_offer_id}/`);
  await expect(page.locator('#match-card')).toHaveAttribute('data-config-hash', /.+/);
  await page.addInitScript(() => {
    window.__matchPercentFrames = [];
    const capture = () => {
      const node = document.querySelector('#match-percentage');
      if (!node) return;
      const value = node.textContent.trim();
      if (window.__matchPercentFrames.at(-1) !== value) window.__matchPercentFrames.push(value);
    };
    new MutationObserver(capture).observe(document, { subtree: true, childList: true, characterData: true });
    document.addEventListener('DOMContentLoaded', capture);
  });
  const matchResponse = page.waitForResponse(response => response.url().includes(`/matching/ofertas/${state.live_offer_id}/calcular/`) && response.request().method() === 'POST');
  await page.locator('#match-button').click();
  const requested = await matchResponse;
  expect([200, 202]).toContain(requested.status());
  const match = await requested.json();
  await page.reload();
  await expect(page.locator('#match-percentage')).toHaveText(/^(Calculando|\d+%)$/, { timeout: 30_000 });
  await expect.poll(async () => {
    const response = await page.request.get(`/matching/estado/${match.request_id}/`);
    return (await response.json()).status;
  }, { timeout: 400_000, intervals: [2000, 4000, 8000] }).toBe('completed');
  console.log('E2E IA real: matching completado; comprobando idempotencia y vigencia.');
  await expect(page.locator('#match-percentage')).toHaveText(/^\d+%$/, { timeout: 30_000 });
  await expect(page.locator('#match-details-action')).toBeVisible();
  await expect(page.locator('#match-details-link')).toBeVisible();
  await expect(page.locator('#match-form')).toBeHidden();
  const detailHref = await page.locator('#match-details-link').getAttribute('href');
  expect(detailHref).toContain(match.request_id);
  expect(status().last_match_schema).toBe('match-result.v2');
  const finalResult = await (await page.request.get(`/matching/estado/${match.request_id}/`)).json();
  if (process.env.E2E_EXPECT_MODEL) {
    expect(finalResult.model_version).toBe(process.env.E2E_EXPECT_MODEL);
    expect(finalResult.provider_model_config).toBe(`gemini:${process.env.E2E_EXPECT_MODEL}`);
  }
  expect(finalResult.match_percentage).toBeGreaterThanOrEqual(0);
  expect(finalResult.match_percentage).toBeLessThanOrEqual(100);
  const detailPage = await page.context().newPage();
  await detailPage.goto(detailHref);
  await expect(detailPage.getByRole('heading', { name: 'Detalles del match', exact: true })).toBeVisible();
  await expect(detailPage.getByRole('heading', { name: 'Compatibilidad por área', exact: true })).toBeVisible();
  await snapshot(detailPage, testInfo, 'detalle-compatibilidad-real');
  await detailPage.close();
  await snapshot(page, testInfo, 'compatibilidad-real');
  const calcPosts = [];
  page.on('request', request => {
    if (request.method() === 'POST' && request.url().includes(`/matching/ofertas/${state.live_offer_id}/calcular/`)) calcPosts.push(request.url());
  });
  await page.evaluate(() => { window.__matchPercentFrames = []; });
  await page.reload();
  await expect(page.locator('#match-details-action')).toBeVisible();
  await expect(page.locator('#match-percentage')).toHaveText(/^\d+%$/);
  await expect(page.locator('#match-form')).toBeHidden();
  const percentFrames = await page.evaluate(() => window.__matchPercentFrames || []);
  const expectedPercentFrame = `${Math.round(Number(finalResult.match_percentage))}%`;
  expect(percentFrames.length).toBeGreaterThan(0);
  expect(percentFrames.at(-1)).toBe(expectedPercentFrame);
  expect(percentFrames).toEqual(Array(percentFrames.length).fill(expectedPercentFrame));
  expect(calcPosts).toEqual([]);
  const duplicate = await page.request.post(`/matching/ofertas/${state.live_offer_id}/calcular/`, {
    headers: { 'X-CSRFToken': (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken').value },
  });
  expect(duplicate.status()).toBe(200);
  expect((await duplicate.json()).request_id).toBe(match.request_id);
  await page.goto('/usuarios/mi-perfil/');
  const previousVersion = status().cv_version_id;
  const replacementResponse = page.waitForResponse(response => response.url().endsWith('/usuarios/mi-perfil/') && response.request().method() === 'POST');
  await page.locator('#cv-input').setInputFiles({ name: 'cv-e2e-reemplazado.txt', mimeType: 'text/plain', buffer: Buffer.from(cvText + ' Disponibilidad actualizada.') });
  expect((await replacementResponse).status()).toBe(200);
  await expect.poll(() => status().cv_version_id).not.toBe(previousVersion);
  await expect(page.locator('#form-analizar-cv')).toHaveAttribute('data-version-cv-id', String(status().cv_version_id));
  const stale = await page.request.post(`/matching/ofertas/${state.live_offer_id}/calcular/`, {
    headers: { 'X-CSRFToken': (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken').value },
  });
  expect(stale.status()).toBe(409);
  const oldAnalysis = await (await page.request.get(`/ia/analisis/${analysisId}/estado/`)).json();
  expect(oldAnalysis.es_version_actual).toBe(false);
  expect(status().new_analysis_count).toBe(1);
  expect(errors).toEqual([]);
  await snapshot(page, testInfo, 'cv-reemplazado-invalida-el-match');
});

test('perfil móvil y navegación sin desbordamiento horizontal', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 'candidate');
  await page.goto('/usuarios/mi-perfil/');
  await expect(page.locator('#cv-upload-area')).toBeVisible();
  const width = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: window.innerWidth }));
  expect(width.content).toBeLessThanOrEqual(width.viewport + 1);
  await snapshot(page, testInfo, 'perfil-movil');
});
