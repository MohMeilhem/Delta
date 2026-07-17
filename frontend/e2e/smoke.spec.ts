import { expect, test, type Page } from '@playwright/test'

/**
 * Demo-path smoke suite — the CLAUDE.md definition of done, automated:
 * sector picker → company page → baseline chart → sliders redraw the
 * analyst forecast → fair value + delta update → anomaly flags with causes
 * → one-click quarter exclusion → scenario cards.
 *
 * Assertions target seed-driven text and relative changes (never pixels,
 * never parsed numerals — the UI renders Arabic-Indic digits).
 */

// The app routes are behind the demo auth guard: seed a session before any
// page script runs so direct navigation to /app and /company/* works.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('delta-user', JSON.stringify({ email: 'e2e@delta.sa' }))
  })
})

/** The analyst fair-value readout card (label + animated number). */
function analystCard(page: Page) {
  return page.getByText('القيمة العادلة، المحلل').locator('..')
}

async function waitForModel(page: Page) {
  // the assumptions panel renders once baseline + assumptions are loaded
  await expect(page.getByLabel('معدل الخصم')).toBeVisible({ timeout: 20_000 })
}

test('landing renders and links into the app', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('link', { name: 'المنصة' }).first()).toBeVisible()
})

test('sector picker drills into a company page', async ({ page }) => {
  await page.goto('/app')
  const telecom = page.getByRole('button', { name: /الاتصالات/ })
  await expect(telecom).toBeVisible()
  await telecom.click()
  await page.getByRole('link', { name: /زين السعودية/ }).click()
  await expect(page).toHaveURL(/company\/7030/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('زين السعودية')
})

test('company page shows the baseline chart and the 7-slider panel', async ({ page }) => {
  await page.goto('/company/4190') // Jarir: clean non-bank
  await waitForModel(page)
  // chart legend (desktop viewport)
  await expect(page.getByText('الأساس الآلي').first()).toBeVisible()
  // classic sliders + the v2 metric section
  await expect(page.getByLabel('نمو الإيرادات السنوي')).toBeVisible()
  await expect(page.getByText('مؤشرات النموذج الموسع')).toBeVisible()
  for (const label of ['هامش EBITDA', 'العائد على حقوق الملكية', 'العائد على الأصول', 'النسبة الجارية']) {
    await expect(page.getByLabel(label)).toBeEnabled()
  }
})

test('dragging sliders redraws the analyst fair value live', async ({ page }) => {
  await page.goto('/company/4190')
  await waitForModel(page)
  const card = analystCard(page)
  const before = await card.innerText()

  const growth = page.getByLabel('نمو الإيرادات السنوي')
  await growth.click()
  for (let i = 0; i < 12; i++) await growth.press('ArrowRight')
  await expect.poll(() => card.innerText(), { timeout: 15_000 }).not.toBe(before)

  // a v2 slider moves it too (ROE feeds the terminal value)
  const afterGrowth = await card.innerText()
  const roe = page.getByLabel('العائد على حقوق الملكية')
  await roe.click()
  for (let i = 0; i < 20; i++) await roe.press('ArrowRight')
  await expect.poll(() => card.innerText(), { timeout: 15_000 }).not.toBe(afterGrowth)
})

test('banks disable the n.a. sliders and use the bank valuation label', async ({ page }) => {
  await page.goto('/company/1120') // Al Rajhi
  await waitForModel(page)
  await expect(page.getByLabel('هامش EBITDA')).toBeDisabled()
  await expect(page.getByLabel('النسبة الجارية')).toBeDisabled()
  await expect(page.getByText('غير متاح للبنوك').first()).toBeVisible()
  await expect(page.getByText('نموذج توزيعات (مصرف إسلامي)')).toBeVisible()
})

test('anomaly flags carry causes and one-click exclusion refits the model', async ({ page }) => {
  await page.goto('/company/7030') // Zain: embedded margin collapse
  await waitForModel(page)

  // the monitoring agent flags the margin break
  const chip = page
    .locator('div.rounded-full')
    .filter({ hasText: 'هامش صافي الربح' })
    .first()
  await expect(chip).toBeVisible({ timeout: 20_000 })

  // hover reveals the cause card with the exclude action
  await chip.hover()
  const exclude = page.getByRole('button', { name: /استبعاد من التوقع/ })
  await expect(exclude).toBeVisible()
  await exclude.click()

  // the excluded quarter appears as a removable chip in the panel...
  await expect(page.getByRole('button', { name: /2026Q2/ })).toBeVisible({ timeout: 15_000 })
  // ...and the incident quarter leaves the z-score window: agent goes clean
  await expect(page.getByText('لا توجد إشارات غير اعتيادية').first()).toBeVisible({
    timeout: 20_000,
  })
})

test('scenario cards generate from the current assumptions', async ({ page }) => {
  await page.goto('/company/4190')
  await waitForModel(page)
  await page.getByRole('button', { name: 'توليد السيناريوهات' }).click()
  await expect(page.getByText('السيناريو المتفائل')).toBeVisible({ timeout: 60_000 })
  await expect(page.getByText('السيناريو المتشائم')).toBeVisible()
})
