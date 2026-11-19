// Renders each .story of story_citation.html to a 1080x1920 PNG (Instagram story).
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.join(__dirname, 'story_citation.html')); await p.evaluate(() => document.fonts.ready);
  const s = await p.$$('.story');
  for (let i = 0; i < s.length; i++) await s[i].screenshot({ path: path.join(__dirname, `story_citation_${i + 1}.png`) });
  await b.close(); console.log(s.length, 'stories');
})();
