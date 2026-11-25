import { expect, test, type Browser, type BrowserContextOptions, type Page } from '@playwright/test'

const number = 'inv-1'
const viewport = { width: 1280, height: 960 }

async function enterDemo(page: Page, owner: string) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Try the demo', exact: true }).first().click()
  await page.getByRole('textbox', { name: 'Your name' }).fill(owner)
  await page.getByRole('button', { name: 'Start the demo' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

async function submitInvoice(page: Page, client: string, expectedStatus: number) {
  await page.getByRole('button', { name: 'Chase an invoice', exact: true }).first().click()
  await page.getByLabel('Invoice ID').fill(number)
  await page.getByLabel('Client Name').fill(client)
  await page.getByLabel('Client Email').fill('billing@example.test')
  await page.getByLabel('Invoice total ($)').fill('1200')
  await page.getByLabel('Days Overdue').fill('10')
  await page.getByLabel('Client location (for legal notices)').fill('California')

  const [response] = await Promise.all([
    page.waitForResponse(response => (
      new URL(response.url()).pathname === '/api/invoices' && response.request().method() === 'POST'
    )),
    page.getByRole('button', { name: 'Start chasing' }).click(),
  ])
  expect(response.status()).toBe(expectedStatus)
}

async function verifyInvoice(page: Page, client: string, otherClient: string) {
  await page.goto('/dashboard')
  await expect(page.getByText(client, { exact: true })).toBeVisible()
  await expect(page.getByText(otherClient, { exact: true })).toHaveCount(0)
  // A reload can render from the app's persistent cache. Check the owner-scoped API as well.
  const response = await page.request.get('/api/invoices')
  expect(response.ok()).toBe(true)
  expect(await response.json()).toEqual([expect.objectContaining({ invoice_id: number, client_name: client })])
}

async function film<T>(
  browser: Browser,
  baseURL: string | undefined,
  clip: string,
  action: (page: Page) => Promise<T>,
  storageState?: BrowserContextOptions['storageState'],
) {
  const info = test.info()
  const recording = process.env.RECORD_FEATURE_EVIDENCE === '1'
  const context = await browser.newContext({
    baseURL,
    viewport,
    storageState,
    recordVideo: recording ? { dir: info.outputPath('raw-video'), size: viewport } : undefined,
  })
  const page = await context.newPage()
  const video = page.video()

  try {
    const result = await action(page)
    // Leave the asserted result on-screen long enough to read in the recording.
    if (recording) await new Promise(resolve => setTimeout(resolve, 900))
    return result
  } catch (error) {
    await info.attach(clip, { body: await page.screenshot(), contentType: 'image/png' }).catch(() => undefined)
    throw error
  } finally {
    await context.close()
    if (video) await video.saveAs(info.outputPath('clips', clip + '.webm'))
  }
}

test('invoice numbers are unique per owner', async ({ browser, baseURL }) => {
  const alice = await film(browser, baseURL, '01-alice-creates', async page => {
    await enterDemo(page, 'Alice')
    await submitInvoice(page, 'Willow Studio', 200)
    await expect(page).toHaveURL(/\/invoice\//)
    await verifyInvoice(page, 'Willow Studio', 'Cedar Studio')
    return page.context().storageState()
  })

  const ben = await film(browser, baseURL, '02-ben-creates', async page => {
    await enterDemo(page, 'Ben')
    await submitInvoice(page, 'Cedar Studio', 200)
    await expect(page).toHaveURL(/\/invoice\//)
    await verifyInvoice(page, 'Cedar Studio', 'Willow Studio')
    return page.context().storageState()
  })

  await film(browser, baseURL, '03-alice-retries', async page => {
    await verifyInvoice(page, 'Willow Studio', 'Cedar Studio')
    await submitInvoice(page, 'Replacement Studio', 409)
    await expect(page.getByRole('alert')).toHaveText("Invoice 'inv-1' already exists")
    if (process.env.RECORD_FEATURE_EVIDENCE === '1') await new Promise(resolve => setTimeout(resolve, 900))
    await page.getByRole('button', { name: 'Close', exact: true }).click()
    await verifyInvoice(page, 'Willow Studio', 'Replacement Studio')
  }, alice)

  await film(browser, baseURL, '04-ben-verifies', page => verifyInvoice(page, 'Cedar Studio', 'Willow Studio'), ben)
})
