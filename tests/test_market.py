from immobiliare.market import _average_nightly, _coord, _histogram, _num


def test_number_formats():
    assert _num("269.000") == 269000
    assert _num("18.24") == 18.24
    assert _num("€ 1.234,56") == 1234.56
    assert _num("1,5") == 1.5
    assert _num("€ 219") == 219


def test_number_invalid():
    assert _num(None) is None
    assert _num("n/a") is None
    assert _num("0") is None
    assert _num(-5) is None


def test_coord():
    assert _coord("41,902") == 41.902
    assert _coord("12.4964") == 12.4964
    assert _coord(None) is None


def test_average_nightly():
    calendar = [
        ("2025-05-01", "€ 120"),
        ("2025-05-02", "€ 200"),
        ("2025-05-03", "n/a"),
    ]
    assert _average_nightly(calendar) == (160.0, 2)
    assert _average_nightly(None) == (None, 0)
    assert _average_nightly([]) == (None, 0)


def test_histogram_boundaries():
    hist = {row["bucket"]: row["count"] for row in _histogram([99, 100, 150, 599, 600])}
    assert hist["< €100"] == 1
    assert hist["€100–150"] == 1
    assert hist["€150–200"] == 1
    assert hist["€400–600"] == 1
    assert hist["€600+"] == 1
