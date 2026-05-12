import { chromium, type Browser, type Page } from 'playwright';
import { PageAgent } from '@/common/agent';
import { WebPage } from '@/playwright/page';

export interface PlaywrightSessionOptions {
  url: string;
  headed?: boolean;
  viewport?: {
    width: number;
    height: number;
  };
  testId?: string;
}

export interface PlaywrightSessionRuntime {
  browser: Browser;
  page: Page;
  webPage: WebPage;
  agent: PageAgent;
  destroy: () => Promise<void>;
}

export async function createPlaywrightSession(
  options: PlaywrightSessionOptions,
): Promise<PlaywrightSessionRuntime> {
  const browser = await chromium.launch({
    headless: !options.headed,
  });

  const page = await browser.newPage({
    viewport: options.viewport,
  });

  await page.goto(options.url);
  await Promise.race([
    page.waitForLoadState('networkidle'),
    new Promise((resolve) => setTimeout(resolve, 20_000)),
  ]);

  const webPage = new WebPage(page);
  const agent = new PageAgent(webPage, {
    testId: options.testId,
    autoPrintReportMsg: false,
  });

  return {
    browser,
    page,
    webPage,
    agent,
    destroy: async () => {
      await agent.destroy();
      await browser.close();
    },
  };
}
