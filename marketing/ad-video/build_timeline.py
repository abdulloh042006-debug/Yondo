"""Builds the per-language timeline (voice placement, phrase chunks, SFX events) -> timeline.json"""
import json, wave, re
import numpy as np

AD = '/tmp/claude-0/-home-claude/80ed5239-9a87-5b7a-bb32-cb2c8e001f18/scratchpad/ad'

TEXT = {
 'uz': {
  'sub': ['Yangi shahar. Rejangiz bor. Hamroh-chi?',
          'Shaharni ko‘rmoqchiman… lekin kim bilan?',
          'Yondo — suhbat, sayr va til mashqi uchun hamroh topish platformasi.',
          'Men hamrohman. Tillarim, qiziqishlarim, xizmatlarim va narxlarim — profilimda ochiq.',
          'Profilni ko‘rdim, narxni oldindan bildim va bron so‘rovini yubordim.',
          'Uchrashuvlar — faqat jamoat joylarida. Har bir ariza ko‘rib chiqiladi.',
          'Yondo. Doim yoningda. Tez kunda!'],
  'v1': ['Yangi shahar.', 'Rejangiz bor.', 'Hamroh-chi?'],
  'v2': ['Shaharni ko‘rmoqchiman…', 'lekin kim bilan?'],
  'slogan': 'doim yoningda',
  'v3': 'Hamroh topish platformasi', 'v3chips': ['Suhbat', 'Sayr', 'Til mashqi'],
  'v4': 'Men hamrohman', 'v4chips': ['Tillar', 'Qiziqishlar', 'Xizmatlar', 'Narxlar — ochiq'],
  'v5': ['Profilni ko‘rdim', 'Narx — oldindan', 'Bron so‘rovi yuborildi'],
  'v6': ['Faqat jamoat joylarida', 'Har bir ariza ko‘rib chiqiladi'],
  'end1': 'Doim yoningda.', 'end2': 'Tez kunda!',
  'demo': 'DEMO ma’lumotlar', 'disc': 'Ekrandagi ma’lumotlar namunaviy (DEMO)',
 },
 'ru': {
  'sub': ['Новый город. План есть. А компания?',
          'Хочу увидеть город… но с кем?',
          'Yondo — платформа, где можно найти компаньона для беседы, прогулки и языковой практики.',
          'Я гид-компаньон. Мои языки, интересы, услуги и цены — открыто в профиле.',
          'Посмотрел профиль, сразу узнал цену и отправил запрос на бронь.',
          'Встречи — только в общественных местах. Каждая заявка проходит проверку.',
          'Yondo. Всегда рядом. Скоро!'],
  'v1': ['Новый город.', 'План есть.', 'А компания?'],
  'v2': ['Хочу увидеть город…', 'но с кем?'],
  'slogan': 'всегда рядом',
  'v3': 'Платформа для поиска компаньона', 'v3chips': ['Беседа', 'Прогулка', 'Языковая практика'],
  'v4': 'Я гид-компаньон', 'v4chips': ['Языки', 'Интересы', 'Услуги', 'Цены — открыто'],
  'v5': ['Посмотрел профиль', 'Цена — заранее', 'Запрос на бронь отправлен'],
  'v6': ['Только в общественных местах', 'Каждая заявка проходит проверку'],
  'end1': 'Всегда рядом.', 'end2': 'Скоро!',
  'demo': 'DEMO данные', 'disc': 'Данные на экране — демонстрационные (DEMO)',
 },
}


def load(p):
    w = wave.open(p)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    return a / max(1, np.abs(a).max()), w.getframerate()


def chunks(p, min_pause=0.3):
    a, sr = load(p)
    hop = int(0.01 * sr)
    env = np.array([np.abs(a[i:i + hop]).mean() for i in range(0, len(a), hop)])
    on = env > 0.025
    regs, s = [], None
    for i, v in enumerate(on):
        t = i * hop / sr
        if v and s is None:
            s = t
        if not v and s is not None:
            regs.append([s, t]); s = None
    if s is not None:
        regs.append([s, len(a) / sr])
    merged = []
    for r in regs:
        if merged and r[0] - merged[-1][1] < min_pause:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    merged = [r for r in merged if r[1] - r[0] > 0.12]
    return [[round(x, 3) for x in r] for r in merged], len(a) / sr


out = {}
for lang in ('uz', 'ru'):
    V = []
    for i in range(1, 8):
        ch, d = chunks(f'{AD}/voice/{lang}-0{i}.wav')
        V.append({'d': round(d, 3), 'ch': ch})
    t = 0.9
    V[0]['s'] = t; t += V[0]['d'] + 0.3
    V[1]['s'] = t; t += V[1]['d'] + 0.25
    L = t; t += 1.25
    V[2]['s'] = t; t += V[2]['d'] + 0.45
    V[3]['s'] = t; t += V[3]['d'] + 0.35
    V[4]['s'] = t; t += V[4]['d'] + 0.35
    V[5]['s'] = t; t += V[5]['d'] + 0.3
    E = t; t += 0.55
    V[6]['s'] = t; t += V[6]['d'] + 1.7
    total = round(t, 3)
    for v in V:
        v['e'] = round(v['s'] + v['d'], 3)
        v['cs'] = [round(v['s'] + c[0], 3) for c in v['ch']]

    def phrase_times(v, n):
        cs = v['cs']
        if len(cs) >= n:
            # take the first n-1 chunk starts + the start of the last chunk group
            if len(cs) == n:
                return cs
            step = len(cs) / n
            return [cs[int(round(k * step))] for k in range(n)]
        return [round(v['s'] + v['d'] * k / n, 3) for k in range(n)]

    T = TEXT[lang]
    tl = {'V': V, 'L': round(L, 3), 'E': round(E, 3), 'total': total,
          'p1': phrase_times(V[0], 3), 'p2': phrase_times(V[1], 2), 'p4': phrase_times(V[3], 4),
          'p5': phrase_times(V[4], 3), 'p6': phrase_times(V[5], 2), 'p7': phrase_times(V[6], 3)}
    v3 = V[2]
    tl['p3'] = [round(v3['s'] + v3['d'] * f, 3) for f in (0.22, 0.4, 0.58)]
    tl['swap'] = [round(v3['e'] - 1.6, 3), round(v3['e'] - 1.05, 3), round(v3['e'] - 0.5, 3)]
    ev = []
    A = ev.append
    A(['riser', 0.0, 0.9]); A(['impact', 0.85])
    for x in tl['p1']: A(['tick', x])
    A(['whoosh', V[1]['s'] - 0.35])
    A(['riser', L - 0.6, 0.6]); A(['whoosh', L + 0.05]); A(['impact_big', L + 0.62]); A(['chime', L + 0.65])
    A(['whoosh', V[2]['s'] + 0.45])
    for x in tl['p3']: A(['tap', x]); A(['pop', x + 0.06])
    for x in tl['swap']: A(['hit', x])
    A(['swipe', V[3]['s'] - 0.2])
    for x in tl['p4']: A(['pop', x + 0.05])
    p5 = tl['p5']
    A(['tap', p5[1] - 0.35]); A(['whoosh', p5[1] - 0.2]); A(['tap', p5[2] + 0.35]); A(['ding', p5[2] + 0.75])
    A(['swipe', V[5]['s'] - 0.2]); A(['pop', V[5]['s'] + 0.25])
    A(['tap', tl['p6'][1] + 0.4]); A(['ding', tl['p6'][1] + 0.8])
    A(['whoosh_big', E]); A(['impact_big', tl['p7'][0]]); A(['chime', tl['p7'][1]]); A(['final', tl['p7'][2]])
    tl['ev'] = [[e[0]] + [round(x, 3) for x in e[1:]] for e in ev]
    tl['text'] = T
    out[lang] = tl
    print(lang, 'total', total, 'L', L, 'E', E, 'chunks', [len(v['ch']) for v in V])
json.dump(out, open(f'{AD}/timeline.json', 'w'), ensure_ascii=False, indent=1)
