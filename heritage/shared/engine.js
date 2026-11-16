/* Heritage video engine — deterministic render(t) for frame-by-frame capture.
 * Timing: window.SCRIPT = [{id, text, pause}] (voice script, shared with voice.py)
 *         window.TIMING = {phrases: {id: {start, end, words: [t...]}}, duration}  (injected by render.js after TTS)
 * Cues (data-cue, data-from/data-to, data-out, ...):  "p3" phrase start · "p3.2" word #2 · "p3$" phrase end · "END" · "+0.3" offset · "1.5" absolute
 */
(() => {
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const easeOut = x => 1 - Math.pow(1 - x, 3);
const easeInOut = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const backOut = x => { const c1 = 1.7, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const NS = 'http://www.w3.org/2000/svg';

/* ---------- timing ---------- */
function estimateTiming(script) {
  const phrases = {}; let t = 0.15;
  for (const p of script) {
    const words = p.text.split(/\s+/).filter(Boolean), ws = [];
    for (const w of words) { ws.push(t); t += 0.17 + 0.045 * w.length + (/[.,:?!…»]$/.test(w) ? 0.18 : 0); }
    phrases[p.id] = { start: ws[0], end: t, words: ws }; t += p.pause ?? 0.3;
  }
  return { phrases, duration: t + 1.2 };
}
const TIMING = window.TIMING || estimateTiming(window.SCRIPT || []);
window.TIMING = TIMING;
function cue(str) {
  if (str == null || str === '') return NaN;
  str = String(str).trim();
  const m = str.match(/^([A-Za-z]\w*|END)?(?:\.(\d+)|(\$))?([+-]\d*\.?\d+)?$/);
  if (!m || (!m[1] && !m[4])) return parseFloat(str);
  let t = 0;
  if (m[1] === 'END') t = TIMING.duration;
  else if (m[1]) {
    const p = TIMING.phrases[m[1]]; if (!p) throw new Error('unknown cue ' + str);
    t = m[3] ? p.end : m[2] != null ? p.words[Math.min(+m[2], p.words.length - 1)] : p.start;
  }
  return t + (m[4] ? parseFloat(m[4]) : 0);
}

/* ---------- builders ---------- */
const EVENTS = [];
// words of a phrase, each word cued to the moment it is spoken. range = [from, to) word indexes
function say(el, pid, from = 0, to, opts = {}) {
  const text = (window.SCRIPT.find(p => p.id === pid) || {}).text || '';
  const words = text.replace(/[«»]/g, '').split(/\s+/).filter(Boolean);
  const all = text.split(/\s+/).filter(Boolean);
  // map indexes on the raw token list (guillemets are separate tokens in the script)
  const idx = []; all.forEach((w, i) => { if (!/^[«»]$/.test(w)) idx.push(i); });
  const shown = opts.words || words.slice(from, to);
  shown.forEach((w, k) => {
    const s = document.createElement('span'); s.className = 'w'; s.textContent = w;
    s.dataset.cue = `${pid}.${idx[from + k] ?? (from + k)}${opts.offset ? (opts.offset > 0 ? '+' : '') + opts.offset : ''}`;
    if (opts.anim) s.dataset.anim = opts.anim;
    el.appendChild(s);
  });
  return el;
}
function logoSymbol() {
  const svg = document.createElementNS(NS, 'svg'); svg.setAttribute('width', 0); svg.setAttribute('height', 0); svg.style.position = 'absolute';
  svg.innerHTML = `<defs><linearGradient id="gg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff1c4"/><stop offset=".5" stop-color="#d9b45a"/><stop offset="1" stop-color="#8a6a25"/></linearGradient>
  <symbol id="logo" viewBox="0 0 200 220"><g id="logo-g" fill="url(#gg)">
    <path d="M58 64 L64 30 L82 48 L100 20 L118 48 L136 30 L142 64 Z"/><rect x="56" y="66" width="88" height="9" rx="2"/>
    <circle cx="64" cy="27" r="5"/><circle cx="100" cy="16" r="6"/><circle cx="136" cy="27" r="5"/>
    <circle cx="100" cy="142" r="50" fill="none" stroke="url(#gg)" stroke-width="5"/>
    <circle cx="100" cy="142" r="42" fill="none" stroke="url(#gg)" stroke-width="1.5"/>
    <text x="100" y="167" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="72">H</text>
    <path d="M88 205 Q100 198 112 205" stroke="url(#gg)" stroke-width="3" fill="none"/></g></symbol></defs>`;
  document.body.prepend(svg);
  const g = svg.querySelector('#logo-g');
  for (const side of [-1, 1]) for (let i = 0; i < 9; i++) {
    const ang = (200 - i * 17) * Math.PI / 180, R = 66, cx = 100 + side * Math.cos(ang) * -R, cy = 142 - Math.sin(ang) * R;
    const e = document.createElementNS(NS, 'ellipse');
    e.setAttribute('cx', cx); e.setAttribute('cy', cy); e.setAttribute('rx', 4.2); e.setAttribute('ry', 10 - i * 0.35);
    e.setAttribute('transform', `rotate(${side * (-(ang * 180 / Math.PI) + 125)} ${cx} ${cy})`); g.appendChild(e);
  }
}
// karaoke captions: chunks of N words, active word in gold
function captions(container, pids, chunk = 5) {
  for (const pid of pids) {
    const all = window.SCRIPT.find(p => p.id === pid).text.split(/\s+/).filter(Boolean);
    const toks = all.map((w, i) => ({ w, i })).filter(o => !/^[«»]$/.test(o.w));
    for (let c = 0; c < toks.length; c += chunk) {
      const part = toks.slice(c, c + chunk);
      // avoid a lonely last word
      if (toks.length - (c + chunk) === 1) { part.push(toks[c + chunk]); c++; }
      const div = document.createElement('div'); div.className = 'cap';
      const next = toks[c + part.length];
      div.dataset.cap = `${pid}.${part[0].i}`; div.dataset.capEnd = next ? `${pid}.${next.i}` : `${pid}$+0.25`;
      part.forEach(o => { const s = document.createElement('span'); s.className = 'w'; s.textContent = o.w; s.dataset.k = `${pid}.${o.i}`; div.appendChild(s); });
      container.appendChild(div);
    }
  }
}

/* ---------- background ---------- */
let silk, sctx, simg, dctx, DUST;
function initBg() {
  silk = document.getElementById('silk'); sctx = silk.getContext('2d'); simg = sctx.createImageData(silk.width, silk.height);
  dctx = document.getElementById('dust').getContext('2d');
  DUST = Array.from({ length: 70 }, (_, i) => { const r = k => { const x = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453; return x - Math.floor(x); };
    return { x: r(1) * 1080, y: r(2) * 1920, sp: 15 + r(3) * 45, sz: 1.2 + r(4) * 3.2, ph: r(5) * 6.28, a: 0.25 + r(6) * 0.6 }; });
}
let glowRanges = [];
function glowAmount(t) {
  let a = 0; for (const [s, e] of glowRanges) a = Math.max(a, clamp((t - s + 0.25) / 0.5) * clamp((e - t + 0.25) / 0.5));
  return easeInOut(a);
}
function drawBg(t) {
  const W = silk.width, H = silk.height, d = simg.data, b = glowAmount(t); let k = 0;
  for (let y = 0; y < H; y++) { const v = y / W;
    for (let x = 0; x < W; x++) { const u = x / W;
      const ph = (u * 0.75 + v * 0.55) * 4.2 + Math.sin(v * 2.3 + t * 0.35) * 0.9 + Math.sin(u * 3.1 - t * 0.22) * 0.5 + t * 0.18;
      let l = 0.5 + 0.5 * Math.sin(ph); l = l * 0.7 + 0.3 * (0.5 + 0.5 * Math.sin(ph * 2.3 + u * 2.0 - t * 0.3));
      const hi = Math.pow(l, 6), glow = Math.exp(-Math.pow(v - 1.78, 2) / 0.18);
      const wr = 7 + 26 * l + 70 * hi, wg = 7 + 22 * l + 55 * hi, wb = 9 + 18 * l + 30 * hi;
      const br = 14 + 46 * l + 120 * hi + 95 * glow, bg = 9 + 30 * l + 85 * hi + 50 * glow, bb = 6 + 12 * l + 28 * hi + 12 * glow;
      d[k++] = wr + (br - wr) * b; d[k++] = wg + (bg - wg) * b; d[k++] = wb + (bb - wb) * b; d[k++] = 255; } }
  sctx.putImageData(simg, 0, 0);
  dctx.clearRect(0, 0, 1080, 1920);
  for (const p of DUST) {
    const y = ((p.y - t * p.sp) % 1920 + 1920) % 1920, x = p.x + Math.sin(t * 0.6 + p.ph) * 30;
    const a = p.a * (0.55 + 0.45 * Math.sin(t * 2.2 + p.ph));
    const g = dctx.createRadialGradient(x, y, 0, x, y, p.sz * 4);
    g.addColorStop(0, `rgba(255,226,150,${a})`); g.addColorStop(1, 'rgba(255,200,90,0)');
    dctx.fillStyle = g; dctx.beginPath(); dctx.arc(x, y, p.sz * 4, 0, 6.29); dctx.fill();
  }
}

/* ---------- timeline ---------- */
let scenes, anims, punches = [], flashes = [], caps = [], hooks = [];
function init() {
  logoSymbol(); initBg();
  if (window.build) window.build({ say, captions, cue });
  scenes = [...document.querySelectorAll('.scene')].map((el, i, arr) => {
    const a = i === 0 ? 0 : cue(el.dataset.from);
    const e = el.dataset.to ? cue(el.dataset.to) : (arr[i + 1] ? cue(arr[i + 1].dataset.from) : TIMING.duration);
    if (el.hasAttribute('data-glow')) glowRanges.push([a, e]);
    if (i > 0 && !el.hasAttribute('data-cut')) EVENTS.push({ t: a, kind: 'whoosh' });
    return { el, a, e, cut: el.hasAttribute('data-cut') };
  });
  anims = [...document.querySelectorAll('[data-cue]')].map(el => {
    const t0 = cue(el.dataset.cue), anim = el.dataset.anim || 'up';
    const o = { el, t0, anim, d: +(el.dataset.d || (anim === 'slam' ? 0.28 : 0.5)), out: el.dataset.out ? cue(el.dataset.out) : Infinity,
      center: el.hasAttribute('data-center'), text: anim === 'type' ? el.textContent : null };
    if (el.hasAttribute('data-punch') || anim === 'slam') punches.push(t0);
    if (el.hasAttribute('data-flash')) flashes.push(t0);
    const sfx = el.dataset.sfx || (anim === 'slam' ? 'hit' : anim === 'pop' ? 'pop' : anim === 'type' ? 'type' : null);
    if (sfx && sfx !== 'none' && t0 > 0) EVENTS.push({ t: t0, kind: sfx, d: o.d });
    return o;
  });
  document.querySelectorAll('[data-sfx-at]').forEach(el => el.dataset.sfxAt.split(';').forEach(s => { const [c, k] = s.split('|'); EVENTS.push({ t: cue(c), kind: k }); }));
  caps = [...document.querySelectorAll('[data-cap]')].map(el => ({ el, a: cue(el.dataset.cap), e: cue(el.dataset.capEnd),
    words: [...el.querySelectorAll('[data-k]')].map(w => ({ w, t: cue(w.dataset.k) })) }));
  caps.forEach((c, i) => { if (caps[i + 1] && caps[i + 1].a - c.e < 0.6) c.e = caps[i + 1].a; });
  if (caps[0] && caps[0].a < 0.6) caps[0].a = -1; // first caption already on screen at frame 0 (hook)
  window.EVENTS = EVENTS; window.DURATION = TIMING.duration;
}
function render(t) {
  drawBg(t);
  let punch = 0; for (const p of punches) if (t >= p) punch += 0.035 * Math.exp(-(t - p) * 9);
  let fl = 0; for (const f of flashes) if (t >= f) fl = Math.max(fl, 0.55 * Math.exp(-(t - f) * 6));
  document.getElementById('cam').style.transform = `scale(${1 + punch}) rotate(${punch * 8 * Math.sin(t * 40)}deg)`;
  document.getElementById('flash').style.opacity = fl;
  for (const s of scenes) {
    const fin = s.a === 0 || s.cut ? (t >= s.a ? 1 : 0) : clamp((t - s.a + 0.2) / 0.35);
    const nextCut = scenes[scenes.indexOf(s) + 1]?.cut;
    const fout = nextCut ? (t < s.e ? 1 : 0) : clamp((s.e - t + 0.15) / 0.35);
    const o = Math.min(fin, fout);
    s.el.style.opacity = o; s.el.style.visibility = o <= 0 ? 'hidden' : 'visible';
    s.el.style.transform = `scale(${1 + (1 - easeOut(fin)) * 0.05 - (1 - fout) * 0.04})`;
    s.el.style.filter = o < 1 ? `blur(${(1 - o) * 12}px)` : 'none';
  }
  for (const a of anims) {
    const { el, t0, d, anim } = a, p = clamp((t - t0) / d), ep = easeOut(p);
    const po = clamp((t - a.out) / 0.25);
    const base = a.center ? 'translateX(-50%) ' : '';
    let op = anim === 'type' ? (t >= t0 ? 1 : 0) : ep, tr = base, fi = 'none';
    if (anim === 'up') { tr += `translateY(${(1 - ep) * 36}px)`; fi = p < 1 ? `blur(${(1 - ep) * 12}px)` : 'none'; }
    else if (anim === 'pop') tr += `scale(${0.55 + 0.45 * backOut(p)})`;
    else if (anim === 'slam') { op = clamp(p * 3); tr += `scale(${1 + (1 - easeOut(p)) * 0.9})`; fi = p < 1 ? `blur(${(1 - p) * 6}px)` : 'none'; }
    else if (anim === 'left' || anim === 'right') { tr += `translateX(${(1 - ep) * (anim === 'left' ? -140 : 140)}px)`; }
    else if (anim === 'type') { const n = Math.round(a.text.length * clamp((t - t0) / d)); el.textContent = a.text.slice(0, n) + (p < 1 && t >= t0 ? '|' : ''); }
    else if (anim === 'draw') { const L = el.getTotalLength ? el.getTotalLength() : 1000; el.style.strokeDasharray = L; el.style.strokeDashoffset = L * (1 - easeInOut(p)); op = t >= t0 ? 1 : 0; }
    if (el.dataset.tilt) tr += ` rotate(${el.dataset.tilt}deg)`;
    if (po > 0) { op *= 1 - po; tr += ` scale(${1 - po * 0.1})`; }
    el.style.opacity = op; el.style.transform = tr; el.style.filter = fi;
  }
  document.querySelectorAll('[data-strike]').forEach(bar => { bar.style.width = (104 * easeInOut(clamp((t - cue(bar.dataset.strike)) / 0.35))) + '%'; });
  document.querySelectorAll('[data-grow]').forEach(l => {
    const [a, b] = l.dataset.grow.split(',').map(cue), p = easeInOut(clamp((t - a) / (b - a)));
    l.style.transform = l.dataset.axis === 'x' ? `scaleX(${p})` : `scaleY(${p})`;
  });
  document.querySelectorAll('[data-class]').forEach(el => el.dataset.class.split(';').forEach(s => {
    const [c, cls] = s.split('|'); el.classList.toggle(cls, t >= cue(c)); }));
  for (const c of caps) {
    const vis = t >= c.a && t < c.e, p = easeOut(clamp((t - c.a) / 0.18));
    c.el.style.opacity = vis ? p : 0; c.el.style.transform = `translateY(${(1 - p) * 20}px) scale(${0.94 + 0.06 * p})`;
    c.words.forEach((w, i) => { const on = t >= w.t && (i === c.words.length - 1 || t < c.words[i + 1].t);
      w.w.classList.toggle('on', on); w.w.style.transform = on ? 'scale(1.04)' : 'none'; });
  }
  document.querySelectorAll('.gold .w, .gold:not(.line), .goldtxt, .subbtn').forEach(el => el.style.backgroundPosition = `${100 - ((t * 35) % 220)}% 0`);
  if (window.onFrame) window.onFrame(t, { clamp, easeOut, easeInOut, backOut, cue });
}
window.render = render;
window.H = { clamp, easeOut, easeInOut, backOut, cue };
document.addEventListener('DOMContentLoaded', () => {
  init();
  if (!navigator.webdriver) { const s = performance.now(); (function loop() { render(((performance.now() - s) / 1000) % window.DURATION); requestAnimationFrame(loop); })(); }
});
})();
