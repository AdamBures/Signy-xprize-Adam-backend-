(async () => {
  const puppeteer = (await import('puppeteer')).default;
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  await page.goto('http://localhost:8080/#/library', {waitUntil: 'networkidle0'});
  console.log('Clicking Section 1');
  await page.click('[data-lessons-filter="section-1"]');
  console.log('Clicked Section 1');
  await new Promise(r => setTimeout(r, 500));
  const sec2 = await page.$('[data-lessons-filter="section-2"]');
  if (sec2) {
    console.log('Clicking Section 2');
    await sec2.click();
  } else {
    console.log('No section 2 button');
  }
  console.log('Done');
  await browser.close();
})();
