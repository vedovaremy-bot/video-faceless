// Renders guide_affiliation.html to an A4 PDF. Usage: node make_pdf.js
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + path.join(__dirname, 'guide_affiliation.html')); await p.evaluate(() => document.fonts.ready);
  await p.pdf({ path: path.join(__dirname, 'Guide_affiliation.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true });
  await b.close();
})();
