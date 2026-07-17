import { devices, expect, test } from '@playwright/test'

// InstallPrompt banner: mobile visitors get the PWA install guide, desktop
// never does, and dismissal persists.
// Only UA/viewport/touch are borrowed from the device presets — spreading the
// whole preset would drag in defaultBrowserType, which test.use() rejects.

function mobile(preset: (typeof devices)[string]) {
  const { userAgent, viewport, isMobile, hasTouch } = preset
  return { userAgent, viewport, isMobile, hasTouch }
}

test.describe('iphone', () => {
  test.use(mobile(devices['iPhone 13']))
  test('iOS visitor sees the Add-to-Home-Screen guide', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('ثبّت دلتا كتطبيق على جوالك')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('إضافة إلى الصفحة الرئيسية')).toBeVisible()
    // dismiss persists
    await page.getByRole('button', { name: 'إغلاق' }).click()
    await page.reload()
    await page.waitForTimeout(3500)
    await expect(page.getByText('ثبّت دلتا كتطبيق على جوالك')).toHaveCount(0)
  })
})

test.describe('android', () => {
  test.use(mobile(devices['Pixel 7']))
  test('Android visitor sees the install banner', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('ثبّت دلتا كتطبيق على جوالك')).toBeVisible({ timeout: 10_000 })
  })
})

test('desktop visitor never sees the banner', async ({ page }) => {
  await page.goto('/')
  await page.waitForTimeout(3500)
  await expect(page.getByText('ثبّت دلتا كتطبيق على جوالك')).toHaveCount(0)
})
