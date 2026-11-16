// Usage: node render.js [preview t1,t2,...]  |  node render.js  (full render → out/heritage_frames.mp4 + out/events.json)
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs'), { spawn } = require('child_process');
const FPS = 30;
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'index.html'));
  await page.evaluate(() => document.fonts.ready);
  const outDir = path.join(__dirname, 'out'); fs.mkdirSync(outDir, { recursive: true });
  if (process.argv[2] === 'preview') {
    const dir = process.argv[4] || outDir;
    for (const t of process.argv[3].split(',').map(Number)) {
      await page.evaluate(t => window.render(t), t);
      await page.screenshot({ path: path.join(dir, `p_${t}.jpg`), type: 'jpeg', quality: 80 });
    }
    await browser.close(); return;
  }
  const dur = await page.evaluate(() => window.DURATION);
  fs.writeFileSync(path.join(outDir, 'events.json'), JSON.stringify(await page.evaluate(() => window.EVENTS)));
  const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', path.join(outDir, 'video_noaudio.mp4')], { stdio: ['pipe', 'ignore', 'inherit'] });
  const n = Math.round(dur * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 90 === 0) console.log(`frame ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
})();
