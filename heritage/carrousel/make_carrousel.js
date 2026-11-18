// Renders each .slide of heritage_carrousel.html to a 1080x1350 PNG (Instagram 4:5).
// Usage: node make_carrousel.js  -> slides/slide_1.png ... slide_7.png
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const out = path.join(__dirname, 'slides'); fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'heritage_carrousel.html'));
  await page.evaluate(() => document.fonts.ready);
  const slides = await page.$$('.slide');
  for (let i = 0; i < slides.length; i++) await slides[i].screenshot({ path: path.join(out, `slide_${i + 1}.png`) });
  console.log(slides.length, 'slides');
  await browser.close();
})();
