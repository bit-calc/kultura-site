#!/usr/bin/env python3
"""Build kulturaba.com: per-language homes (from _build/app.html) + static SEO pages.

Run from anywhere:  python3 _build/build.py  && node _build/prerender.js
Inputs : _build/app.html (the one-page site, source of content data)
         _build/content/services_seo.py, _build/content/articles_new.py
Outputs: index.html, ru/, en/, servicios/, blog/, productos/, ru/uslugi/..., en/services/...,
         assets/, sitemap.xml, robots.txt, llms.txt, 404.html, _headers
"""
import json, os, re, subprocess, sys, html, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, 'content'))
from services_seo import SERVICES, ARTICLE_SLUGS          # noqa: E402
from articles_new import ARTICLES_NEW                     # noqa: E402
from articles_batch2 import ARTICLES_B2                   # noqa: E402

DOMAIN = 'https://kulturaba.com'
TODAY = '2026-11-14'
# pages whose content changed later (key: Spanish URL of the page group) -> date for sitemap <lastmod>
LASTMOD = {'/': '2026-11-18', '/servicios/manicura-rusa/': '2026-11-18', '/servicios/pedicura-rusa/': '2026-11-18', '/servicios/manicura-pedicura-cuatro-manos/': '2026-11-18',
           '/blog/': '2026-11-18', '/blog/manicura-rusa-precio-buenos-aires/': '2026-11-18', '/blog/manicura-rusa-o-semipermanente-diferencias/': '2026-11-18',
           '/blog/manicura-en-microcentro/': '2026-11-18', '/blog/como-retirar-semipermanente-sin-danar-la-una/': '2026-11-18',
           '/blog/diseno-de-unas-minimalismo-o-atrevido/': '2026-11-18',
           '/blog/kapping-soft-gel-unas-esculpidas-diferencias/': '2026-11-18',
           '/blog/manicura-francesa/': '2026-11-18',
           '/blog/manicura-rusa-esmaltado-pegado-a-la-cuticula/': '2026-11-18',
           '/blog/manicura-y-pedicura-a-cuatro-manos/': '2026-11-18',
           '/blog/pedicura-rusa-smart-que-incluye/': '2026-11-18'}
LANGS = ['es', 'ru', 'en']
PFX = {'es': '', 'ru': '/ru', 'en': '/en'}
SEG = {'svc': {'es': 'servicios', 'ru': 'uslugi', 'en': 'services'},
       'blog': {'es': 'blog', 'ru': 'blog', 'en': 'blog'},
       'prod': {'es': 'productos', 'ru': 'produkty', 'en': 'products'}}
OG_LOCALE = {'es': 'es_AR', 'ru': 'ru_RU', 'en': 'en_US'}
INDEXNOW_KEY = '7f3c9a51e2d84b6fa0c1d5e8b9a24c67'
MAPS = 'https://maps.app.goo.gl/TiiG9uPdZeCiG7pJ8'
IG = 'https://www.instagram.com/kultura.ba/'
FB = 'https://www.facebook.com/profile.php?id=61591149431358'
TG = 'https://t.me/kulturaba'
GSC_META = '<meta name="google-site-verification" content="7s5pBvu950L4dqgWdP1ySm9-_SQzntV4EEBasq_62UQ">'  # Search Console, KULTURA Google account

# ------------------------------------------------------------------ data from the app
APP = open(os.path.join(HERE, 'app.html'), encoding='utf-8').read()

def extract_data():
    m = re.search(r'<script>(.*?)</script>', APP, re.S)
    js = m.group(1)
    cut = js.find('const LANGS')
    names = re.findall(r'^const\s+([A-Z][A-Z0-9_]*)\s*=', js[:cut], re.M)
    tmp = os.path.join(HERE, '.data_tmp.js')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(js[:cut] + '\nmodule.exports={' + ','.join(names) + '};\n')
    out = subprocess.check_output(['node', '-e', f"const d=require({json.dumps(tmp)});process.stdout.write(JSON.stringify(d))"])
    os.remove(tmp)
    return json.loads(out)

D = extract_data()
U, R, SVC, ARTS, PRODS, LINES, PEOPLE, WHO = D['U'], D['R'], D['SVC'], D['ARTS'], D['PRODS'], D['LINES'], D['PEOPLE'], D['WHO']
BOOK, WA = D['BOOK'], D['WA']

def L(o, lang):
    if o is None: return ''
    if isinstance(o, str): return o
    return o.get(lang) if o.get(lang) is not None else o.get('es', '')

def t(k, lang): return U[k][LANGS.index(lang)] if k in U else ''
def e(s): return html.escape(str(s), quote=True)

def fmt(n, lang):
    if lang == 'ru': return f'{n:,}'.replace(',', ' ') + ' ARS'
    if lang == 'en': return f'ARS {n:,}'
    return '$' + f'{n:,}'.replace(',', '.')

def dur(m, lang):
    if not m: return ''
    h, r = divmod(m, 60)
    s = f"{r} {t('min', lang)}" if not h else (f"{h} {t('h', lang)} {r} {t('min', lang)}" if r else f"{h} {t('h', lang)}")
    return t('upto', lang) + ' ' + s

def wa(msg): return WA + '?text=' + __import__('urllib.parse').parse.quote(msg)

# ------------------------------------------------------------------ extra UI strings
X = {
 'svc_all': ['Servicios y precios', 'Услуги и цены', 'Services and prices'],
 'svc_all_lead': ['Color, cortes, tratamientos, manicura rusa, pedicura SMART, pestañas y cejas en Microcentro, Buenos Aires. Precios de referencia en pesos, según el sistema de reservas del estudio (noviembre de 2026).',
                  'Окрашивание, стрижки, уход, русский маникюр, SMART-педикюр, ресницы и брови в Микроцентро, Буэнос-Айрес. Ориентировочные цены в песо по системе записи студии (ноябрь 2026).',
                  'Colour, cuts, treatments, Russian manicure, SMART pedicure, lashes and brows in Microcentro, Buenos Aires. Guide prices in pesos from the studio booking system (November 2026).'],
 'blog_lead': ['Técnicas, cuidado y respuestas a lo que más nos preguntan en el estudio.', 'Техники, уход и ответы на частые вопросы из студии.', 'Techniques, care and answers to what we’re asked most in the studio.'],
 'prod_lead': ['Cuidado y styling de Schwarzkopf Professional para casa. Todos los productos se compran en el estudio o por WhatsApp. KULTURA es partner oficial de Schwarzkopf Professional.',
               'Уход и стайлинг Schwarzkopf Professional для дома. Всё можно купить в студии или заказать в WhatsApp. KULTURA — официальный партнёр Schwarzkopf Professional.',
               'Schwarzkopf Professional care and styling for home. Buy everything in the studio or on WhatsApp. KULTURA is an official Schwarzkopf Professional partner.'],
 'home': ['Inicio', 'Главная', 'Home'],
 'faq': ['Preguntas frecuentes', 'Частые вопросы', 'Frequently asked questions'],
 'prices': ['Precios', 'Цены', 'Prices'],
 'more_svc': ['Otros servicios', 'Другие услуги', 'Other services'],
 'read_more': ['Leer en el Journal', 'Читать в журнале', 'Read in the Journal'],
 'book_cta': ['Reservá tu turno', 'Запишитесь', 'Book your visit'],
 'visit': ['Dónde estamos', 'Где мы', 'Where we are'],
 'langs_spoken': ['Atendemos en español y ruso; en inglés, con traductor.', 'Говорим по-русски и по-испански; по-английски — через переводчика.', 'We speak Spanish and Russian; English with a translator.'],
 'all_arts': ['Todos los artículos', 'Все статьи', 'All articles'],
 'buy': ['Comprar por WhatsApp', 'Купить в WhatsApp', 'Buy on WhatsApp'],
 'for': ['Para quién', 'Кому подойдёт', 'Who it’s for'],
 'does': ['Qué hace', 'Что делает', 'What it does'],
 'use': ['Cómo usarlo', 'Как использовать', 'How to use'],
 'same_line': ['De la misma línea', 'Из той же линии', 'From the same line'],
 'src': ['Resultados según Schwarzkopf Professional.', 'Результаты по данным Schwarzkopf Professional.', 'Results according to Schwarzkopf Professional.'],
 'svc_page': ['Todo sobre el servicio y preguntas frecuentes', 'Всё об услуге и частые вопросы', 'All about this service and FAQ'],
 'svc_hub_link': ['Todos los servicios y precios', 'Все услуги и цены', 'All services and prices'],
 'blog_hub_link': ['Todos los artículos del Journal', 'Все статьи журнала', 'All Journal articles'],
 'prod_hub_link': ['Catálogo completo de productos', 'Весь каталог продукции', 'Full product catalogue'],
 'idx_svc': ['Servicios', 'Услуги', 'Services'],
 'idx_blog': ['Journal', 'Журнал', 'Journal'],
 'idx_prod': ['Productos', 'Продукция', 'Products'],
 'home_title': ['KULTURA · Salón de belleza ruso en Microcentro, Buenos Aires',
                'KULTURA — русский салон красоты в Буэнос-Айресе',
                'KULTURA · Russian beauty salon in Microcentro, Buenos Aires'],
 'home_desc': ['Salón de belleza ruso en Microcentro, Buenos Aires: AirTouch, rubio total, cortes, manicura rusa, pedicura SMART, pestañas y cejas. Partner oficial de Schwarzkopf.',
               'Русский салон красоты в Микроцентро, Буэнос-Айрес: AirTouch, тотал блонд, стрижки, русский маникюр, SMART-педикюр, ресницы и брови. Партнёр Schwarzkopf Professional.',
               'Russian beauty salon in Microcentro, Buenos Aires: AirTouch, total blonde, cuts, Russian manicure, SMART pedicure, lashes and brows. Official Schwarzkopf partner.'],
 'blog_desc': ['Journal de KULTURA: técnicas de color, manicura rusa, pedicura SMART, pestañas y cejas, cuidado del pelo y respuestas a lo que más nos preguntan en el estudio.',
               'Журнал KULTURA: техники окрашивания, русский маникюр, SMART-педикюр, ресницы и брови, уход за волосами и ответы на частые вопросы клиентов студии.',
               'KULTURA Journal: colour techniques, Russian manicure, SMART pedicure, lashes and brows, hair care and answers to what we’re asked most in the studio.'],
 'nf': ['Página no encontrada', 'Страница не найдена', 'Page not found'],
}
def x(k, lang): return X[k][LANGS.index(lang)]

# ------------------------------------------------------------------ URLs
def home_url(lang): return PFX[lang] + '/'
def hub(kind, lang): return f"{PFX[lang]}/{SEG[kind][lang]}/"
def svc_url(sid, lang): return f"{hub('svc', lang)}{SERVICES[sid]['slug'][lang]}/"

# meta descriptions for the Journal articles that live in app.html (their lead is too short for a search snippet)
ART_DESC = {
 'airtouch': {'es': 'AirTouch no es mechas ni balayage: Roman, colorista principal de KULTURA en Buenos Aires, explica el método, la corrección, el tiempo y el precio.',
              'ru': 'Чем AirTouch отличается от мелирования и балаяжа: метод, коррекция, время и цена. Рассказывает Роман, главный колорист KULTURA в Буэнос-Айресе.',
              'en': 'AirTouch isn’t highlights or balayage: Roman, head colourist at KULTURA in Buenos Aires, explains the method, the touch-up, timing and price.'},
 'russian': {'es': 'Manicura rusa en Buenos Aires: cómo se trabaja con torno, por qué el color queda pegado a la cutícula y cómo hacer que dure. En KULTURA, Microcentro.',
             'ru': 'Русский маникюр в Буэнос-Айресе: как устроена аппаратная техника, почему покрытие ложится у самой кутикулы и как продлить носку. Студия KULTURA.',
             'en': 'Russian manicure in Buenos Aires: how the e-file technique works, why colour sits right up to the cuticle and how to make it last. KULTURA, Microcentro.'},
 'cuatro-manos': {'es': 'Manicura rusa y pedicura SMART al mismo tiempo con dos maestras, en unas dos horas y media: qué incluye, para quién es, precio y cómo reservar en KULTURA.',
                  'ru': 'Русский маникюр и SMART-педикюр одновременно у двух мастеров, примерно за два с половиной часа: что входит, кому подойдёт, цена и как записаться.',
                  'en': 'Russian manicure and SMART pedicure at the same time with two artists, in about two and a half hours: what’s included, who it’s for, price and booking.'},
 'grey': {'es': 'Camuflaje de canas en Buenos Aires: cómo integrar las canas sin una línea marcada de crecimiento, qué tonos se usan y cuánto cuesta en KULTURA, Microcentro.',
          'ru': 'Камуфлирование седины в Буэнос-Айресе: как объединить седину с цветом без резкой границы отрастания, какие оттенки подходят и сколько это стоит.',
          'en': 'Grey blending in Buenos Aires: how to blend grey without a hard regrowth line, which shades are used and what it costs at KULTURA, Microcentro.'},
 'french': {'es': 'Manicura francesa: variantes del clásico, cómo la forma de la uña cambia el resultado y cuánto dura. Con manicura rusa en KULTURA, Microcentro, Buenos Aires.',
            'ru': 'Френч: варианты классики, как форма ногтя меняет результат и сколько держится покрытие. Русский маникюр в студии KULTURA, Микроцентро, Буэнос-Айрес.',
            'en': 'French manicure: variations on the classic, how nail shape changes the result and how long it lasts. Russian manicure at KULTURA, Microcentro, Buenos Aires.'},
 'lashes': {'es': 'Extensión de pestañas en Buenos Aires: efectos muñeca, zorro, ardilla y anime, materiales, cuidados y cómo elegir el tuyo. Con Sofía en KULTURA, Microcentro.',
            'ru': 'Наращивание ресниц в Буэнос-Айресе: кукольный, лисий, беличий и аниме-эффекты, материалы, уход и как выбрать свой. Мастер София, студия KULTURA.',
            'en': 'Lash extensions in Buenos Aires: doll, fox, squirrel and anime effects, materials, aftercare and how to choose yours. With Sofía at KULTURA, Microcentro.'},
 'removal': {'es': 'Remoción de color en Buenos Aires: cómo sacar el color acumulado y volver a un tono natural cuidando la calidad del pelo. Por dónde empezar y qué sigue.',
             'ru': 'Смывка цвета в Буэнос-Айресе: как убрать накопленный цвет и вернуться к натуральному оттенку, сохранив качество волос. С чего начать и что после.',
             'en': 'Colour removal in Buenos Aires: how to lift built-up colour and return to a natural shade while keeping the hair healthy. Where to start and what’s next.'},
 'layers': {'es': 'Corte en capas y coloración con relieve: dos técnicas de Roman, colorista principal de KULTURA en Buenos Aires, que dan volumen y movimiento sin perder largo.',
            'ru': 'Стрижка слоями и рельефное окрашивание: две техники Романа, главного колориста KULTURA в Буэнос-Айресе, которые дают объём и движение без потери длины.',
            'en': 'Layered cuts and relief colouring: two techniques by Roman, head colourist at KULTURA in Buenos Aires, that add volume and movement without losing length.'},
 'care': {'es': 'Cuidado del pelo en casa: cómo elegir los productos según lo que tu pelo necesita y qué hay en los estantes de KULTURA, partner de Schwarzkopf Professional.',
          'ru': 'Домашний уход за волосами: как подобрать средства под задачу и что стоит на полках KULTURA — официального партнёра Schwarzkopf Professional.',
          'en': 'Hair care at home: how to choose products for what your hair needs and what’s on the shelves at KULTURA, an official Schwarzkopf Professional partner.'},
 'nails': {'es': 'Diseño de uñas en Buenos Aires: del nude minimalista al stamping, los sliders y los stickers. Qué se puede hacer y cuánto cuesta en KULTURA, Microcentro.',
           'ru': 'Дизайн ногтей в Буэнос-Айресе: от минималистичного нюда до стемпинга, слайдеров и стикеров. Что можно сделать и сколько это стоит в студии KULTURA.',
           'en': 'Nail art in Buenos Aires: from minimal nude to stamping, decals and stickers. What’s possible and what it costs at KULTURA, Microcentro.'},
}
ALL_ARTS = []   # unified list: dict(id, slug, img, pos, min, svc, k, t, l, by, b, date, title, desc, new)
for a in ARTS:
    ALL_ARTS.append(dict(id=a['id'], slug=ARTICLE_SLUGS[a['id']], img=a['img'], pos=a.get('pos', '50% 50%'), min=a['min'],
                         svc=a.get('svc'), k=a['k'], t=a['t'], l=a['l'], by=a['by'], b=a['b'], date='2026-11-13',
                         title={g: L(a['t'], g) + ' | KULTURA' for g in LANGS}, desc={g: ART_DESC.get(a['id'], {}).get(g) or L(a['l'], g) for g in LANGS}, new=False))
for a in ARTICLES_B2 + ARTICLES_NEW:   # newest batch first in the Journal
    d = dict(a); d['new'] = True
    if d['id'] == 'salon-ruso': d['svc'] = None
    ALL_ARTS.append(d)
ART_BY_ID = {a['id']: a for a in ALL_ARTS}
def art_url(aid, lang): return f"{hub('blog', lang)}{ART_BY_ID[aid]['slug'][lang]}/"

TY_EN = {'sh': 'shampoo', 'co': 'conditioner', 'tr': 'treatment', 'ma': 'mask', 'sp': 'spray', 'se': 'serum'}
def slugify(s):
    s = s.lower().replace('+', ' plus ')
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')
LINE_BY_ID = {l['id']: l for l in LINES}
for p in PRODS:
    ln = LINE_BY_ID[p['line']]['name']
    p['slug'] = slugify(f"{ln} {p['n']} {L(p['ty'], 'en')} {p['vol']}")
def prod_url(pid, lang):
    p = next(q for q in PRODS if q['id'] == pid)
    return f"{hub('prod', lang)}{p['slug']}/"
def prod_name(p, lang):
    return f"{LINE_BY_ID[p['line']]['name']} {p['n']} {L(p['ty'], lang)} {p['vol']}"

def abs_url(path): return DOMAIN + path
def img_abs(src): return DOMAIN + '/' + src.lstrip('/')

# ------------------------------------------------------------------ JSON-LD pieces
SALON_ID = DOMAIN + '/#salon'
def salon_node(lang, full=True):
    n = {
        '@type': ['BeautySalon', 'HairSalon', 'NailSalon'], '@id': SALON_ID,
        'name': 'KULTURA Beauty Studio', 'alternateName': 'KULTURA',
        'url': DOMAIN + '/', 'image': DOMAIN + '/og.jpg', 'logo': DOMAIN + '/apple-touch-icon.png',
        'telephone': '+54 9 11 3762-6937',
        'address': {'@type': 'PostalAddress', 'streetAddress': 'Tte. Gral. Juan Domingo Perón 683', 'postalCode': 'C1038AAM',
                    'addressLocality': 'Buenos Aires', 'addressRegion': 'CABA', 'addressCountry': 'AR'},
        'geo': {'@type': 'GeoCoordinates', 'latitude': -34.6056868, 'longitude': -58.3762758},
        'hasMap': MAPS,
        'openingHoursSpecification': [{'@type': 'OpeningHoursSpecification',
            'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'], 'opens': '10:00', 'closes': '20:00'}],
        'priceRange': '$$$', 'currenciesAccepted': 'ARS',
        'knowsLanguage': ['es', 'ru'],
        'areaServed': {'@type': 'City', 'name': 'Buenos Aires'},
        'sameAs': [IG, FB, TG],
        'description': x('home_desc', lang),
    }
    if full:
        n['potentialAction'] = {'@type': 'ReserveAction', 'target': BOOK, 'name': t('book_online', lang)}
        n['hasOfferCatalog'] = {'@type': 'OfferCatalog', 'name': x('svc_all', lang), 'itemListElement': [
            {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': L(s['name'], lang), 'url': abs_url(svc_url(s['id'], lang))},
             **({'priceSpecification': {'@type': 'PriceSpecification', 'minPrice': R[s['rows'][0]][1], 'priceCurrency': 'ARS'}}
                if s['rows'] and R[s['rows'][0]][1] and not s.get('consult') else {})}
            for s in SVC]}
    return n

def ld(nodes):
    return '<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@graph': nodes}, ensure_ascii=False).replace('</', '<\\/') + '</script>'

def crumbs_node(items):
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': abs_url(u)} for i, (n, u) in enumerate(items)]}

def faq_node(pairs):
    return {'@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in pairs]}

# ------------------------------------------------------------------ chrome
MARK = '<svg width="26" height="26" viewBox="0 0 34 34" aria-hidden="true"><path d="M4 30C10 22 8 12 17 6s14 2 13 -2" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M2 24C9 18 9 9 18 3" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>'

def header(lang, alts):
    langs = ''.join(f'<a href="{e(alts[g])}" hreflang="{g}" lang="{g}"{" aria-current=\"true\"" if g == lang else ""}>{g.upper()}</a>' for g in LANGS)
    return f'''<header class="sp-bar"><div class="g w sp-bar-in">
<a class="mark cap" href="{home_url(lang)}">{MARK}<span>KULTURA</span></a>
<nav class="sp-nav cap" aria-label="{e(t('n_services', lang))}"><a href="{hub('svc', lang)}">{e(t('n_services', lang))}</a><a href="{hub('blog', lang)}">{e(t('n_journal', lang))}</a><a href="{hub('prod', lang)}">{e(t('n_shop', lang))}</a><a href="{home_url(lang)}#prices">{e(t('n_prices', lang))}</a><a href="#visit">{e(t('n_visit', lang))}</a></nav>
<div class="sp-langs cap" role="group" aria-label="Idioma / Язык / Language">{langs}</div>
<a class="btn" href="{BOOK}" target="_blank" rel="noopener">{e(t('book', lang))}</a>
</div></header>'''

def link_index(lang):
    svcs = ''.join(f'<li><a href="{svc_url(s["id"], lang)}">{e(L(s["name"], lang))}</a></li>' for s in SVC)
    arts = ''.join(f'<li><a href="{art_url(a["id"], lang)}">{e(L(a["t"], lang))}</a></li>' for a in ALL_ARTS)
    lines = ''.join(f'<li><a href="{hub("prod", lang)}#{l["id"]}">{e(l["name"])}</a></li>' for l in LINES)
    return f'''<nav class="sp-index g w cap" aria-label="{e(x('idx_svc', lang))}">
<div><a class="sp-ih" href="{hub('svc', lang)}">{e(x('idx_svc', lang))}</a><ul>{svcs}</ul></div>
<div><a class="sp-ih" href="{hub('blog', lang)}">{e(x('idx_blog', lang))}</a><ul>{arts}</ul></div>
<div><a class="sp-ih" href="{hub('prod', lang)}">{e(x('idx_prod', lang))}</a><ul>{lines}</ul></div>
</nav>'''

def footer(lang):
    return f'''<footer id="visit" class="bt sp-foot">
<div class="g w sp-visit">
<p class="d sp-vh">{e(t('v_h', lang))}</p>
<div class="vfoot cap">
<div><span class="mu">{e(t('v_a', lang))}</span><span>Tte. Gral. Juan D. Perón 683<br>Microcentro, Buenos Aires</span><a href="{MAPS}" target="_blank" rel="noopener" class="lnk">{e(t('v_map', lang))}</a></div>
<div><span class="mu">{e(t('v_hl', lang))}</span><span>{e(t('f2v', lang))}</span><span class="mu2">{e(x('langs_spoken', lang))}</span></div>
<div><span class="mu">{e(t('v_b', lang))}</span><a href="{e(wa(t('wa_hi', lang)))}" target="_blank" rel="noopener">WhatsApp +54 9 11 3762-6937</a><a href="{BOOK}" target="_blank" rel="noopener">{e(t('book_online', lang))}</a><a href="{IG}" target="_blank" rel="noopener">Instagram @kultura.ba</a><a href="{FB}" target="_blank" rel="noopener">Facebook</a><a href="{TG}" target="_blank" rel="noopener">Telegram @kulturaba</a></div>
</div>
</div>
{link_index(lang)}
<div class="legal g cap mu"><span>© 2026 KULTURA Beauty Studio</span><span>{e(t('legal', lang))}</span></div>
</footer>'''

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oranienbaum&family=Playfair+Display:ital@1&family=Manrope:wght@400;500;600;700&display=swap">'

def alt_links(alts):
    s = ''.join(f'<link rel="alternate" hreflang="{g}" href="{abs_url(alts[g])}">' for g in LANGS)
    return s + f'<link rel="alternate" hreflang="x-default" href="{abs_url(alts["es"])}">'

def page(lang, path, alts, title, desc, body, nodes, og_img=None, og_type='website', crumbs=None):
    ogi = og_img or (DOMAIN + '/og.jpg')
    crumb_html = ''
    if crumbs:
        crumb_html = '<nav class="sp-crumbs cap mu" aria-label="breadcrumb"><ol>' + ''.join(
            (f'<li><a href="{u}">{e(n)}</a></li>' if i < len(crumbs) - 1 else f'<li aria-current="page">{e(n)}</li>') for i, (n, u) in enumerate(crumbs)) + '</ol></nav>'
        nodes = nodes + [crumbs_node(crumbs)]
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{abs_url(path)}">
{alt_links(alts)}
<meta name="theme-color" content="#000000">
<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="KULTURA Beauty Studio">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{abs_url(path)}"><meta property="og:image" content="{e(ogi)}"><meta property="og:locale" content="{OG_LOCALE[lang]}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
{FONTS}
<link rel="stylesheet" href="/assets/site.css"><link rel="stylesheet" href="/assets/pages.css">
{ld(nodes)}
</head>
<body class="sp">
{header(lang, alts)}
<main id="main" class="sp-main">
{crumb_html}
{body}
</main>
{footer(lang)}
</body>
</html>
'''

def write(path, content):
    fp = os.path.join(ROOT, path.lstrip('/'))
    if fp.endswith('/'): fp += 'index.html'
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, 'w', encoding='utf-8') as f: f.write(content)

SITEMAP = []   # (alts dict)

# ------------------------------------------------------------------ blocks -> html
def blocks_html(blocks):
    out, faqs = [], []
    for blk in blocks:
        k, v = blk[0], blk[1]
        if k == 'h': out.append(f'<h2 class="d">{e(v)}</h2>')
        elif k == 'q': out.append(f'<blockquote class="it">{e(v)}</blockquote>')
        elif k == 'ul': out.append('<ul>' + ''.join(f'<li><b>{e(b)}</b>{(" " + e(r)) if r else ""}</li>' for b, r in v) + '</ul>')
        elif k == 'img': out.append(f'<figure class="rd-fig"><img src="/{v[0].lstrip("/")}" alt="{e(v[1])}" loading="lazy"><figcaption class="cap mu">{e(v[1])}</figcaption></figure>')
        elif k == 'imgs': out.append('<div class="rd-pair">' + ''.join(f'<figure class="rd-fig"><div class="ph"><img src="/{s.lstrip("/")}" alt="{e(c)}" loading="lazy"></div><figcaption class="cap mu">{e(c)}</figcaption></figure>' for s, c in v) + '</div>')
        elif k == 'faq': faqs.extend(v)
        else: out.append(f'<p>{e(v)}</p>')
    return ''.join(out), faqs

def faq_html(pairs, lang):
    if not pairs: return ''
    return f'<section class="sp-faq"><h2 class="d">{e(x("faq", lang))}</h2>' + ''.join(
        f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in pairs) + '</section>'

def price_rows(rows, lang, range_=True):
    out = []
    for key in rows:
        r = R[key]; n, p, mx, m = r[0], r[1], r[2], r[3]; note = r[4] if len(r) > 4 else None
        sub = ', '.join([s for s in [dur(m, lang), L(note, lang)] if s])
        price = t('on_req', lang) if not p else (f'{fmt(p, lang)} – {fmt(mx, lang)}' if range_ and mx else f"{t('from', lang)} {fmt(p, lang)}")
        out.append(f'<div class="row"><span>{e(L(n, lang))}{f"<small>{e(sub)}</small>" if sub else ""}</span><span class="p">{e(price)}</span></div>')
    return ''.join(out)

def who_line(w, lang):
    return (t('whos', lang) if w in ('nails', 'browslash') else t('who', lang)) + ' ' + L(WHO[w], lang)

def cta_buttons(s, lang):
    book = f'<a class="btn" href="{BOOK}" target="_blank" rel="noopener">{e(t("sh_book", lang))}</a>'
    w = f'<a class="btn btn-o" href="{e(wa(t("wa_svc", lang) + L(s["name"], lang)))}" target="_blank" rel="noopener">WhatsApp</a>'
    return w + book if s.get('wa') else book + w

# ------------------------------------------------------------------ nail promo (first nail visit −15% + 15% in points, until 15.12.2026)
# Terms come from the studio owner (16.11.2026). The block hides itself after PROMO_UNTIL, so nothing stale stays online.
PROMO_UNTIL = '2026-12-16T00:00:00-03:00'
PROMO_SVC = {'nails': 'mr', 'pedi': None, 'cuatro-manos': 'm4'}   # service id -> price row shown with the discount
PROMO_HIDE = '<script>document.querySelectorAll("[data-until]").forEach(function(n){if(Date.now()>Date.parse(n.dataset.until))n.remove()})</script>'

def promo_card(s, lang):
    if s['id'] not in PROMO_SVC: return ''
    row = PROMO_SVC[s['id']]
    line = ''
    if row:
        full = R[row][1]; off = round(full * 0.85)
        line = f'<p class="cap pl"><span>{e(L(R[row][0], lang))}</span><span class="pr"><b>{e(fmt(off, lang))}</b><s>{e(fmt(full, lang))}</s></span></p>'
    msg = t('wa_promo', lang) + ': ' + L(s['name'], lang)
    return f'''<div class="sp-promo on-paper" data-until="{PROMO_UNTIL}">
<p class="cap k">{e(t('pr_k', lang))}</p>
<p class="d h">{e(t('pr_h', lang))}</p>
<p class="p">{e(t('pr_p', lang))}</p>
{line}
<div class="acts"><a class="btn" href="{e(wa(msg))}" target="_blank" rel="noopener">{e(t('pr_btn', lang))}</a></div>
</div>{PROMO_HIDE}'''

# ------------------------------------------------------------------ service pages
def build_services():
    for s in SVC:
        sid = s['id']; seo = SERVICES[sid]
        alts = {g: svc_url(sid, g) for g in LANGS}
        SITEMAP.append(alts)
        for lang in LANGS:
            nm = L(s['name'], lang)
            faqs = [(L(q, lang), L(a, lang)) for q, a in seo['faq']]
            rows = s['rows']
            rows_html = price_rows(rows, lang) if rows else ''
            if s.get('consult'):
                rows_html = f'<div class="row"><span>{e(nm)}</span><span class="p">{e(t("on_req", lang))}</span></div>' + rows_html
            rel = [a for a in ALL_ARTS if a.get('svc') == sid]
            rel_html = ''.join(f'<a class="sp-rel" href="{art_url(a["id"], lang)}"><span class="cap mu">{e(x("read_more", lang))}</span><span class="d">{e(L(a["t"], lang))}</span></a>' for a in rel)
            others = ''.join(f'<li><a href="{svc_url(o["id"], lang)}">{e(L(o["name"], lang))}</a></li>' for o in SVC if o['id'] != sid)
            body = f'''<article class="sp-svc g w">
<div class="sp-svc-ph"><div class="ph"><img src="/{s['img']}" alt="{e(nm)}" style="object-position:{s.get('pos', '50% 50%')}"></div></div>
<div class="sp-svc-t">
<p class="cap mu">{e(t('g_hair', lang) if s['g'] == 'hair' else t('g_hands', lang))}</p>
<h1 class="d">{e(seo['h1'][lang])}</h1>
<p class="lead it">{e(L(s['lead'], lang))}</p>{promo_card(s, lang)}
<div class="sp-txt">{''.join(f'<p>{e(p)}</p>' for p in L(s['body'], lang))}</div>
<div class="sp-card on-paper"><h2 class="cap">{e(x('prices', lang))}</h2><p class="cap who-l">{e(who_line(s['who'], lang))}</p><div class="rows">{rows_html}</div>
<div class="acts">{cta_buttons(s, lang)}</div></div>
{faq_html(faqs, lang)}
{rel_html}
<div class="sp-others"><h2 class="cap mu">{e(x('more_svc', lang))}</h2><ul class="cap">{others}</ul></div>
</div>
</article>'''
            svc_node = {'@type': 'Service', 'name': nm, 'serviceType': nm, 'url': abs_url(alts[lang]), 'description': seo['desc'][lang],
                        'image': img_abs(s['img']), 'provider': {'@id': SALON_ID}, 'areaServed': {'@type': 'City', 'name': 'Buenos Aires'},
                        'availableLanguage': ['es', 'ru']}
            prices = [R[k][1] for k in rows if R[k][1] and k != 'ts'] + [R[k][2] for k in rows if R[k][2] and k != 'ts']
            if prices and not s.get('consult'):
                svc_node['offers'] = {'@type': 'AggregateOffer', 'priceCurrency': 'ARS', 'lowPrice': min(p for p in prices), 'highPrice': max(prices), 'url': BOOK}
            nodes = [salon_node(lang, full=False), svc_node, faq_node(faqs)]
            crumbs = [(x('home', lang), home_url(lang)), (t('n_services', lang), hub('svc', lang)), (nm, alts[lang])]
            write(alts[lang], page(lang, alts[lang], alts, seo['title'][lang], seo['desc'][lang], body, nodes, img_abs(s['img']), 'website', crumbs))

def build_svc_hub():
    alts = {g: hub('svc', g) for g in LANGS}
    SITEMAP.append(alts)
    for lang in LANGS:
        groups = []
        for g in ('hair', 'hands'):
            items = []
            for s in [s for s in SVC if s['g'] == g]:
                p = t('on_req', lang) if (not s['rows'] or s.get('consult') or not R[s['rows'][0]][1]) else f"{t('from', lang)} {fmt(R[s['rows'][0]][1], lang)}"
                items.append(f'<li><a href="{svc_url(s["id"], lang)}"><span class="d">{e(L(s["name"], lang))}</span><small class="cap mu">{e(p)}</small></a></li>')
            groups.append(f'<h2 class="cap mu">{e(t("g_" + g, lang))}</h2><ul class="sp-list">{"".join(items)}</ul>')
        body = f'''<section class="sp-hub g w"><h1 class="d">{e(x('svc_all', lang))}</h1><p class="lead it">{e(x('svc_all_lead', lang))}</p>{''.join(groups)}
<div class="acts"><a class="btn" href="{BOOK}" target="_blank" rel="noopener">{e(t('sh_book', lang))}</a><a class="btn btn-o" href="{e(wa(t('wa_hi', lang)))}" target="_blank" rel="noopener">WhatsApp</a></div></section>'''
        nodes = [salon_node(lang, full=True), {'@type': 'CollectionPage', 'name': x('svc_all', lang), 'url': abs_url(alts[lang]),
                 'mainEntity': {'@type': 'ItemList', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'url': abs_url(svc_url(s['id'], lang)), 'name': L(s['name'], lang)} for i, s in enumerate(SVC)]}}]
        title = {'es': 'Servicios y precios · Peluquería y uñas en Microcentro | KULTURA', 'ru': 'Услуги и цены салона красоты в Буэнос-Айресе | KULTURA', 'en': 'Services and prices · Hair and nails in Buenos Aires | KULTURA'}[lang]
        write(alts[lang], page(lang, alts[lang], alts, title, x('svc_all_lead', lang)[:158], body, nodes, None, 'website',
                               [(x('home', lang), home_url(lang)), (t('n_services', lang), alts[lang])]))

# ------------------------------------------------------------------ articles
def build_articles():
    for i, a in enumerate(ALL_ARTS):
        alts = {g: art_url(a['id'], g) for g in LANGS}
        SITEMAP.append(alts)
        nx = ALL_ARTS[(i + 1) % len(ALL_ARTS)]
        for lang in LANGS:
            blocks = L(a['b'], lang)
            bhtml, faqs = blocks_html(blocks)
            svc = next((s for s in SVC if s['id'] == a.get('svc')), None)
            cta2 = (f'<a class="btn btn-o" href="{svc_url(svc["id"], lang)}">{e(L(svc["name"], lang))}: {e(t("wk_more", lang).lower())}</a>' if svc
                    else f'<a class="btn btn-o" href="{hub("svc", lang)}">{e(x("svc_all", lang))}</a>')
            body = f'''<article class="sp-art g">
<header class="rd-head"><span class="meta cap mu"><span>{e(L(a['k'], lang))}</span><span>{a['min']} {e(t('read', lang))}</span><span>{e(L(a['by'], lang))}</span></span>
<h1 class="d">{e(L(a['t'], lang))}</h1><p class="lead it">{e(L(a['l'], lang))}</p></header>
<div class="rd-img"><div class="ph"><img src="/{a['img']}" alt="{e(L(a['t'], lang))}" style="object-position:{a.get('pos', '50% 50%')}"></div></div>
<div class="rd-body">{bhtml}{faq_html(faqs, lang)}</div>
{promo_card(svc, lang) if svc else ''}<div class="rd-cta"><p class="d">{e(t('rd_cta', lang))}</p><div style="display:flex;flex-wrap:wrap;gap:10px"><a class="btn" href="{BOOK}" target="_blank" rel="noopener">{e(t('sh_book', lang))}</a>{cta2}</div></div>
<div class="rd-next"><a href="{art_url(nx['id'], lang)}"><span class="cap mu">{e(t('rd_next', lang))}</span><span class="d">{e(L(nx['t'], lang))}</span></a></div>
</article>'''
            author = ({'@type': 'Person', 'name': 'Roman', 'jobTitle': L(a['by'], lang)} if 'Roman' in L(a['by'], 'en')
                      else {'@type': 'Organization', 'name': 'KULTURA Beauty Studio', '@id': SALON_ID})
            art_node = {'@type': 'BlogPosting', 'headline': L(a['t'], lang), 'description': a['desc'][lang], 'image': img_abs(a['img']),
                        'datePublished': a['date'], 'dateModified': max(a['date'], LASTMOD.get(alts['es'], TODAY)), 'inLanguage': lang, 'url': abs_url(alts[lang]),
                        'mainEntityOfPage': abs_url(alts[lang]), 'author': author,
                        'publisher': {'@type': 'Organization', 'name': 'KULTURA Beauty Studio', 'logo': {'@type': 'ImageObject', 'url': DOMAIN + '/apple-touch-icon.png'}}}
            if svc: art_node['about'] = {'@type': 'Service', 'name': L(svc['name'], lang), 'url': abs_url(svc_url(svc['id'], lang))}
            nodes = [salon_node(lang, full=False), art_node] + ([faq_node(faqs)] if faqs else [])
            crumbs = [(x('home', lang), home_url(lang)), (t('n_journal', lang), hub('blog', lang)), (L(a['t'], lang), alts[lang])]
            write(alts[lang], page(lang, alts[lang], alts, a['title'][lang], a['desc'][lang], body, nodes, img_abs(a['img']), 'article', crumbs))

def build_blog_hub():
    alts = {g: hub('blog', g) for g in LANGS}
    SITEMAP.append(alts)
    order = [a for a in ALL_ARTS if a['new']] + [a for a in ALL_ARTS if not a['new']]
    for lang in LANGS:
        items = ''.join(f'''<a class="jitem" href="{art_url(a['id'], lang)}"><div class="ph"><img src="/{a['img']}" alt="" loading="lazy" style="object-position:{a.get('pos', '50% 50%')}"></div>
<span><span class="meta cap mu"><span>{e(L(a['k'], lang))}</span><span>{a['min']} {e(t('read', lang))}</span></span><h2 class="d">{e(L(a['t'], lang))}</h2><span class="mu2" style="font-size:14px">{e(L(a['l'], lang))}</span></span></a>''' for a in order)
        body = f'<section class="sp-hub g w"><h1 class="d big">Journal</h1><p class="lead it">{e(x("blog_lead", lang))}</p><div class="jlist sp-jlist">{items}</div></section>'
        nodes = [salon_node(lang, full=False), {'@type': 'Blog', 'name': 'KULTURA Journal', 'url': abs_url(alts[lang]), 'inLanguage': lang,
                 'blogPost': [{'@type': 'BlogPosting', 'headline': L(a['t'], lang), 'url': abs_url(art_url(a['id'], lang))} for a in order]}]
        title = {'es': 'Journal · Color, uñas, pestañas y cejas | KULTURA', 'ru': 'Журнал KULTURA · Окрашивание, ногти, ресницы, брови', 'en': 'Journal · Colour, nails, lashes and brows | KULTURA'}[lang]
        write(alts[lang], page(lang, alts[lang], alts, title, x('blog_desc', lang), body, nodes, None, 'website',
                               [(x('home', lang), home_url(lang)), (t('n_journal', lang), alts[lang])]))

# ------------------------------------------------------------------ products
def build_products():
    for p in PRODS:
        alts = {g: prod_url(p['id'], g) for g in LANGS}
        SITEMAP.append(alts)
        line = LINE_BY_ID[p['line']]
        same = [q for q in PRODS if q['line'] == p['line'] and q['id'] != p['id']]
        if p.get('sl'): same = [q for q in same if q.get('sl') == p['sl']] + [q for q in same if q.get('sl') != p['sl']]
        for lang in LANGS:
            nm = prod_name(p, lang)
            ph = (f'<div class="ph noimg"><span class="d">{e(p["n"])}</span><span class="cap">{e(line["name"])}</span></div>' if p.get('noimg')
                  else f'<div class="ph"><img src="/{p["img"]}" alt="{e(p["n"] + " " + L(p["ty"], lang))}"></div>')
            lis = ''.join(f'<li>{e(b)}</li>' for b in L(p['b'], lang))
            sl = ''.join(f'<li><a href="{prod_url(q["id"], lang)}">{e(q["n"] + " · " + L(q["ty"], lang) + " " + q["vol"])}</a></li>' for q in same[:6])
            body = f'''<article class="sp-prod g w">
<div class="sp-svc-ph">{ph}</div>
<div class="sp-svc-t">
<p class="cap mu"><a href="{hub('prod', lang)}#{line['id']}">{e(line['name'])}</a> · {e(L(p['ty'], lang))} · {e(p['vol'])}</p>
<h1 class="d">{e(line['name'] + ' ' + p['n'])}</h1>
<p class="lead it">{e(L(p['s'], lang))}</p>
<p class="sp-price d">{e(fmt(p['price'], lang))}</p>
<div class="acts"><a class="btn" href="{e(wa(t('wa_buy', lang) + nm))}" target="_blank" rel="noopener">{e(x('buy', lang))}</a></div>
<div class="rd-body sp-pbody"><h2 class="d">{e(x('for', lang))}</h2><p>{e(L(p['f'], lang))}</p><h2 class="d">{e(x('does', lang))}</h2><ul>{lis}</ul><h2 class="d">{e(x('use', lang))}</h2><p>{e(L(p['u'], lang))}</p></div>
<p class="cap mu">{e(x('src', lang))}</p>
{f'<div class="sp-others"><h2 class="cap mu">{e(x("same_line", lang))}</h2><ul class="cap">{sl}</ul></div>' if sl else ''}
</div>
</article>'''
            pnode = {'@type': 'Product', 'name': nm, 'description': L(p['s'], lang), 'brand': {'@type': 'Brand', 'name': 'Schwarzkopf Professional'},
                     'category': L(p['ty'], lang), 'url': abs_url(alts[lang]),
                     'offers': {'@type': 'Offer', 'price': p['price'], 'priceCurrency': 'ARS', 'availability': 'https://schema.org/InStoreOnly',
                                'url': abs_url(alts[lang]), 'seller': {'@id': SALON_ID}}}
            if not p.get('noimg'): pnode['image'] = img_abs(p['img'])
            title = f"{line['name']} {p['n']} {L(p['ty'], lang)} {p['vol']} · {'Precio' if lang == 'es' else 'Цена' if lang == 'ru' else 'Price'} | KULTURA"
            if len(title) > 62: title = f"{line['name']} {p['n']} {L(p['ty'], lang)} {p['vol']} | KULTURA"
            desc = f"{L(p['s'], lang)} {fmt(p['price'], lang)}."
            tail = {'es': ' Schwarzkopf Professional en KULTURA, Microcentro, Buenos Aires.', 'ru': ' Schwarzkopf Professional в студии KULTURA, Буэнос-Айрес.', 'en': ' Schwarzkopf Professional at KULTURA, Microcentro, Buenos Aires.'}[lang]
            if len(desc) + len(tail) <= 160: desc += tail
            crumbs = [(x('home', lang), home_url(lang)), (t('n_shop', lang), hub('prod', lang)), (line['name'] + ' ' + p['n'], alts[lang])]
            write(alts[lang], page(lang, alts[lang], alts, title, desc[:160], body, [salon_node(lang, full=False), pnode],
                                   None if p.get('noimg') else img_abs(p['img']), 'product', crumbs))

def build_prod_hub():
    alts = {g: hub('prod', g) for g in LANGS}
    SITEMAP.append(alts)
    for lang in LANGS:
        secs = []
        for l in LINES:
            items = ''.join(f'''<li><a href="{prod_url(p['id'], lang)}"><span class="d">{e(p['n'])}</span><small class="cap mu">{e(L(p['ty'], lang))} · {e(p['vol'])} · {e(fmt(p['price'], lang))}</small></a></li>''' for p in PRODS if p['line'] == l['id'])
            if items: secs.append(f'<h2 class="d" id="{l["id"]}">{e(l["name"])}</h2><p class="mu2">{e(L(l["lead"], lang))}</p><ul class="sp-list">{items}</ul>')
        body = f'<section class="sp-hub g w"><h1 class="d big">{e(t("n_shop", lang))}</h1><p class="lead it">{e(x("prod_lead", lang))}</p>{"".join(secs)}</section>'
        title = {'es': 'Productos Schwarzkopf Professional en Buenos Aires | KULTURA', 'ru': 'Продукция Schwarzkopf Professional в Буэнос-Айресе | KULTURA', 'en': 'Schwarzkopf Professional products in Buenos Aires | KULTURA'}[lang]
        nodes = [salon_node(lang, full=False), {'@type': 'CollectionPage', 'name': t('n_shop', lang), 'url': abs_url(alts[lang])}]
        write(alts[lang], page(lang, alts[lang], alts, title, x('prod_lead', lang)[:158], body, nodes, None, 'website',
                               [(x('home', lang), home_url(lang)), (t('n_shop', lang), alts[lang])]))

# ------------------------------------------------------------------ homes (from the app)
REDIRECT = '<script>(function(){if(location.pathname!=="/")return;var s=null;try{s=localStorage.getItem("kultura_lang")}catch(e){}if(!s){try{if(!/bot|crawl|spider|slurp|lighthouse|headless|preview/i.test(navigator.userAgent)){var l=(navigator.languages&&navigator.languages.length?navigator.languages:[navigator.language||""]).map(function(x){return String(x).toLowerCase().slice(0,2)});var r=l.indexOf("ru"),es=l.indexOf("es");if(r>-1&&(es<0||r<es))s="ru";else if(l[0]==="en"&&es<0)s="en"}}catch(e){}}if(s==="ru"||s==="en")location.replace("/"+s+"/"+location.hash)})();</script>'
OLD_LANG_LINE = "let lang = LANGS.includes(store.get('kultura_lang')) ? store.get('kultura_lang') : 'es';"
OLD_SWITCH = "if (lb){ lang = lb.dataset.lang; store.set('kultura_lang', lang); renderAll(); if (!$('#sheet').hidden) { const h = location.hash.slice(3); if (h) openSvc(h); } if (!$('#reader').hidden) { const h = location.hash.slice(3); if (h && location.hash.startsWith('#a-')) openArt(h); if (h && location.hash.startsWith('#p-')) openProd(h); } return; }"
NEW_SWITCH = "if (lb){ store.set('kultura_lang', lb.dataset.lang); if (lb.dataset.lang !== lang) location.href = ({es:'/',ru:'/ru/',en:'/en/'})[lb.dataset.lang] + location.hash; return; }"
OLD_REL = "${a ? `<button class=\"rel\""

def build_homes():
    alts = {g: home_url(g) for g in LANGS}
    SITEMAP.insert(0, alts)
    pages_js = {
        'svc': {g: {s['id']: svc_url(s['id'], g) for s in SVC} for g in LANGS},
        'art': {g: {a['id']: art_url(a['id'], g) for a in ALL_ARTS} for g in LANGS},
        't': {'svc_page': X['svc_page']},
    }
    for lang in LANGS:
        h = APP
        # assets: absolute paths so /ru/ and /en/ work
        for d in ('img3/', 'img4/', 'img/', 'media/'):
            h = h.replace(f'"{d}', f'"/{d}').replace(f"'{d}", f"'/{d}")
        h = h.replace('<html lang="es">', f'<html lang="{lang}" data-page-lang="{lang}">', 1)
        # head
        def sub(pat, rep, flags=0):
            nonlocal h
            h = re.sub(pat, lambda m: rep, h, count=1, flags=flags)
        sub(r'<title>.*?</title>', f'<title>{e(x("home_title", lang))}</title>', re.S)
        sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(x("home_desc", lang))}">')
        sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{abs_url(alts[lang])}">' + alt_links(alts))
        sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{e(x("home_title", lang))}">')
        sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{e(x("home_desc", lang))}">')
        sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{abs_url(alts[lang])}">')
        sub(r'<meta property="og:locale" content="[^"]*">(<meta property="og:locale:alternate" content="[^"]*">)*',
            f'<meta property="og:locale" content="{OG_LOCALE[lang]}">' + ''.join(f'<meta property="og:locale:alternate" content="{OG_LOCALE[g]}">' for g in LANGS if g != lang))
        sub(r'<script type="application/ld\+json">.*?</script>', ld([salon_node(lang, full=True), {'@type': 'WebSite', '@id': DOMAIN + '/#website', 'url': DOMAIN + '/', 'name': 'KULTURA Beauty Studio', 'inLanguage': ['es', 'ru', 'en']}]), re.S)
        h = h.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + GSC_META, 1)
        if lang == 'es':
            h = h.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + REDIRECT, 1)
        # script patches
        assert OLD_LANG_LINE in h and OLD_SWITCH in h and OLD_REL in h, 'app script changed: update build.py patches'
        h = h.replace(OLD_LANG_LINE, "let lang = document.documentElement.dataset.pageLang || 'es';")
        h = h.replace(OLD_SWITCH, NEW_SWITCH)
        h = h.replace(OLD_REL, "${PAGES.svc[lang] && PAGES.svc[lang][s.id] ? `<a class=\"cap lnk\" href=\"${PAGES.svc[lang][s.id]}\">${PAGES.t.svc_page[li()]} →</a>` : ''}" + OLD_REL, 1)
        h = h.replace('const LANGS = [', 'const PAGES = ' + json.dumps(pages_js, ensure_ascii=False) + ';\nconst LANGS = [', 1)
        # visible links to the static pages
        h = h.replace('<p class="svc-hint cap mu" data-t="svc_hint">', f'<p class="cap" style="margin:0 0 14px"><a class="lnk" href="{hub("svc", lang)}">{e(x("svc_hub_link", lang))} →</a></p><p class="svc-hint cap mu" data-t="svc_hint">', 1)
        h = h.replace('<div class="jr" id="jr"></div>', f'<div class="jr" id="jr"></div><p class="cap" style="margin:36px 0 0"><a class="lnk" href="{hub("blog", lang)}">{e(x("blog_hub_link", lang))} →</a></p>', 1)
        h = h.replace('<div class="pgrid" id="shop-grid"></div>', f'<div class="pgrid" id="shop-grid"></div><p class="cap" style="margin:20px 0 0"><a class="lnk" href="{hub("prod", lang)}">{e(x("prod_hub_link", lang))} →</a></p>', 1)
        h = h.replace('<div class="legal g cap mu">', link_index(lang) + '<div class="legal g cap mu">', 1)
        h = h.replace('</style>', PAGES_CSS_HOME + '</style>', 1)
        assert 'id="promoMore" href="#services"' in h, 'promo block changed: update build.py'
        h = h.replace('id="promoMore" href="#services"', f'id="promoMore" href="{svc_url("nails", lang)}"', 1)
        write(alts[lang], h)

PAGES_CSS_HOME = '.sp-index{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px 36px;padding-block:40px;border-top:1px solid var(--line)}.sp-index ul{list-style:none;margin:10px 0 0;padding:0;display:flex;flex-direction:column;gap:6px}.sp-index a{text-decoration:none;color:var(--mute2)}.sp-index a:hover{color:var(--hi)}.sp-index .sp-ih{color:var(--fg)}@media (max-width:760px){.sp-index{grid-template-columns:1fr}}'

# ------------------------------------------------------------------ misc files
def build_misc():
    css = re.search(r'<style>(.*?)</style>', APP, re.S).group(1).replace('url(img', 'url(/img')
    write('/assets/site.css', css)
    shutil.copyfile(os.path.join(HERE, 'pages.css'), os.path.join(ROOT, 'assets', 'pages.css'))
    # sitemap
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for alts in SITEMAP:
        for g in LANGS:
            links = ''.join(f'<xhtml:link rel="alternate" hreflang="{h}" href="{abs_url(alts[h])}"/>' for h in LANGS) + f'<xhtml:link rel="alternate" hreflang="x-default" href="{abs_url(alts["es"])}"/>'
            out.append(f'<url><loc>{abs_url(alts[g])}</loc><lastmod>{LASTMOD.get(alts['es'], TODAY)}</lastmod>{links}</url>')
    out.append('</urlset>')
    write('/sitemap.xml', '\n'.join(out) + '\n')
    # robots
    bots = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'PerplexityBot', 'Perplexity-User', 'ClaudeBot', 'Claude-SearchBot', 'Claude-User', 'Google-Extended', 'Applebot-Extended', 'Bingbot', 'Googlebot']
    rb = ['User-agent: *', 'Allow: /', 'Disallow: /_build/', '']
    for b in bots: rb += [f'User-agent: {b}', 'Allow: /', 'Disallow: /_build/', '']
    rb.append(f'Sitemap: {DOMAIN}/sitemap.xml')
    write('/robots.txt', '\n'.join(rb) + '\n')
    # _headers (Cloudflare Pages)
    write('/_headers', '/_build/*\n  X-Robots-Tag: noindex\n\n/img3/*\n  Access-Control-Allow-Origin: *\n\n/assets/gbp/*\n  Access-Control-Allow-Origin: *\n  X-Robots-Tag: noindex\n')
    # IndexNow key
    write(f'/{INDEXNOW_KEY}.txt', INDEXNOW_KEY)
    # llms.txt
    def svc_line(s, lang):
        p = '' if (not s['rows'] or s.get('consult') or not R[s['rows'][0]][1]) else f" — {t('from', lang)} {fmt(R[s['rows'][0]][1], lang)}"
        return f"- [{L(s['name'], lang)}]({abs_url(svc_url(s['id'], lang))}){p}"
    ll = ['# KULTURA Beauty Studio', '',
          '> Russian beauty salon (salón de belleza ruso) in Microcentro, Buenos Aires, Argentina: hair colour (AirTouch, balayage, total blonde, contouring, toning, grey blending), haircuts, treatments, Russian e-file manicure, Russian SMART pedicure, four-hand manicure and pedicure, lash extensions, brow architecture, brow and lash lamination. Official Schwarzkopf Professional partner.', '',
          '## Key facts', '',
          '- Address: Tte. Gral. Juan D. Perón 683, Microcentro, C1038AAM Buenos Aires, Argentina',
          '- Hours: Monday to Saturday, 10:00–20:00; closed on Sunday',
          '- WhatsApp: +54 9 11 3762-6937',
          f'- Online booking: {BOOK}',
          '- Languages: Spanish and Russian; English with a translator',
          f'- Instagram: {IG}',
          f'- Facebook: {FB}',
          f'- Telegram: {TG}',
          '- Team: Roman (co-founder, head colourist), Valeria and Tatiana (manicure and pedicure), Sofía (lash extensions, 4 years’ experience, trains beginners), Nikolai (brow architecture, brow and lash lamination)',
          '- Prices in Argentine pesos from the studio booking system, November 2026',
          '- Nail offer until 15 December 2026: 15% off the first nail visit (manicure, pedicure, four-hand manicure and pedicure) plus another 15% back in points for the next visit. Booking by WhatsApp.', '',
          '## Servicios (español)', ''] + [svc_line(s, 'es') for s in SVC] + ['', '## Services (English)', ''] + [svc_line(s, 'en') for s in SVC] + \
         ['', '## Услуги (русский)', ''] + [svc_line(s, 'ru') for s in SVC] + ['', '## Journal', ''] + \
         [f"- [{L(a['t'], 'es')}]({abs_url(art_url(a['id'], 'es'))}) · [EN]({abs_url(art_url(a['id'], 'en'))}) · [RU]({abs_url(art_url(a['id'], 'ru'))})" for a in ALL_ARTS] + \
         ['', '## Products', '', f'- [Productos Schwarzkopf Professional]({abs_url(hub("prod", "es"))}) · [EN]({abs_url(hub("prod", "en"))}) · [RU]({abs_url(hub("prod", "ru"))})', '']
    write('/llms.txt', '\n'.join(ll))
    # 404
    nf = ''.join(f'<p lang="{g}"><b>{e(x("nf", g))}</b> · <a href="{home_url(g)}">{e(x("home", g))}</a> · <a href="{hub("svc", g)}">{e(t("n_services", g))}</a> · <a href="{hub("blog", g)}">Journal</a></p>' for g in LANGS)
    write('/404.html', f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>404 · KULTURA Beauty Studio</title><link rel="stylesheet" href="/assets/site.css"><link rel="stylesheet" href="/assets/pages.css"></head><body class="sp"><main class="sp-main g w sp-hub"><h1 class="d big">404</h1>{nf}</main></body></html>')

if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'assets'), exist_ok=True)
    build_homes(); build_services(); build_svc_hub(); build_articles(); build_blog_hub(); build_products(); build_prod_hub(); build_misc()
    n = sum(len(a) for a in SITEMAP)
    print(f'OK: {len(SITEMAP)} page groups, {n} URLs; articles {len(ALL_ARTS)}, services {len(SVC)}, products {len(PRODS)}')
