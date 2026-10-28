/* Build: node prototype/build.js  → prototype/index.html + screens/0N-*.html (single-file, no external JS). */
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..'), rd = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const css = rd('design-system/tokens.css') + '\n' + rd('design-system/components.css');
const js = ['logic', 'mockapi', 'components', 'app', 'roles'].map((n) => '/* ' + n + '.js */\n' + rd('prototype/src/' + n + '.js')).join('\n');
const fav = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cg stroke='%23111' stroke-width='9' fill='none' stroke-linecap='round'%3E%3Cpath d='M16 15 28 34Q31 38 32 40M48 15 36 34Q33 38 32 40M32 40v17'/%3E%3C/g%3E%3Ccircle cx='16' cy='15' r='9'/%3E%3Ccircle cx='48' cy='15' r='9' fill='%23E8501A'/%3E%3C/svg%3E";
const page = (title, boot) => `<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>${title}</title><link rel="icon" href="${fav}">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@700&display=swap" rel="stylesheet">
<script>try{document.documentElement.dataset.theme=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'}catch(e){}${boot}</script>
<style>
${css}
</style></head><body>
<div id="app"></div><dialog class="sheet" id="dlg" aria-modal="true"></dialog><div class="toast" id="ts" role="status" aria-live="polite"></div>
<script>
${js}
</script></body></html>
`;
fs.writeFileSync(path.join(root, 'prototype/index.html'), page('YONDO — prototip (DEMO)', ''));
const screens = [['01-home', 'home', 'Bosh sahifa'], ['02-search', 'search', 'Qidiruv'], ['03-companion-profile', 'profile', 'Hamroh profili'], ['04-booking', 'booking', 'Bron'], ['05-chat-active-booking', 'chat', 'Chat / faol bron'], ['06-flowers-gifts', 'gifts', 'Gul va sovgʻalar']];
screens.forEach(([f, n, t]) => fs.writeFileSync(path.join(root, 'screens', f + '.html'), page('YONDO — ' + t + ' (DEMO ekran)', `location.hash='#/screen/${n}';`)));
console.log('built', 1 + screens.length, 'files; index.html', Math.round(fs.statSync(path.join(root, 'prototype/index.html')).size / 1024) + ' KB');
// ---- component gallery (design-system/gallery.html) ----
const C = require('./src/components.js'), tok = JSON.parse(rd('design-system/tokens.json'));
const sec = (t, d, body) => `<section class="gsec"><h2>${t}</h2><p class="mu sm">${d}</p><div class="gbox">${body}</div></section>`;
const swatch = (th) => Object.entries(tok.color[th]).map(([k, v]) => `<span class="sw"><i style="background:${v}"></i><span class="cap">${k}<br>${v}</span></span>`).join('');
const g = [
  sec('Button', 'Variants: primary, <code>sec</code>, <code>danger</code>. States: default, disabled, loading (aria-busy). Min height 48 px.', `<div class="col">${C.Button('Birlamchi')} ${C.Button('Ikkilamchi', { variant: 'sec' })} ${C.Button('Xavfli amal', { variant: 'danger' })} ${C.Button('Nofaol', { disabled: true })} ${C.Button('Yuklanmoqda', { loading: true })}</div>`),
  sec('Chip', 'Toggle filter. Uses <code>aria-pressed</code>. Min height 44 px.', `<div class="chips w">${C.Chip('Tanlanmagan')}${C.Chip('Tanlangan', { on: true })}${C.Chip('Band', { disabled: true })}</div>`),
  sec('Verified / unverified', 'Badge appears ONLY when the backend <code>verified</code> boolean is true. Lists show nothing for unverified; detail views may show the neutral explicit label.', `<div class="col"><div class="row">${C.Verified(true)} <span class="sm mu">verified: true</span></div><div class="row">${C.Verified(false, { explicit: true })} <span class="sm mu">verified: false (detail view)</span></div><div class="row"><span class="sm mu">verified: false (list) → nothing rendered</span></div></div>`),
  sec('Avatar, tag, DEMO marker', 'Initial avatars (no fake photos). DEMO marks all sample data.', `<div class="row wrap">${C.Avatar('Madina', 160)} ${C.Avatar('Jasur', 30, 'lg')} ${C.Tag('kitoblar')} ${C.Tag('kofe')} ${C.Demo()}</div>`),
  sec('Field', 'Label, hint, error. Error sets <code>aria-invalid</code> and <code>aria-describedby</code>.', `<div class="col">${C.Field('g1', 'Ism', { value: 'Madina', required: true })}${C.Field('g2', 'Telefon', { hint: 'Masalan, 90 123 45 67' })}${C.Field('g3', 'Ism', { err: 'Ismni kiriting.', required: true })}${C.Field('g4', 'Tavsif', { area: true, value: 'Matn' })}${C.Field('g5', 'Til', { options: [['uz', 'Oʻzbek'], ['ru', 'Rus']] })}</div>`),
  sec('Alert', 'Errors and unavailability use <code>role="alert"</code>; info/success use <code>role="status"</code>. 503 uses the distinct <code>unavailable</code> kind, never styled as a declined payment.', `<div class="col">${C.Alert('info', 'Maʼlumot xabari.', { title: 'Eslatma' })}${C.Alert('success', 'Amal bajarildi.', { title: 'Tayyor' })}${C.Alert('error', 'Toʻlov rad etildi. Bron saqlangan.', { title: 'Toʻlov amalga oshmadi' })}${C.Alert('unavailable', 'Toʻlov tizimi vaqtincha mavjud emas.', { title: 'Xizmat mavjud emas', rid: 'req-123', actions: C.Button('Qayta urinish', { variant: 'sec' }) })}</div>`),
  sec('Card', 'Static card or whole-card button (<code>a</code> option).', `<div class="col">${C.Card('<span class="grow col" style="gap:2px"><b>Statik karta</b><span class="sm mu">Matn</span></span>')}${C.Card('<span class="grow"><b>Bosiladigan karta</b></span><span aria-hidden="true">›</span>', { a: 'x' })}</div>`),
  sec('Status and timeline', 'Booking statuses from the backend enum; timeline shows the happy path.', `<div class="col"><div class="row wrap">${['pending', 'accepted', 'confirmed', 'active', 'completed', 'cancelled'].map((k) => C.Status(({ pending: 'Kutilmoqda', accepted: 'Qabul qilindi', confirmed: 'Tasdiqlandi', active: 'Uchrashuv faol', completed: 'Yakunlandi', cancelled: 'Bekor qilindi' })[k], k)).join('')}</div>${C.Timeline(['Soʻrov', 'Qabul', 'Tasdiq', 'Faol', 'Yakun'], 2)}</div>`),
  sec('Empty, skeleton, spinner, check, logo', 'Loading and result states. Motion respects <code>prefers-reduced-motion</code>.', `<div class="col">${C.Empty('Hali bronlar yoʻq', 'Hamroh tanlab, birinchi bronni yarating.', C.Button('Hamroh topish'))}${C.Skeleton(2, 56)}<div class="row">${C.Spinner()} ${C.Check()} ${C.Logo(64, true)}</div></div>`),
  sec('Navigation bar', 'Bottom nav, 4–5 items, ≥56 px tall, <code>aria-current="page"</code>.', `<div class="navdemo">${C.NavBar([{ id: 'a', href: '#', icon: '⌂', label: 'Bosh sahifa' }, { id: 'b', href: '#', icon: '⌕', label: 'Qidiruv' }, { id: 'c', href: '#', icon: '☰', label: 'Bronlar' }, { id: 'd', href: '#', icon: '✿', label: 'Sovgʻalar' }], 'a')}</div>`),
  sec('Dialog / sheet', 'Native <code>&lt;dialog&gt;</code> with <code>showModal()</code>: focus moves inside, Tab wraps, Escape closes, focus returns to the opener. Bottom sheet on mobile, centered on ≥768 px.', `<button class="btn sec" id="gdlg" type="button">Dialogni ochish</button>`),
  sec('Colour tokens', 'Light and dark. Measured contrast pairs are in <code>tokens.json</code> → <code>contrast</code>.', `<div class="col"><b>Light</b><div class="sws">${swatch('light')}</div><b>Dark</b><div class="sws">${swatch('dark')}</div></div>`)
].join('');
const galleryCss = `.gsec{padding:16px 20px;border-bottom:1px solid var(--bd)}.gbox{margin-top:12px}.navdemo .nav{position:static}.sws{display:flex;flex-wrap:wrap;gap:8px}.sw{display:flex;gap:8px;align-items:center;width:150px}.sw i{width:28px;height:28px;border-radius:6px;border:1px solid var(--bs);flex:none}`;
const gal = `<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>YONDO — komponentlar galereyasi</title>
<script>try{document.documentElement.dataset.theme=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'}catch(e){}</script>
<style>
${css}
${galleryCss}
</style></head><body>
<div id="app"><main id="v"><div class="pad"><h1>Komponentlar galereyasi</h1><p class="mu sm">Manba: <code>design-system/components.css</code> va <code>prototype/src/components.js</code>.</p><button class="btn sec" id="gth" type="button">Mavzuni almashtirish</button></div>${g}</main></div>
<dialog class="sheet" id="dlg" aria-labelledby="dt"><div class="gh"></div><h2 id="dt">Namuna dialog</h2><p class="mu" style="margin:8px 0 16px">Fokus dialog ichida, Esc yopadi.</p><div class="col"><button class="btn" type="button" id="gc1">Tasdiqlash</button><button class="btn sec" type="button" id="gc2">Bekor qilish</button></div></dialog>
<script>
const d=document.getElementById('dlg');document.getElementById('gdlg').onclick=()=>{d.showModal();requestAnimationFrame(()=>d.classList.add('in'))};
const cl=()=>{d.classList.remove('in');setTimeout(()=>d.open&&d.close(),200)};document.getElementById('gc1').onclick=cl;document.getElementById('gc2').onclick=cl;d.addEventListener('click',e=>{if(e.target===d)cl()});d.addEventListener('close',()=>d.classList.remove('in'));
document.getElementById('gth').onclick=()=>{const r=document.documentElement;r.dataset.theme=r.dataset.theme==='dark'?'light':'dark'};
</script></body></html>
`;
fs.writeFileSync(path.join(root, 'design-system/gallery.html'), gal);
console.log('gallery.html', Math.round(gal.length / 1024) + ' KB');
