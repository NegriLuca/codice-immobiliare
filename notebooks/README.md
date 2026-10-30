# Notebooks

Original exploration notebooks, numbered in the order the pipeline runs. They are kept for
provenance and are not maintained as libraries.

| Notebook | Purpose |
|---|---|
| `01_immobiliare_listing_scraper.ipynb` | Scans Immobiliare.it sale listings per zone (price, size, floor, €/m², benchmarks) |
| `02_booking_scraper.ipynb` | Scrapes Booking.com search results and per-property calendar prices for Rome |
| `03_spatial_join.ipynb` | Joins listings and short-let supply with polygons and OSMnx distances |
| `04_market_analysis.ipynb` | Exploratory plots and the yield analysis that feeds the dashboard |
| `05_zone_dictionary.ipynb` | Builds the zone dictionary from Immobiliare.it filters |
| `06_coordinates.ipynb` | Geocodes listings and plots them |

## Running

1. Install `requirements.txt`.
2. Provide a Chrome/Chromedriver environment (the original notebooks used Colab; paths have been
   replaced with `project-data/`).
3. Expect the portals' DOM to have changed — selectors are intentionally left as they were when
   the snapshot was collected.
4. Outputs and execution counts were cleared so the repository contains code only, with no
   scraped page dumps or personal listing data.

## Data

The notebooks reference raw `.xlsx`/`.pkl` files that are **not committed**. See the root
[README](../README.md#rebuild-the-dashboard-data) for the expected input layout and the
`src/immobiliare/market.py` aggregator that turns them into dashboard JSON.
