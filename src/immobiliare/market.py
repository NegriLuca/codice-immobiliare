"""Aggregate the 2025 Rome listing scan and Booking.com nightly prices.

The public dashboard only consumes aggregated statistics and coordinate-level
nightly rates: no listing titles, URLs or personal notes are exported.
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROME_BBOX = (41.70, 41.98, 12.33, 12.65)
PRICE_RE = re.compile(r"([\d\.\,]+)")


def _num(value: object) -> float | None:
    """Parse both ``269.000`` (IT thousands) and ``18.24`` (decimal)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).replace("€", "").replace("m²", "").strip()
    match = PRICE_RE.search(text)
    if not match:
        return None
    raw = match.group(1)
    if "." in raw and "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        whole, _, fraction = raw.partition(",")
        raw = whole + ("." + fraction if len(fraction) in (1, 2) else fraction)
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    elif "." in raw:
        whole, _, fraction = raw.partition(".")
        if len(fraction) <= 2:
            raw = whole + "." + fraction
        else:
            raw = whole + fraction
    try:
        number = float(raw)
    except ValueError:
        return None
    return number if number > 0 else None


def _coord(value: object) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 2) if values else None


def load_zone_stats(listing_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(listing_dir.glob("Lista_Annunci_Immobiliare_2025_*.xlsx")):
        zone = re.sub(r"^Lista_Annunci_Immobiliare_2025_", "", path.stem).replace("_", " ")
        try:
            frame = pd.read_excel(path, sheet_name="Annunci Completo")
        except Exception:
            continue
        if frame.empty:
            continue
        prices = [v for v in (_num(v) for v in frame.get("Prezzo", [])) if v and v >= 20000]
        sizes = [v for v in (_num(v) for v in frame.get("Dimensione", [])) if v and 10 <= v <= 1000]
        listing_m2 = [p / s for p, s in zip(prices, sizes) if p and s and s > 15]
        zone_sale_m2 = [v for v in (_num(v) for v in frame.get("Vendita Euro/m2 Macro Zona", [])) if v and 500 <= v <= 30000]
        zone_rent_m2 = [v for v in (_num(v) for v in frame.get("Affitto Euro/m2 Macro Zona", [])) if v and 5 <= v <= 250]
        price_m2 = _median(zone_sale_m2)
        rent_m2 = _median(zone_rent_m2)
        gross_yield = None
        if price_m2 and rent_m2:
            gross_yield = round(rent_m2 * 12 / price_m2 * 100, 2)
        above_zone = None
        if price_m2 and listing_m2:
            above_zone = round(sum(1 for value in listing_m2 if value > price_m2) / len(listing_m2) * 100, 1)
        rows.append(
            {
                "zone": zone,
                "listings": int(len(frame)),
                "median_price": _median(prices),
                "median_size": _median(sizes),
                "price_m2": price_m2,
                "rent_m2": rent_m2,
                "gross_yield": gross_yield,
                "above_zone_pct": above_zone,
            }
        )
    return sorted(rows, key=lambda row: row["price_m2"] or 0, reverse=True)


def _average_nightly(calendar: object) -> tuple[float | None, int]:
    if not isinstance(calendar, (list, tuple)):
        return None, 0
    values: list[float] = []
    for _, price in calendar:
        number = _num(price)
        if number and 10 <= number <= 3000:
            values.append(number)
    if not values:
        return None, 0
    return round(statistics.mean(values), 2), len(values)


def load_nightly(pickle_path: Path) -> tuple[list[dict[str, Any]], list[int]]:
    with pickle_path.open("rb") as handle:
        raw = pickle.load(handle)
    frame = pd.DataFrame.from_dict(raw).transpose()
    points: list[dict[str, Any]] = []
    prices: list[int] = []
    lat_min, lat_max, lon_min, lon_max = ROME_BBOX
    for _, row in frame.iterrows():
        avg, n_prices = _average_nightly(row.get("calendar"))
        if not avg:
            continue
        lat, lon = _coord(row.get("latitude")), _coord(row.get("longitude"))
        if not lat or not lon or not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
            continue
        score = _num(row.get("score"))
        points.append(
            {
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "night": avg,
                "prices": n_prices,
                "score": round(score, 1) if score else None,
            }
        )
        prices.append(int(avg))
    return points, prices


def _histogram(prices: list[int]) -> list[dict[str, Any]]:
    buckets = [(0, 100), (100, 150), (150, 200), (200, 250), (250, 300), (300, 400), (400, 600), (600, 99999)]
    counts = Counter()
    for price in prices:
        for low, high in buckets:
            if low <= price < high:
                counts[(low, high)] += 1
                break
    labels = {
        (0, 100): "< €100",
        (100, 150): "€100–150",
        (150, 200): "€150–200",
        (200, 250): "€200–250",
        (250, 300): "€250–300",
        (300, 400): "€300–400",
        (400, 600): "€400–600",
        (600, 99999): "€600+",
    }
    return [{"bucket": labels[b], "count": int(counts[b])} for b in buckets]


def build_payload(listing_dir: Path, booking_pickle: Path) -> dict[str, Any]:
    zones = load_zone_stats(listing_dir)
    points, prices = load_nightly(booking_pickle)
    total_listings = sum(zone["listings"] for zone in zones)
    yields = [zone["gross_yield"] for zone in zones if zone["gross_yield"]]
    price_m2_values = [zone["price_m2"] for zone in zones if zone["price_m2"]]
    return {
        "meta": {
            "source": "Immobiliare.it listing scan + Booking.com calendar scrape",
            "snapshot": "May 2025",
            "zones": len(zones),
            "listings": total_listings,
            "median_price_m2": _median(price_m2_values),
            "median_gross_yield": _median(yields),
            "booking_properties": len(points),
            "median_nightly": _median([float(p) for p in prices]),
            "median_availability_days": _median([p["prices"] for p in points]),
        },
        "zones": zones,
        "nightly": {
            "points": points,
            "histogram": _histogram(prices),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listings", type=Path, required=True, help="folder with Lista_Annunci_Immobiliare_2025_*.xlsx")
    parser.add_argument("--booking", type=Path, required=True, help="properties_scraped_*.pkl file")
    parser.add_argument("--out", type=Path, required=True, help="output JSON path")
    args = parser.parse_args()

    payload = build_payload(args.listings, args.booking)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    meta = payload["meta"]
    print(
        f"{meta['listings']} listings · {meta['zones']} zones · "
        f"{meta['booking_properties']} booking properties · "
        f"median yield {meta['median_gross_yield']}%"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
