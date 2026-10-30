# Free and cheap cloud hosting with Docker for the Yondo closed beta (Uzbekistan, ~20-500 users, 24/7) — research notes, 2026-10-28

Method note: pages marked "fetched 2026-10-28" were read live on the research date. Items from blogs/forums are labelled as user reports. "Inference" = my reasoning, not a sourced fact. Anything not verified is in Gaps. Project facts come from the local repo (`D:\Yondo\compose.yaml`, `D:\Yondo\infra\deploy\README.md`, `D:\Yondo\infra\deploy\Dockerfile`, `D:\Yondo\infra\jobs\`).

---

## 1. Oracle Cloud "Always Free" in 2026: real resources, sign-up from Uzbekistan, capacity, terminations, idle reclamation, is it realistic for production?

### Takeaway
Oracle halved the free Arm allowance in June 2026 (4 OCPU/24 GB -> 2 OCPU/12 GB), enforcement and PAYG treatment have been chaotic, idle instances can be reclaimed, and 2026 user reports describe silent suspensions and "out of host capacity". It is still a genuinely free box, but I would not make it the only production host for Yondo; Uzbekistan sign-up could not be verified.

### Cited Findings
**Current free resources (Oracle's own doc, fetched 2026-10-28)**
- Ampere A1 (VM.Standard.A1.Flex): 1,500 OCPU-hours and 9,000 GB-hours per month, "equivalent to 2 OCPUs and 12 GB of memory"; can be one instance or split across up to two — [Oracle Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm)
- AMD micro (VM.Standard.E2.1.Micro): up to 2 instances, each 1/8 OCPU (burstable), 1 GB RAM, 1 public IP, up to 50 Mbps — same page
- Compute and Always Free volumes must be created in the **home region** — same page
- Block volume: 200 GB total shared by boot + block volumes, 5 backups total (page says boot minimum 47 GB in one section, 50 GB in another) — same page
- Object Storage (Always-Free-only tenancy): 20 GB combined across tiers, 50,000 API requests/month; outbound data transfer 10 TB/month — same page
- Databases: 2 Autonomous (Oracle DB) at 1 OCPU/20 GB, NoSQL, and one MySQL HeatWave (50 GB) — i.e. **no PostgreSQL** — same page
- Load balancer: 1 flexible LB at 10 Mbps — same page
- The older figure (4 OCPU/24 GB = 3,000 OCPU-h/18,000 GB-h) still appears in some guides and some indexed Oracle material — [InfoQ, July 2026](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/); [Linuxiac](https://linuxiac.com/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half/)

**The 2026 cut and its chaotic rollout**
- InfoQ: change effective June 15, 2026; Oracle published no blog, customer email or announcement, only updated the docs; free-only accounts with instances above 2 OCPU/12 GB get them shut down until resized — [InfoQ](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)
- A blog author could not find an official effective date and noted enforcement was unclear in late June — [terminalbytes, 2026-06-26](https://terminalbytes.com/oracle-cloud-free-tier-changes-2026)
- LowEndSpirit thread timeline (user reports): console banner July 17 ("limits have changed to 2 OCPUs and 12 GB"); an email Aug 4 said over-limit resources must be reduced by **Aug 18, 2026** or be auto-terminated; Aug 19 a user who upgraded to PAYG at the last minute still had two instances disabled overnight, support was unreachable, recreating instances from boot volumes worked — [LowEndSpirit](https://lowendspirit.com/discussion/10956/oracle-free-tier-changing-be-careful-confirmed)
- PAYG treatment is contradictory: some users relay Oracle support saying new limits apply only to free-tier accounts and PAYG keeps 4/24 free ([InfoQ](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)); others relay support saying PAYG is also affected ([Linuxiac](https://linuxiac.com/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half/)); a blog warns overage on PAYG may be billed (est. ~$25-28/month for keeping 4/24; blogger's estimate, unverified) — [terminalbytes](https://terminalbytes.com/oracle-cloud-free-tier-changes-2026), [braindetox, 2026-06-14](https://braindetox.kr/en/posts/oracle_always_free_tier_reduced_2026.html)
- Reddit-quoted doc line: "it may not be possible to recreate resources above the updated Always Free limit" — quoted in [InfoQ](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)

**Idle reclamation (official)**
- "Idle Always Free compute instances may be reclaimed by Oracle": idle = over 7 days CPU 95th percentile < 20% **and** network < 20% **and** (A1 only) memory < 20% — [Oracle Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm). (A 2023 Oracle email quoted by a blog used 15%; thresholds changed over time — [51sec.org](https://blog.51sec.org/2023/02/oracle-cloud-cleaning-up-idle-compute.html))
- PAYG as the workaround: the 2023 Oracle notice (as relayed by that blog) said converting to PAYG stops idle reclamation and you are not charged while within Always Free limits; some prepaid cards failed to upgrade — [51sec.org](https://blog.51sec.org/2023/02/oracle-cloud-cleaning-up-idle-compute.html) (read via search summary, page not fetched). The Aug 19, 2026 report above shows PAYG did not protect against the limit enforcement.

**Capacity ("out of host capacity") and terminations (user reports)**
- Finnish blogger (free tier, ~2.5 years): Oracle deprovisioned his Arm VM after ~1 month for low usage, he could not get a replacement because of capacity; on 13 May 2026 his two x86 nodes vanished, console login failed, he suspects a silent account suspension (not confirmed, no support contact) — [fingon.iki.fi, 2026-05-19](https://www.fingon.iki.fi/blog/i-am-done-with-oracle-cloud-for-now/)
- A user got a forced reboot migration on July 29 and the instance then could not start with "out of host capacity" — [LowEndSpirit](https://lowendspirit.com/discussion/10956/oracle-free-tier-changing-be-careful-confirmed)
- A user reported a week of failed A1 creation in eu-frankfurt-1 in every availability domain; another blog claims Frankfurt/Singapore are less crowded (anecdotal, conflicting) — [Oracle community](https://community.oracle.com/customerconnect/discussions/tagged/arm/p1), [braindetox](https://braindetox.kr/en/posts/oracle_always_free_backend_2026.html) (from search summaries)
- A1 can be created in any AD except South Korea North (Chuncheon); E2.1.Micro only in one AD — same braindetox post (secondary, unverified)

**Sign-up**
- Oracle states one Free Trial/Always Free account per person; if your country is not in the sign-up list, contact Oracle Sales via the chat link — [Oracle Free Tier](https://www.oracle.com/cloud/free/) (page itself returned 403 on direct fetch; wording from search result)
- Oracle promotion docs: a 30-day free-credit promotion; upgrade to paid allowed any time during it or within 30 days after — [Oracle docs](https://docs.oracle.com/en-us/iaas/Content/GSG/Tasks/signingup.htm)
- Card verification: third-party guides say a small temporary hold is placed; a forum user's card was refused when it was a type the form did not accept (Visa, MasterCard, Amex only); address/country mismatch is a commonly reported cause of failure — [Oracle forum sign-up error](https://forums.oracle.com/ords/apexds/post/oracle-cloud-sign-up-error-0423) (via search summary)

### Inferences
- A closed beta of 20-500 users will run a small FastAPI + Postgres + Redis well below 20% CPU p95 and low network, so the **A1 instance will look "idle" by Oracle's definition** and be a reclamation candidate. Memory (>=20% of 12 GB = 2.4 GB) might be kept above the threshold by Postgres/Redis caches, but relying on that is fragile and the rule is on three conditions I cannot test.
- Free Oracle managed databases are Oracle DB/MySQL, not PostgreSQL, so Postgres must run inside Docker on the VM.
- Given the unannounced cut, silent-suspension reports and weak support, Oracle Always Free fits "free extra box for backups/staging/a second node", not "the single copy of production data".
- Docker runs on the Oracle VM itself (Ubuntu or Oracle Linux, Arm images - the repo's `python:3.12-slim` and `node:22-slim` bases are multi-arch), never on the owner's laptop. 12 GB RAM is plenty for the Yondo stack; the 1 GB micro VMs are only suitable for a monitor or a tiny relay.
- Uzbek-issued Humo/Uzcard cards will almost certainly not pass (Oracle only lists Visa/MasterCard/Amex); a Visa/Mastercard in the owner's own name with a matching address is required. This is an inference, not verified.

### Gaps
- Whether Uzbekistan is on Oracle's country list, whether Uzbek-issued Visa/Mastercard cards pass verification, and any reported Uzbekistan sign-up outcome: nothing found (searches returned no Uzbekistan-specific source).
- Which Oracle regions are closest to Tashkent and which have spare A1 capacity today (Frankfurt, Mumbai, Dubai, Jeddah etc.): no authoritative capacity data; home region cannot be changed after sign-up per one secondary source only.
- Whether PAYG accounts are exempt from the 2026 cut: contradictory user reports, no official statement.
- Oracle's own forum/Reddit counts of 2026 terminations: only individual anecdotes found, no statistics.

---

## 2. Where Docker lives and a minimal production layout with Docker Compose

### Takeaway
Docker runs on a rented Linux VM (any provider), never on the owner's laptop. One small VM with Docker Compose (Caddy + one Yondo container + Postgres + Redis), nightly encrypted pg_dump to cheap S3-compatible storage, images from GHCR, and a free uptime monitor is enough for a closed beta.

### Cited Findings
- Repo today: `compose.yaml` already defines postgres:17-alpine, redis:7-alpine (appendonly) and MinIO for local development; `infra/deploy/Dockerfile` builds one image with the API and the built web app on one port; `infra/jobs/` holds the hourly `python -m yondo_api.jobs` cron; the demo image uses test doubles (on-screen OTP, in-memory photos, no Redis) and "is NOT production" — `D:\Yondo\compose.yaml`, `D:\Yondo\infra\deploy\README.md`, `D:\Yondo\infra\deploy\Dockerfile`
- Caddy: automatic HTTPS by default from Let's Encrypt (falls back to ZeroSSL), automatic renewal and HTTP->HTTPS redirect; needs an A/AAAA record to the server, ports 80 and 443 open, and a persistent writable data directory — [Caddy docs](https://caddyserver.com/docs/automatic-https)
- Cloudflare Tunnel: `cloudflared` opens only outbound connections to Cloudflare, so the firewall can block all inbound traffic and the origin is reachable only through Cloudflare — [Cloudflare docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- Cloudflare R2 (S3-compatible): free 10 GB-month storage, 1M Class A and 10M Class B operations per month; paid $0.015/GB-month; **no egress fee** — [Cloudflare R2 pricing, fetched 2026-10-28](https://developers.cloudflare.com/r2/pricing/)
- Backblaze B2 (S3-compatible): from $6.95/TB/month, first 10 GB free, free egress up to 3x average stored data then $0.01/GB — [Backblaze pricing, fetched 2026-10-28](https://www.backblaze.com/cloud-storage/pricing)
- Neon free Postgres: 1 GB per project, 100 CU-hours/month, compute auto-suspends after 5 min and this cannot be turned off on Free, 5 GB egress, 6-hour history window; Launch plan pay-as-you-go $0.106/CU-hour + $0.35/GB-month, history up to 7 days — [Neon pricing, fetched 2026-10-28](https://neon.com/pricing)
- Upstash Redis free: 500K commands/month, 250 MB, 1 database; pay-as-you-go $0.20 per 100K commands; fixed 250 MB plan $10/month — [Upstash pricing, fetched 2026-10-28](https://upstash.com/pricing/redis)

### Inferences
Sketch (my design, standard practice, not from one source):
```
Cloud VM (Ubuntu 24.04 LTS, Docker Engine + compose plugin), firewall: 22 (key-only, ideally your IP), 80, 443
/opt/yondo/compose.prod.yaml + .env (chmod 600, secrets never in git)
  caddy     image caddy:2        ports 80/443, Caddyfile: yondo.example.uz { reverse_proxy app:8000 }, volume caddy_data
  app       ghcr.io/<owner>/yondo:<git-sha>   (API + built web, port 8000, same pattern as infra/deploy/Dockerfile but with REAL providers, not demo doubles)
  postgres  postgres:17-alpine   volume, NOT published to the host
  redis     redis:7-alpine       volume, NOT published (chat realtime)
  jobs      host cron or systemd timer: docker compose exec -T app python -m yondo_api.jobs   (hourly, as infra/jobs/)
Backups:  nightly cron: pg_dump -Fc | encrypt (age/gpg) | rclone -> Cloudflare R2 or Backblaze B2; keep 7 daily + 4 weekly; do a test restore monthly
Updates:  GitHub Actions builds+pushes image to GHCR on tag; server runs `docker compose pull && docker compose up -d` (small deploy.sh over SSH, or a pull-based timer); keep previous tag for rollback; run `alembic upgrade head` as a one-shot before switch
Monitoring: free external uptime check on /api health (UptimeRobot, Better Stack or similar - limits not verified here), email/Telegram alert; `docker logs` rotation (json-file max-size) ; disk usage alert
Photos:   S3 adapter (not yet written) -> R2 or B2 bucket (R2 has zero egress fees)
```
- Postgres in a container on the same VM is right for the closed beta (cost 0, low latency). Neon Free is not suitable for real 24/7 beta data (suspends after 5 min, 6-hour history, 1 GB) but Neon Launch is a viable later managed option. A container DB means the owner owns backups: the off-site pg_dump is non-negotiable.
- Upstash free's 500K commands/month would likely be consumed quickly by chat pub/sub; a Redis container on the VM is simpler and free.
- If the VM has no public inbound ports needed (e.g. Oracle behind restrictive networking), Cloudflare Tunnel can replace Caddy's inbound exposure; otherwise Caddy alone is simplest.
- A single-VM design has no high availability: a VM reboot or provider incident means downtime. Acceptable for a closed beta if backups exist and the team states it.

### Gaps
- Free-plan limits of uptime monitors (UptimeRobot/Better Stack etc.) not researched.
- Whether Cloudflare Tunnel/Pages are free and under what terms: the Cloudflare pages fetched did not state pricing; I did not verify as of 2026. Cloudflare Pages (static hosting) not researched at all.
- GHCR pricing/limits for private images not researched (public images are the simple route).
- ARM vs x86 compatibility of every Python wheel in `apps/api` not tested.

---

## 3. Alternatives: real 2026 prices/limits and latency from Tashkent

### Takeaway
Hetzner is still the price leader on paper but, as of today, all its cloud server plans show "unavailable" on its own pricing pages after two 2026 price rises and a capacity incident open since 2026-06-26. Contabo, DigitalOcean (Frankfurt) and local Tashkent VDS are the practical paid options; PaaS (Render, Fly, Railway, Koyeb) work but cost more per unit of resource and the free tiers are demo-grade.

### Cited Findings

**Hetzner Cloud (fetched 2026-10-28)**
- Cost-Optimized plans: CX23 2 vCPU/4 GB/40 GB NVMe EUR 5.99; CAX11 (Arm) 2 vCPU/4 GB EUR 6.49; CX33 4 vCPU/8 GB EUR 8.99; CAX21 4 vCPU/8 GB EUR 10.99; 20 TB traffic included; locations NBG1, HEL1; prices excl. VAT; **every plan's create button says "This product is currently unavailable"** — [Hetzner Cost-Optimized](https://www.hetzner.com/cloud/cost-optimized/)
- Regular Performance (CPX) now far dearer: CPX22 2 vCPU/4 GB EUR 19.99; CPX02 1 vCPU/1 GB EUR 6.49; also "currently unavailable"; Singapore (SIN1) has only 0.5-5 TB traffic — [Hetzner Regular Performance](https://www.hetzner.com/cloud/regular-performance/)
- Official price adjustment effective 15 June 2026 08:00 CEST for new orders and rescales (excl. IPv4): CX23 3.99->5.49, CAX11 4.49->5.99, CX33 6.49->8.49, CPX22 7.99->19.49, CCX13 15.99->42.99; certain changes to legacy-priced servers can trigger the new price — [Hetzner price adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
- Status page incident "Limited availability of cloud instances", start 2026-06-26, still listed with no resolved label — [Hetzner status](https://status.hetzner.com/); a search summary says Hetzner states provisioning is possible only to a limited extent and affected existing customers are chosen at random — [search result via Findstack/Borncity](https://borncity.com/blog/?p=329200)
- Third-party analysis: prior April 1, 2026 increase (CX22/CAX11 3.29->4.49 per one source) and four price changes in 2026 — [agentdeals.dev](https://agentdeals.dev/hetzner-pricing-2026), [privatedevops](https://privatedevops.com/news/hetzner-june-2026-cloud-price-increase-what-to-do)

**Contabo (fetched 2026-10-28; page text fragmented, verify at checkout)**
- "Cloud VPS 4": 4 vCPU, 8 GB RAM, 100 GB SSD, 200 Mbit/s, outbound "unlimited" under fair use (may be throttled): EUR 4.40/mo on a 24-month term (20% off), EUR 5.50 regular; "Cloud VPS 6": 6 vCPU/12 GB/200 GB SSD EUR 6.00 (24 mo) / EUR 7.50; "Cloud VPS 8": 8 vCPU/24 GB EUR 11.20 / EUR 14.00; locations EU, UK, US, Singapore, Japan, India, Australia; minimum contract 1 month — [Contabo VPS](https://contabo.com/en/vps/)

**DigitalOcean (fetched 2026-10-28)**
- Basic Droplets: 512 MiB/1 vCPU/10 GiB/500 GiB transfer $4; 1 GiB/1 vCPU/25 GiB $6; 2 GiB/1 vCPU/50 GiB $12; 2 GiB/2 vCPU/60 GiB $18; 4 GiB/2 vCPU/80 GiB/4,000 GiB $24; datacenters include Frankfurt, Amsterdam, Bangalore, Singapore (per-plan regional availability not shown) — [DigitalOcean Droplets](https://www.digitalocean.com/pricing/droplets)

**Fly.io (fetched 2026-10-28)**
- No free tier; new accounts get a trial of up to 2 hours of machine runtime or 7 days; shared-cpu-1x always-on 256 MB $2.19/mo, 512 MB $3.69, 1 GB $6.70 (prices vary by region); volumes $0.15/GB-month; outbound $0.02/GB NA/Europe, $0.04/GB Asia-Pacific, $0.12/GB India/Africa; Managed Postgres from $38/month plus $0.28/GB storage; no minimum bill — [Fly.io pricing](https://docs.fly.io/about/pricing)

**Render (fetched 2026-10-28 for free tier; paid prices from secondary sources)**
- Free web service sleeps after 15 min of no traffic, ~1 min to wake, 750 instance hours/month; free Postgres 1 GB, expires 30 days after creation with a 14-day grace period, no backups; free Key Value is in-memory and lost on restart — [Render free docs](https://render.com/docs/free)
- Paid (secondary): Starter $7/mo (512 MB, 0.5 CPU), Standard $25/mo (2 GB, 1 CPU), Postgres Basic-256mb $6/mo with storage billed separately (~$0.30/GB-month); workspace fee sources disagree; one July-2026 third-party post title mentions a "1 August plan change and 20x bandwidth cut" I could not read — [PricingSaaS](https://pricingsaas.com/companies/render), [Makerkit comparison](https://makerkit.dev/pricing-calculator/render), [jwatte.com](https://jwatte.com/blog/render-com-platform-review.md)

**Railway (fetched 2026-10-28)**
- Free: $1/month credit, up to 0.5 GB/1 vCPU per service; one-time $5 trial credit for 30 days; Hobby $5/month incl. $5 usage; Pro $20/month; usage rates: $0.00000772/vCPU-s (~$20 per vCPU-month), $0.00000386/GB-s (~$10 per GB-month), volumes $0.15/GB-month, egress $0.05/GB — [Railway pricing](https://railway.com/pricing)

**Koyeb (fetched 2026-10-28)**
- Pricing page lists no free compute instance; Pro $29/month incl. $10 compute credit; managed serverless Postgres free "5h" tier (0.25 vCPU, 1 GB) then Small $29.76/month; regions include Frankfurt, Singapore, Washington for Postgres; 1 TB bandwidth included then $0.02/GB EU/US, $0.04/GB Asia — [Koyeb pricing](https://www.koyeb.com/pricing)

**Google Cloud / AWS free tiers**
- GCP Always Free: one e2-micro only in us-west1, us-central1 or us-east1; 30 GB standard disk; 1 GB/month outbound from North America; $300 trial lasts 90 days — [Google Cloud free features](https://docs.cloud.google.com/free/docs/free-cloud-features)
- AWS: only a secondary mention of a July 2025 free tier model with $200 credits and a 6-month plan — [braindetox](https://braindetox.kr/en/posts/oracle_always_free_tier_reduced_2026.html)

**Uzbekistan-local options**
- aHOST (Tashkent, SUVAN NET LLC): VDS Cloud 10 = 125,000 UZS/mo, Cloud 20 = 140,000, Cloud 100 = 320,000, Cloud 300 = 770,000, Cloud 400 = 1,040,000 UZS/mo; own datacenter in TAS-IX; 99.9% uptime claim; daily backups; RU/UZ/EN support (listing prices from aggregator pages; vCPU/RAM per plan not retrieved) — [whtop aHOST plans](https://www.whtop.com/plans/ahost.uz/142321), [whtop VDS Cloud 20](https://www.whtop.com/plans/ahost.uz/142322)
- pro-data.tech (Tashkent): "Generic 1" VDS 24 vCPU/32 GB/240 GB 3,377,600 UZS/mo, wire transfer payment, 100 Mbit/s to Internet and TAS-IX — [whtop pro-data](https://www.whtop.com/plans/pro-data.tech/147030), [pro-data.tech](https://pro-data.tech/en/dedicated-server)
- Serverspace (ITGLOBAL) opened VPS in the East Telecom YA DC in Tashkent (2026-03-11); designed "in line with Tier III recommendations", not formally certified; payment options not stated — [Serverspace](https://serverspace.us/about/news/new-serverspace-data-center-in-uzbekistan-tashkent-located/)
- A colocation listing reports no direct cloud on-ramps in Tashkent (Sept 2025), nearest hubs Frankfurt or Moscow; Zenlayer lists no public POPs in Uzbekistan — [Inflect](https://inflect.com/datacenters/emea/uzbekistan/tashkent), [Zenlayer](https://zenlayer.com/global/countries/uzbekistan)

**Cloudflare**
- R2 and Tunnel facts in Section 2. A listing says average end-user latency in Tashkent is 87 ms broadband / 91 ms mobile (consumer averages, not server latency) — [SpeedGeo](https://speedgeo.net/statistics/uzbekistan/tashkent)

**Latency from Tashkent**
- I found **no measured Tashkent-to-region latency data** (RIPE Atlas, cloudping-type sites). Only a flight-route distance (Tashkent-Frankfurt 2,531 NM) — [AirNavRadar](https://en.airnavradar.com/data/mode-s/507C54).
- My own calculation (great-circle distance, fiber at ~200,000 km/s, RTT = 2 x distance / 200,000; this is a physical **minimum**, real routes are longer and via Russia/Kazakhstan or Turkey): Dubai 2,207 km -> >=22 ms; Mumbai 2,494 km -> >=25 ms; Moscow 2,792 km -> >=28 ms; Istanbul 3,342 km -> >=33 ms; Helsinki 3,655 km -> >=37 ms; Warsaw 3,792 km -> >=38 ms; Nuremberg 4,518 km -> >=45 ms; Frankfurt 4,672 km -> >=47 ms; Singapore 5,631 km -> >=56 ms.

### Inferences
- Hetzner would be the best-value choice (CAX11 EUR 6.49 / CX23 EUR 5.99 incl. IPv4 per the pricing pages; EUR 5.99 / 5.49 excl. IPv4 per the adjustment notice) if capacity returns; its own site says unavailable today, so planning around it is risky. Re-check before deciding.
- A Frankfurt/Nuremberg/Helsinki server will likely deliver 60-120 ms real RTT to Tashkent (my estimate from the physical floor plus typical routing overhead, not measured). For a booking/chat app that is acceptable; the web app's static files can sit behind Cloudflare's CDN. A Tashkent VDS would cut it to a few ms for local users.
- Moscow-region hosting is closer by distance but I did not research sanctions/payment/politics; given Yondo's international card and cloud-vendor dependencies, I would not recommend it (unverified judgment).
- Fly/Railway/Render/Koyeb per-unit prices are 2-4x a VPS for the same RAM, but include deploy automation and TLS; Fly egress is 6x dearer for India ($0.12/GB) than Europe, so choose Frankfurt over Mumbai there.
- Indicative closed-beta cost (my arithmetic from the cited prices): VPS EUR 6-12/month + R2 free tier (0 within 10 GB) + free uptime monitor = about EUR 6-12/month; Render equivalent = Starter $7 + Postgres $6 + storage = >= $13/month with a smaller box; Fly with Managed Postgres starts at $38/month + compute.

### Gaps
- Real 2026 latency/ping figures from Tashkent to Frankfurt, Helsinki, Istanbul, Mumbai, Dubai: not found; must be measured (ping/mtr from the university network to a trial VM).
- Whether Hetzner, Contabo, DigitalOcean, Fly etc. accept payment from Uzbekistan (Uzbek-issued Visa/Mastercard, Humo/Uzcard), ID verification requirements, and account-approval friction: not researched; this is likely a practical blocker for a foreign provider and should be checked first.
- Contabo's current availability, real-world performance and support quality: not researched; Contabo plan names in the fetched text ("Cloud VPS 4/6/8") may be incomplete.
- DigitalOcean managed Postgres pricing, new-user credits, and per-region plan availability: not fetched. Render's current paid pricing and any 1 August 2026 plan change: primary page did not render.
- AWS 2026 free-tier terms (primary source); Cloudflare Pages and Tunnel pricing; Supabase intentionally excluded per the owner.
- UZS->EUR/USD conversion for local VDS prices and each local plan's vCPU/RAM: not retrieved.

---

## 4. Data residency and legal context for hosting abroad (Uzbekistan)

### Takeaway
Since the March 2026 amendment, only biometric and genetic data (and telecom subscriber data) must be stored on servers in Uzbekistan; other personal data may be stored abroad under conditions, and Germany, Finland, the USA and Singapore appear on the 49-country simplified-transfer list. Yondo's identity-verification step must be checked: if it stores biometric data, that part must stay in Uzbekistan.

### Cited Findings
- Law No. 1125 (26 March 2026) amended the Law "On Personal Data": mandatory in-country storage now covers only biometric and genetic data plus telecom subscriber data; other personal data may be stored/processed abroad if the destination country is deemed adequate, standard contractual clauses/BCRs approved by the authorized body are used, or approved international standards are followed — [Legal 500 (Vakhidov & Partners)](https://www.legal500.com/developments/thought-leadership/legislative-updates-in-the-field-of-artificial-intelligence-and-personal-data-regulation-uzbekistan/) (read via search summary; the page returned 404 on a later direct fetch)
- A Cabinet of Ministers resolution adopted July 29, 2026 and published on Lex.uz approves 49 countries for simplified transfers; the article names Germany, Finland, the USA and Singapore among 20 listed; India and UAE are not named in the visible part; EU as a bloc not mentioned — [Kun.uz, 2026-08-04](https://kun.uz/en/news/2026/08/04/uzbekistan-approves-49-countries-for-simplified-personal-data-transfers)
- Before the reform, the localization rule required storing citizens' personal data in-country, with vague interpretation reported by experts in July 2025 — [Kun.uz, 2025-07](https://ad.kun.uz/en/news/2025/07/22/experts-urge-uzbekistan-to-revise-data-localization-rules-to-support-innovation)

### Inferences
- Hosting in Germany/Finland (Hetzner, DigitalOcean Frankfurt, Contabo EU) is likely compliant for ordinary personal data (names, phones, bookings), if the 49-country list includes the host country and the operator meets the other conditions. Whether Yondo's companion identity verification (selfies/passport photos) counts as "biometric" is a question for a lawyer; if yes, that data must be stored in Uzbekistan (a local VDS for that component, or an in-country object store).
- The repo notes that the owner said legal review is not required; I flag this as a compliance item only, without overriding that decision.

### Gaps
- Full text of Law No. 1125 and the Cabinet resolution (Lex.uz) not read; whether the complete 49-country list contains all EU states and India/UAE is unverified; operator registration/notification duties not researched.

---

## 5. Which option for a closed beta, and the upgrade path (plus plain summary and ranked recommendation)

### Takeaway
Run Docker Compose on one inexpensive paid VPS (EUR 6-12/month), with off-site encrypted backups to R2/B2, and keep Render for the public demo. Choose the VPS provider by whether the owner can actually pay and by availability today: Hetzner if ordering works, otherwise DigitalOcean Frankfurt, Contabo, or a Tashkent VDS. Use Oracle Always Free only as an extra free box.

### Cited Findings
(see Sections 1-4 for sources; no new facts introduced here)

### Inferences
**Ranked recommendation (closed beta, 20-500 users, 24/7, near-zero cost)**
1. **One paid VPS with Docker Compose in an EU datacenter, EUR 6-12/month.** Order of preference: Hetzner CAX11/CX23 (Helsinki/Nuremberg) when "available" again; DigitalOcean Frankfurt $12-24/month (works today, but check Uzbekistan payment); Contabo Cloud VPS (most RAM per euro, but check reviews/performance). 2 vCPU/4 GB is the sensible starting size (my sizing estimate, to be confirmed with a load test).
2. **Tashkent VDS (aHOST, pro-data.tech, Serverspace)** if foreign payment is impossible, if you want the lowest latency for local users, or if biometric data must stay in-country; pay in UZS; get specs and a trial first. Could also be the in-country component of a hybrid.
3. **Oracle Always Free (2 OCPU/12 GB A1)** as a free secondary: backups target, staging, or monitoring node. Do not keep the only copy of data there (silent suspensions, reclamation, unannounced cuts, Uzbekistan sign-up unverified).
4. **PaaS (Render Starter + Postgres, Railway Hobby, Fly)** if zero server administration is worth 2-4x the price; keep the existing Render free service only as the demo (sleeps after 15 min, free Postgres expires after 30 days).
- Do not use: Google Cloud Always Free (US-only micro, 1 GB egress), Neon Free or Upstash Free as the real beta backend (suspend after 5 min / 500K commands).

**Upgrade path (stages are my plan, not sourced)**
- Stage 0 (now): demo on Render free (as in `infra/deploy`), with test doubles.
- Stage 1 (closed beta): 1 VPS, Compose stack above, photos in R2/B2 (S3 adapter to be written), nightly pg_dump, uptime monitor.
- Stage 2 (hundreds to low thousands): resize the VPS (vertical), add a second VPS for Postgres or move to managed Postgres (Neon Launch pay-as-you-go $0.106/CU-hour + $0.35/GB, or a provider-managed DB), put Cloudflare in front for static/CDN, keep Redis on the VM.
- Stage 3 (growth/resilience): 2+ app nodes behind a load balancer, managed Postgres with replicas, move to a provider with a Tashkent presence if in-country storage becomes mandatory for more data types.

**10-line plain summary for the owner**
1. Docker does not live on your laptop; it lives on a rented server (a "VPS") that runs 24/7 in a datacenter.
2. Oracle's free server exists, but in June 2026 Oracle halved it (now 2 CPU / 12 GB) without announcing it.
3. Oracle can also take back servers it thinks are "idle", and some people lost servers or whole accounts without warning; for a real app that is too risky as the only home.
4. I could not confirm that Oracle accepts sign-ups from Uzbekistan or Uzbek bank cards; this has to be tried.
5. Hetzner is the cheapest good option (about EUR 6-7/month), but today its website says new servers are "unavailable"; check again before deciding.
6. Practical alternatives today: DigitalOcean Frankfurt ($12-24/month), Contabo (about EUR 5.50/month for 8 GB), or a Tashkent local server paid in UZS.
7. Since March 2026 only biometric/genetic data must stay in Uzbekistan; ordinary data may be abroad (Germany, Finland, USA, Singapore are on the approved list). Ask a lawyer about the companion ID-photo/selfie check.
8. Plan: one small server running Docker Compose (Caddy for HTTPS, Yondo, Postgres, Redis), nightly encrypted database backup to Cloudflare R2 or Backblaze B2 (both have free starter space).
9. Keep the free Render deployment only as the public demo; do not put real users' data on it (it sleeps, and its free database expires after 30 days).
10. Ranked: (1) paid EU VPS with Compose, ~EUR 6-12/month; (2) Tashkent VDS if payment/latency/data-law needs it; (3) Oracle Always Free as an extra free box only; (4) managed PaaS if you prefer no server admin and accept higher cost.

### Gaps
- Which provider the owner can actually pay for from Uzbekistan, and real latency from the university network: both must be tested before the final choice.
- User growth thresholds for upgrades: no data; needs a load test of the Yondo API with chat on the chosen VPS.
