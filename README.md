# KULTURA Beauty Studio

Sitio web de KULTURA Beauty Studio, Microcentro, Buenos Aires — https://kulturaba.com

## Build

The site is generated. Edit sources in `_build/`, then run from the repo root:

```
python3 _build/build.py      # homes (/, /ru/, /en/) + service, journal and product pages, sitemap, robots, llms.txt
node _build/prerender.js     # prerender the three homes (needs Playwright)
```

- `_build/app.html` — the one-page site and its content data (services, prices, articles, products).
- `_build/content/services_seo.py` — slugs, titles, descriptions and FAQ for service pages.
- `_build/content/articles_new.py` — Journal articles that live only as separate pages.
- `_build/pages.css` — styles for the static pages.

Do not edit the generated `index.html`, `ru/`, `en/`, `servicios/`, `blog/`, `productos/` by hand.
