import base64, io, re
from PIL import Image
AD='/path/to/ad'  # change to your folder
def uri(name, w, d='shots-yondo'):
    im=Image.open(f'{AD}/{d}/{name}.png').convert('RGB'); h=int(im.size[1]*w/im.size[0]); im=im.resize((w,h),Image.LANCZOS)
    b=io.BytesIO(); im.save(b,'JPEG',quality=82,optimize=True,progressive=True); return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
wm=open(f'{AD}/wordmark.svgfrag').read()
LOGO=lambda col: f'<svg viewBox="0 0 219 64" role="img" aria-label="Yondo" style="color:{col}"><g stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-width="5"><path d="M14 12 28 33Q31 37 32 40M50 12 36 33Q33 37 32 40M32 40v12"/></g><circle cx="14" cy="12" r="7" fill="currentColor"/><circle cx="50" cy="12" r="7" fill="#E8501A"/><circle cx="32" cy="55" r="5.5" fill="currentColor"/>{wm}</svg>'
groups=[
 ('Mijoz', 'Hamroh topish, profilni ko‘rish va bron so‘rovi', [('discovery','Kashfiyot'),('discovery-scrolled','Filtrlar'),('profile-services','Hamroh profili'),('profile','Xizmatlar va narxlar'),('booking-dialog','Bron so‘rovi'),('bookings','Bronlarim'),('login-code','SMS-kod bilan kirish')]),
 ('Hamroh', 'Ariza, profil va xizmatlarni yuritish', [('studio','Hamroh studiyasi'),('account','Hisobim'),('settings','Sozlamalar · mavzular')]),
 ('Admin', 'Moderatsiya, foydalanuvchilar va audit', [('admin-dashboard','Boshqaruv paneli'),('admin-queue','Arizalar navbati'),('admin-detail','Ariza tafsiloti'),('admin-confirm','Qarorni tasdiqlash'),('admin-users','Foydalanuvchilar'),('admin-safety','Xavfsizlik signallari'),('admin-audit','Audit jurnali')]),
]
themes=[('yondo','Yondo'),('gul','Gul'),('rausch','Jurnal'),('stone','Stone')]
def pair(n,w,alt): return f'<img class="day" loading="lazy" src="{uri(n,w)}" alt="{alt}"><img class="night" loading="lazy" src="{uri(n,w,"shots-yondo-tun")}" alt="{alt} (tungi)">'
def phone(n,cap): return f'<figure class="ph"><div class="frame">{pair("m-"+n,520,cap+" — mobil ekran")}</div><figcaption>{cap}</figcaption></figure>'
def desk(n,cap): return f'<figure class="dk"><div class="win"><div class="bar"><i></i><i></i><i></i><span>yondo</span></div>{pair("d-"+n,1400,cap+" — kompyuter ekrani")}</div><figcaption>{cap}</figcaption></figure>'
secs=''
for g,sub,items in groups:
    secs+=f'<section class="grp"><div class="gh"><h2>{g}</h2><p>{sub}</p></div><div class="mob rail">{"".join(phone(n,c) for n,c in items)}</div><div class="desk">{"".join(desk(n,c) for n,c in items)}</div></section>'
th=''.join(f'<figure class="ph"><div class="frame"><img src="{uri("m-discovery",520,d)}" alt="{l}"></div><figcaption>{l}</figcaption></figure>' for d,l in [('shots-yondo','Yondo kunduzgi'),('shots-yondo-tun','Yondo tungi')])
html=f'''<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Yondo — doim yoningda</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Space+Grotesk:wght@700&display=swap">
<style>
:root{{--ink:#111111;--paper:#F5F2EC;--acc:#E8501A;--bg:#F5F2EC;--fg:#111111;--muted:rgba(17,17,17,.68);--line:rgba(17,17,17,.12);--gl:rgba(255,255,255,.62);--gle:rgba(255,255,255,.7)}}
body.tun{{--bg:#111111;--fg:#F5F2EC;--muted:rgba(245,242,236,.68);--line:rgba(245,242,236,.14);--gl:rgba(245,242,236,.07);--gle:rgba(245,242,236,.14)}}
.night{{display:none!important}} body.tun .night{{display:block!important}} body.tun .day{{display:none!important}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);transition:background .3s,color .3s;font:16px/1.55 Manrope,"Segoe UI",system-ui,sans-serif;overflow-x:hidden}}
.aur{{position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden}}
.aur i{{position:absolute;width:60vmax;height:60vmax;border-radius:50%;filter:blur(70px);opacity:.42;animation:dr 24s ease-in-out infinite alternate}}
.aur i:nth-child(1){{left:-20vmax;top:-22vmax;background:#E8501A;opacity:.16}}.aur i:nth-child(2){{right:-24vmax;top:20vmax;background:#FFFFFF;opacity:.5;animation-duration:30s}}.aur i:nth-child(3){{left:20vmax;bottom:-30vmax;background:#E8501A;opacity:.1;animation-duration:36s}}body.tun .aur i:nth-child(2){{opacity:.03}}body.tun .aur i:nth-child(1){{opacity:.09}}body.tun .aur i:nth-child(3){{opacity:.06}}
@keyframes dr{{to{{transform:translate(6vmax,4vmax) scale(1.08)}}}}
.wrap{{max-width:1240px;margin:0 auto;padding:0 max(16px,env(safe-area-inset-left))}}
header.top{{position:sticky;top:12px;z-index:5;margin:12px auto 0;max-width:1240px;padding:0 16px}}
.glass{{background:var(--gl);backdrop-filter:blur(22px) saturate(1.4);-webkit-backdrop-filter:blur(22px) saturate(1.4);border:1px solid var(--gle);box-shadow:0 18px 40px -22px rgba(17,17,17,.35),inset 0 1px 0 var(--gle)}}
.nav{{display:flex;align-items:center;gap:16px;padding:10px 14px 10px 20px;border-radius:999px}}
.nav svg{{height:26px;width:auto}}
.seg{{display:flex;gap:4px;padding:4px;border-radius:999px;background:var(--line)}}.segs{{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}}
.seg button{{font:600 14px Manrope,sans-serif;border:0;background:transparent;padding:10px 16px;min-height:44px;border-radius:999px;cursor:pointer;color:var(--fg)}}
.seg button[aria-pressed="true"]{{background:var(--fg);color:var(--bg)}}
.seg button:focus-visible{{outline:3px solid var(--acc);outline-offset:2px}}
.hero{{padding:72px 0 40px;display:grid;gap:28px;justify-items:start}}
.hero svg{{width:min(520px,80vw);height:auto}}
.hero h1{{margin:0;font:700 clamp(40px,7vw,86px)/1 "Space Grotesk",Manrope,sans-serif;letter-spacing:-.035em}}
.hero p{{margin:0;max-width:60ch;color:var(--muted);font-size:18px}}
.pills{{display:flex;flex-wrap:wrap;gap:10px}}
.pill{{padding:10px 16px;border-radius:999px;font-weight:700;display:flex;gap:8px;align-items:center}}
.pill::before{{content:"";width:9px;height:9px;border-radius:50%;background:var(--acc)}}
.grp{{padding:44px 0 12px}}
.gh{{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:18px}}
.gh h2{{margin:0;font:700 34px/1.1 "Space Grotesk",Manrope,sans-serif;letter-spacing:-.02em}}
.gh p{{margin:0;color:var(--muted)}}
.rail{{display:flex;gap:22px;overflow-x:auto;padding:10px 4px 26px;scroll-snap-type:x mandatory}}
.ph{{margin:0;flex:0 0 auto;width:240px;scroll-snap-align:start;display:grid;gap:12px;justify-items:center}}
.frame{{width:240px;aspect-ratio:975/2110;border-radius:36px;background:#0d0d0d;padding:8px;box-shadow:0 30px 60px -28px rgba(17,17,17,.45),0 0 0 1px rgba(255,255,255,.08) inset;transition:transform .35s cubic-bezier(.2,0,0,1)}}
.frame img{{width:100%;height:100%;display:block;border-radius:29px;object-fit:cover;object-position:top}}
.ph:hover .frame{{transform:translateY(-6px) rotate(-.6deg)}}
figcaption{{font-weight:600;font-size:14px;color:var(--muted)}}
.desk{{display:none;grid-template-columns:repeat(auto-fill,minmax(min(100%,520px),1fr));gap:28px}}
.dk{{margin:0;display:grid;gap:10px;min-width:0}}
.win{{border-radius:16px;overflow:hidden;box-shadow:0 30px 60px -30px rgba(17,17,17,.4),0 0 0 1px var(--line);background:var(--bg)}}
.bar{{height:32px;display:flex;align-items:center;gap:7px;padding:0 12px;background:var(--line)}}
.bar i{{width:10px;height:10px;border-radius:50%;background:var(--line)}}.bar span{{margin-left:10px;font-size:12px;color:var(--muted)}}
.win img{{display:block;width:100%;height:auto}}
body.desktop .mob{{display:none}} body.desktop .desk{{display:grid}}
.themes{{padding:44px 0 72px}}
footer{{padding:28px 0 48px;color:var(--muted);font-size:14px;border-top:1px solid var(--line)}}
@media (prefers-reduced-motion:reduce){{.aur i{{animation:none}}.frame{{transition:none}}}}
</style></head><body>
<div class="aur" aria-hidden="true"><i></i><i></i><i></i></div>
<header class="top"><nav class="nav glass" aria-label="Ko‘rinish">{LOGO('currentColor')}<div class="segs"><div class="seg" role="group" aria-label="Ko‘rinish"><button type="button" id="t-k" aria-pressed="true">Kunduzgi</button><button type="button" id="t-t" aria-pressed="false">Tungi</button></div><div class="seg" role="group" aria-label="Qurilma"><button type="button" id="b-m" aria-pressed="true">Mobil</button><button type="button" id="b-d" aria-pressed="false">Kompyuter</button></div></div></nav></header>
<main class="wrap">
<section class="hero">{LOGO('currentColor')}<h1>Doim yoningda.</h1>
<p>Suhbat va sayr uchun hamroh topish platformasi. Quyida ilovaning yangi “Yondo” mavzusidagi ekranlari: mijoz, hamroh va administrator uchun.</p>
<div class="pills"><span class="pill glass">Ochiq narxlar</span><span class="pill glass">Jamoat joylarida uchrashuv</span><span class="pill glass">Arizalar moderatsiyasi</span></div></section>
{secs}
<section class="themes"><div class="gh"><h2>Kunduzgi va tungi</h2><p>Faqat logotip ranglari: oq, qora va sabzi rang</p></div><div class="rail">{th}</div></section>
<footer>Ekranlar ilovaning haqiqiy build’idan olingan; ismlar va ma’lumotlar namunaviy.</footer>
</main>
<script>
const bm=document.getElementById('b-m'),bd=document.getElementById('b-d');
function set(d){{document.body.classList.toggle('desktop',d);bm.setAttribute('aria-pressed',!d);bd.setAttribute('aria-pressed',d);}}
bm.onclick=()=>set(false);bd.onclick=()=>set(true);
const tk=document.getElementById('t-k'),tt=document.getElementById('t-t');function th(n){{document.body.classList.toggle('tun',n);tk.setAttribute('aria-pressed',!n);tt.setAttribute('aria-pressed',n);}}tk.onclick=()=>th(false);tt.onclick=()=>th(true);
</script></body></html>'''
open('/mnt/user-data/outputs/yondo-ekranlar.html','w').write(html)
import os; print(os.path.getsize('/mnt/user-data/outputs/yondo-ekranlar.html')//1024,'KB')
