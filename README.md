# Codice Immobiliare — Rome rental-yield scanner

A web-scraping and geospatial project that compares **Rome sale prices** with **short-let
income** to estimate gross rental yield by neighbourhood.

- **Live case study:** https://negriluca.github.io/projects/codice-immobiliare.html
- **Portfolio:** https://negriluca.github.io/

---

## Results (May 2025 snapshot)

| Metric | Value |
|---|---|
| Sale listings scanned | **430** |
| Zones | **17** |
| Booking.com properties with calendar prices | **1,615** |
| Median nightly rate | **€219** |
| Median gross yield | **4.99%** |

The dashboard ranks zones by gross yield and shows that peripheral areas (Magliana, Portuense,
Marconi, San Paolo) screen higher on gross yield, while central areas trade at a premium that
compresses it.

> Gross yield = `monthly rent per m² × 12 ÷ sale price per m²`. It ignores taxes, fees, vacancy,
> maintenance, utilities and financing. This is a screening tool, not investment advice.

---

## What the pipeline does

1. **Scan sale listings** — an Immobiliare.it crawler runs per zone and captures price, size,
   floor, €/m² and the portal’s rent/sale benchmarks.
2. **Scan the short-let supply** — a Booking.com crawler captures property search results and
   calendar prices for each property.
3. **Join spatially** — GeoPandas polygons and OSMnx road-network distances associate listings
   with the local short-let market.
4. **Rank and publish** — aggregate gross yield, over/under-pricing versus the zone benchmark,
   and export a non-identifying JSON payload for the dashboard.

```
Immobiliare.it ──┐
                 ├──> normalise prices/coords ──> spatial join ──> zone stats ──> JSON ──> dashboard
Booking.com ─────┘
```

---

## Repository layout

```
codice-immobiliare/
├── notebooks/                   # original crawlers + analysis, numbered
│   ├── 01_immobiliare_listing_scraper.ipynb
│   ├── 02_booking_scraper.ipynb
│   ├── 03_spatial_join.ipynb
│   ├── 04_market_analysis.ipynb
│   ├── 05_zone_dictionary.ipynb
│   └── 06_coordinates.ipynb
├── src/immobiliare/
│   ├── booking_scraper.py       # standalone Booking.com scraper
│   ├── market.py                # aggregation → dashboard JSON
│   └── __init__.py
├── tests/
├── requirements.txt
└── pyproject.toml
```

## Rebuild the dashboard data

Raw scraped files are **not committed** (size, personal paths, and portal content). Point the
aggregator at your local copies:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

PYTHONPATH=src python -m immobiliare.market \
  --listings /path/to/listing_xlsx_folder \
  --booking  /path/to/properties_scraped_Roma.pkl \
  --out      /path/to/NegriLuca.github.io/assets/data/rome_rental_market.json
```

Expected inputs:

- a folder containing `Lista_Annunci_Immobiliare_2025_*.xlsx` files, each with an
  `Annunci Completo` sheet;
- a Booking.com pickle produced by the scraper: a dict keyed by listing URL, with `title`,
  `score`, `latitude`, `longitude` and a `calendar` list of `(date, price)` pairs.

The aggregator also handles the messy Italian number formats (`€ 269.000`, `€ 1.234,56`) and
filters coordinates to the Rome bounding box.

## Tests

```bash
pytest
```

The tests cover number parsing, coordinate parsing, nightly averages and histogram buckets.
They do not require the raw scraped data.

## Notebooks

The notebooks are the original exploratory code. They are kept for provenance and are not
maintained as libraries.

- **01** — Immobiliare.it listing crawler (Selenium / undetected-chromedriver).
- **02** — Booking.com search + calendar scraper (flexible dates, filters, lazy loading).
- **03** — joins listings and bookings with polygons and OSMnx distances.
- **04** — exploratory plots (Plotly/Matplotlib) and market analysis.
- **05** — builds the zone dictionary from Immobiliare.it filters.
- **06** — geocodes listings and plots them on a map.

## Data & privacy

Committed: code and notebooks only.

Excluded: raw scraped `.xlsx`/`.pkl`, Chromium/ChromeDriver binaries, downloaded ZIPs, personal
notes (`Da_Chiamare_*`), debug logs, caches and `.ipynb_checkpoints`. Personal Google Drive paths
inside the notebooks were sanitised to `project-data/`. The published dashboard uses aggregated
statistics and anonymous coordinates only — no listing titles, URLs or personal data.

## Tech

Python · Selenium · undetected-chromedriver · BeautifulSoup · pandas · openpyxl · GeoPandas ·
Shapely · OSMnx · Plotly · Leaflet · pytest

## License

MIT — see [`LICENSE`](LICENSE).
