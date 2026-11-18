// Usage: node render2.js <video.html> <outDir> [preview t1,t2,... previewDir]
// Injects <outDir>/timing.json (from voice) if present, renders 30 fps -> <outDir>/video_noaudio.mp4 + events.json
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs'), { spawn } = require('child_process');
const FPS = 30;
(async () => {
  const [html, outDir, mode, times, pdir] = process.argv.slice(2);
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  const tf = path.join(outDir, 'timing.json');
  if (fs.existsSync(tf)) await page.addInitScript(t => { window.TIMING = t; }, JSON.parse(fs.readFileSync(tf, 'utf8')));
  if (process.env.PREVIEW) await page.addInitScript(() => { window.PREVIEW = true; });
  await page.goto('file://' + path.resolve(html));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => window.DURATION > 0);
  const dur = await page.evaluate(() => window.DURATION);
  if (mode === 'preview') {
    for (const t of times.split(',')) {
      const tt = await page.evaluate(c => isNaN(+c) ? window.H.cue(c) : +c, t);
      await page.evaluate(t => window.render(t), tt);
      await page.screenshot({ path: path.join(pdir, `p_${t.replace(/[^\w.+-]/g, '_')}.jpg`), type: 'jpeg', quality: 80 });
    }
    console.log('duration', dur); await browser.close(); return;
  }
  fs.writeFileSync(path.join(outDir, 'events.json'), JSON.stringify(await page.evaluate(() => window.EVENTS)));
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', path.join(outDir, 'video_noaudio.mp4')], { stdio: ['pipe', 'ignore', 'inherit'] });
  const n = Math.round(dur * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await browser.close();
  console.log('rendered', n, 'frames');
})();
