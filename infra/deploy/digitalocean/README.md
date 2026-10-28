# Yondo bitta serverda (DigitalOcean) — Docker Compose

**Holat: yozilgan, lekin Docker bilan hali qurilmagan va serverda sinalmagan** (Docker Desktop kompyuteringizda o‘chiq). API ishga tushishi (migratsiyalar, production sozlamalari) PostgreSQL 16 bilan mahalliy tekshirilgan; Dockerfile va compose fayllarini birinchi marta serverda ishga tushirasiz, xato chiqsa menga yozing.

Bu **demo emas**, haqiqiy API (`apps/api`) + veb-ilova (`apps/web`) + PostgreSQL + Redis. Demo (`infra/deploy/README.md`) Render’da alohida qoladi.

## Nima bor va nima YO‘Q (halol ro‘yxat)
| Bor | Hali yo‘q (beta uchun blokerlar) |
|---|---|
| API + migratsiyalar, veb-ilova, PostgreSQL, Redis (chat), soatlik vazifalar (`jobs`), avtomatik HTTPS (Caddy), kunlik zaxira skripti | **Rasm saqlash** (S3/MinIO adapteri yozilmagan: rasm yuklash xato beradi) · **shaxs tasdig‘i** (ulanmagan) · **SMS** (kod faqat Telegram orqali, token kerak) · to‘lov (TezCheck + domen + komissiya qarori) |
| Ekranda kod **yo‘q** (production’da ko‘rsatilmaydi) | Birinchi admin: tayyor buyruq yo‘q (pastda SQL) |

## Domen kerakmi?
Domen **keyin** qo‘shiladi, ish ko‘paymaydi: `.env` dagi `DOMAIN=:80` ni `DOMAIN=yondo.example` ga almashtirasiz, domenning DNS A yozuvini server IP’siga qaratasiz, `docker compose up -d` — HTTPS o‘zi paydo bo‘ladi.
`:80` (HTTP, IP bo‘yicha) faqat **sizning shaxsiy sinovingiz va SOXTA ma’lumotlar** uchun: HTTP’da kod va token ochiq yuradi, SOS joylashuvi (brauzer HTTPS talab qiladi) ishlamaydi, TezCheck webhook’i HTTPS + domen talab qiladi. Haqiqiy odamlar uchun faqat domen + HTTPS.

## 1. Serverni yarating (DigitalOcean, siz)
1. Create → Droplets → region **Frankfurt**, image **Ubuntu 24.04 LTS**, Basic, **kamida 2 GB RAM**.
2. Authentication: **SSH key**. Windows PowerShell’da `ssh-keygen`, keyin `type $env:USERPROFILE\.ssh\id_ed25519.pub` — chiqqan matnni DigitalOcean’ga qo‘ying.
3. Networking → Firewalls: faqat **22, 80, 443** kiruvchi portlar.

## 2. Serverga o‘rnating
```bash
ssh root@SERVER_IP
curl -fsSL https://get.docker.com | sh
git clone -b design/prototype https://github.com/abdulloh042006-debug/Yondo.git
cd Yondo/infra/deploy/digitalocean
cp .env.example .env
openssl rand -hex 24   # ikki marta: POSTGRES_PASSWORD va YONDO_AUTH_OTP_PEPPER uchun
nano .env              # to‘ldiring (Ctrl+O, Enter, Ctrl+X)
docker compose up -d --build
docker compose ps
curl http://localhost/health
```
Birinchi qurish 5–10 daqiqa (taxminiy). `.env` — sirlar: uni hech kimga yubormang va git’ga qo‘shmang. Telegram tokenini (`YONDO_TELEGRAM_GATEWAY_TOKEN`) shu faylga o‘zingiz yozasiz.

## 3. Birinchi admin
Avval veb-ilovada o‘z raqamingiz bilan bir marta kiring (akkaunt yaratiladi), keyin serverda:
```bash
docker compose exec postgres psql -U yondo -d yondo -c "INSERT INTO user_roles (user_id, role) SELECT id, 'admin' FROM users WHERE phone_number = '+998XXXXXXXXX' ON CONFLICT DO NOTHING;"
```
Admin sahifalari xato bersa, menga yozing (hisob holati yoki yosh maydoni kerak bo‘lishi mumkin).

## 4. Yangilash, zaxira, holat
- Yangilash: `cd Yondo && git pull && cd infra/deploy/digitalocean && docker compose up -d --build`
- Loglar: `docker compose logs --tail 100 api` (kod va token log’ga yozilmaydi)
- Zaxira (har kecha 03:00): `crontab -e` va qator qo‘shing: `0 3 * * * /root/Yondo/infra/deploy/digitalocean/backup.sh >> /var/log/yondo-backup.log 2>&1` (avval `chmod +x backup.sh`). Zaxira shu serverning o‘zida turadi: uni muntazam boshqa joyga ham nusxalang.
- Tiklash: `gunzip -c yondo-YYYY-MM-DD.sql.gz | docker compose exec -T postgres psql -U yondo -d yondo` (bo‘sh bazaga; avval sinab ko‘ring).

## Tekshirilmagan
Docker qurilishi, Caddy sozlamasi, Compose healthcheck va `depends_on` ketma-ketligi, DigitalOcean’dagi aniq narx va qurish vaqti, HTTPS sertifikat olish (domen bo‘lgach), zaxirani tiklash. Birinchi ishga tushirishda shularni birga tekshiramiz.
