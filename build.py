#!/usr/bin/env python3
"""Generate static HTML for Keep the Tank from data/listings.json."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "listings.json"
CSS_HREF = "css/style.css"

DAY_LABELS = [
    ("mon", "Mon"),
    ("tue", "Tue"),
    ("wed", "Wed"),
    ("thu", "Thu"),
    ("fri", "Fri"),
    ("sat", "Sat"),
    ("sun", "Sun"),
]

SERVICE_ORDER = {"fill": 0, "both": 1, "exchange": 2}

SERVICE_LABEL = {
    "fill": "FILL",
    "exchange": "EXCHANGE ONLY",
    "both": "FILL + EXCHANGE",
}


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def show(value) -> str:
    if value is None or value == "":
        return "unknown"
    return str(value)


def sunday_status(listing: dict) -> tuple[str, str]:
    hours = listing.get("hours") or {}
    sun = hours.get("sun")
    if sun is None or sun == "" or str(sun).lower() == "unknown":
        return "unknown", "unknown"
    if str(sun).lower() == "closed":
        return "closed", "closed"
    return "open", sun


def hours_line(listing: dict) -> str:
    hours = listing.get("hours") or {}
    if not any(hours.get(k) for k, _ in DAY_LABELS):
        return "unknown"
    parts = []
    for key, label in DAY_LABELS:
        val = hours.get(key)
        parts.append(f"{label} {show(val)}")
    return "; ".join(parts)


def tel_href(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return f"tel:+1{digits}"
    if digits:
        return f"tel:{digits}"
    return None


def badge(service_type: str) -> str:
    label = SERVICE_LABEL.get(service_type, service_type.upper())
    cls = escape(service_type)
    return f'<span class="badge {cls}">{escape(label)}</span>'


def listing_html(listing: dict, *, call_first: bool = False, html_id: str | None = None) -> str:
    st = listing.get("service_type") or "fill"
    sun_cls, sun_text = sunday_status(listing)
    phone = listing.get("phone")
    tel = tel_href(phone)
    if tel:
        phone_html = f'<a href="{escape(tel, quote=True)}">{escape(phone)}</a>'
    else:
        phone_html = "unknown"

    addr = ", ".join(
        p
        for p in [
            listing.get("address"),
            listing.get("city"),
            f"{listing.get('state') or ''} {listing.get('zip') or ''}".strip(),
        ]
        if p
    )
    maps_q = quote_plus(addr)
    source = listing.get("source") or ""

    recert = show(listing.get("recertifies"))
    rv = show(listing.get("fills_rv_onboard"))
    call_first_html = (
        '<p class="note call-first">Call first — attendant may leave before close.</p>'
        if call_first
        else ""
    )

    aid = html_id or listing["id"]

    return f"""
<article class="listing service-{escape(st)}" id="{escape(aid)}">
  <div class="listing-head">
    {badge(st)}
    <h2>{escape(listing['name'])}</h2>
  </div>
  <p class="meta">{escape(addr)} · <a href="https://maps.google.com/?q={maps_q}">map</a></p>
  <p class="meta">Phone: {phone_html}</p>
  <p class="meta sunday {escape(sun_cls)}">Sunday: {escape(sun_text)}</p>
  {call_first_html}
  <dl class="facts">
    <dt>Service</dt><dd>{escape(SERVICE_LABEL.get(st, st))}</dd>
    <dt>Tank sizes</dt><dd>{escape(show(listing.get('tank_sizes')))}</dd>
    <dt>RV onboard</dt><dd>{escape(rv)}</dd>
    <dt>RV access</dt><dd>{escape(show(listing.get('rv_access')))}</dd>
    <dt>Recert</dt><dd>{escape(recert)}</dd>
    <dt>Pay at pump</dt><dd>{escape(show(listing.get('pay_at_pump')))}</dd>
    <dt>Hours</dt><dd>{escape(hours_line(listing))}</dd>
    <dt>Fill hours note</dt><dd>{escape(show(listing.get('propane_hours_note')))}</dd>
    <dt>Last verified</dt><dd>{escape(show(listing.get('last_verified')))}</dd>
  </dl>
  <p class="tiny">{escape(show(listing.get('notes')))}</p>
  <p class="tiny">Source: <a href="{escape(source, quote=True)}">{escape(source)}</a></p>
</article>
"""


def page_shell(
    title: str,
    nav: str,
    body: str,
    last_updated: str,
    footer_note: str,
    description: str | None = None,
    *,
    brand: str,
    tagline: str,
) -> str:
    desc = description or (
        f"{brand} — directory of propane cylinder FILL stations. Not exchange cages. "
        "Hours, tank sizes, Sunday service, recert — labeled, dated, local."
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(desc)}">
  <link rel="stylesheet" href="{CSS_HREF}">
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header>
    <a class="brand" href="index.html">{escape(brand)}</a>
    <p class="tag">{escape(tagline)}</p>
    {nav}
  </header>
  <main id="main">
{body}
  </main>
  <footer>
    <p>Last updated {escape(last_updated)}.</p>
    <p><strong>{escape(footer_note)}</strong></p>
    <p>Not affiliated with U-Haul, Tractor Supply, Home Depot, Blue Rhino, AmeriGas, or any propane brand. We do not sell propane, take commissions on gallons, or publish prices as fact. Unknown fields stay unknown.</p>
  </footer>
</body>
</html>
"""


def sunday_href(city: dict) -> str:
    return f"{city['slug']}-sunday.html"


def large_href(city: dict) -> str:
    return f"{city['slug']}-large.html"


def nav_html(current: str, cities: list[dict]) -> str:
    items = ['<a href="index.html"' + (' aria-current="page"' if current == "home" else "") + ">Home</a>"]
    for city in cities:
        href = f"{city['slug']}.html"
        cur = ' aria-current="page"' if current == city["slug"] else ""
        items.append(f'<a href="{escape(href, quote=True)}"{cur}>{escape(city["metro_name"])} fills</a>')
        sun = sunday_href(city)
        sun_cur = ' aria-current="page"' if current == f"{city['slug']}-sunday" else ""
        items.append(f'<a href="{escape(sun, quote=True)}"{sun_cur}>Open Sunday</a>')
        large = large_href(city)
        large_cur = ' aria-current="page"' if current == f"{city['slug']}-large" else ""
        items.append(
            f'<a href="{escape(large, quote=True)}"{large_cur}>100-lb / RV / forklift</a>'
        )
    return "<nav>" + " ".join(items) + "</nav>"


def build_index(data: dict) -> str:
    cities = data["cities"]
    last = data["last_updated"]
    footer = data["site"]["footer_note"]
    city_links = "\n".join(
        (
            f'<li><a class="cta" href="{escape(c["slug"], quote=True)}.html">{escape(c["metro_name"])} fill directory</a></li>\n'
            f'<li><a class="cta" href="{escape(sunday_href(c), quote=True)}">Open Sunday</a></li>\n'
            f'<li><a class="cta" href="{escape(large_href(c), quote=True)}">100-lb, RV, and forklift fills</a></li>'
        )
        for c in cities
    )
    body = f"""
    <h1>Fill the tank you already own.</h1>
    <p class="lede">Google still mixes propane <em>fill</em> stations with locked exchange cages. This directory labels every row. Denver metro, Boulder / Lafayette / Longmont, and Colorado Springs are live.</p>

    <div class="compare">
      <section class="card fill-card">
        <h2>Fill</h2>
        <p>They put propane into <strong>your</strong> cylinder. You keep the tank. You pay for the gallons they add. 30-, 40-, and 100-lb bottles and RV onboard tanks can be filled here — if that shop lists it.</p>
        <p>Look for a bulk tank and an attendant. U-Haul, Tractor Supply, and independent dealers are the usual fill points.</p>
      </section>
      <section class="card ex-card">
        <h2>Exchange</h2>
        <p>A locked cage (often Blue Rhino). You leave a 20-lb grill tank and take a different one. You do not get credit for propane left in your old tank. Exchange tanks are often filled to about 15 lb, not a true 20.</p>
        <p>Cages do not fill 30/40/100-lb bottles, forklifts, or the tank bolted to an RV.</p>
      </section>
    </div>

    <p class="note"><strong>Costco:</strong> many warehouses dropped propane fill in 2024–2026. Do not assume a warehouse still fills. Call first. We are not listing Costco as a fill until a warehouse page says it does.</p>

    <h2>Cities</h2>
    <ul class="city-list">
      {city_links}
    </ul>

    <h2>What we put on each row</h2>
    <ul class="plain">
      <li>Service type: fill, exchange, or both — never unlabeled.</li>
      <li>Sunday hours, tank sizes, RV onboard, recert, phone, last verified — or the word <em>unknown</em>.</li>
      <li>No live prices. No “best of.” No affiliate links.</li>
    </ul>
"""
    brand = data["site"]["name"]
    tagline = data["site"]["tagline"]
    return page_shell(
        f"{brand} — propane fill stations, not cages",
        nav_html("home", cities),
        body,
        last,
        footer,
        brand=brand,
        tagline=tagline,
    )


def sunday_fill_rank(listing: dict) -> int:
    """0 = Sunday hours posted and not closed; 1 = closed or unknown."""
    hours = listing.get("hours") or {}
    sun = hours.get("sun")
    if sun and str(sun).lower() not in ("closed", "unknown"):
        return 0
    return 1


def listing_sort_key(listing: dict):
    st = listing.get("service_type")
    return (
        SERVICE_ORDER.get(st, 9),
        sunday_fill_rank(listing) if st == "fill" else 0,
        listing.get("city") or "",
        listing.get("name") or "",
    )


def build_city(data: dict, city: dict) -> str:
    last = data["last_updated"]
    footer = data["site"]["footer_note"]
    rows = [l for l in data["listings"] if l.get("city_slug") == city["slug"]]
    rows.sort(key=listing_sort_key)

    fills = [l for l in rows if l.get("service_type") == "fill"]
    boths = [l for l in rows if l.get("service_type") == "both"]
    exchanges = [l for l in rows if l.get("service_type") == "exchange"]

    def block(title: str, items: list[dict], extra: str = "") -> str:
        if not items:
            return ""
        inner = "\n".join(listing_html(l) for l in items)
        return f'<h2 class="section-label">{escape(title)}</h2>\n{extra}\n{inner}'

    sun_page = sunday_href(city)
    body = f"""
    <h1>{escape(city["metro_name"])} propane fill stations</h1>
    <p class="lede">{escape(city.get("blurb") or "")}</p>
    <p class="count">{len(rows)} places · {len(fills)} fill · {len(boths)} both · {len(exchanges)} exchange-only. Sorted fill first, then both, then cages. Not ranked.</p>
    <p class="legend">
      {badge("fill")} they fill your tank
      {badge("both")} fill and exchange on the same lot
      {badge("exchange")} cage / swap only
    </p>
    <p class="note">Hours below are <em>store or office hours from the shop’s own page</em>. Propane often stops when the certified attendant leaves. Call before you drive. <a href="{escape(sun_page, quote=True)}"><strong>Open Sunday</strong></a> — fills with posted Sunday hours only. Need a 100-lb bottle, an onboard RV tank, or a forklift cylinder? See <a href="{escape(large_href(city), quote=True)}"><strong>100-lb / RV / forklift</strong></a>.</p>
    <nav class="filters" aria-label="Jump">
      <a href="#fills">Fills</a>
      <a href="#both">Both</a>
      <a href="#exchange">Exchange only</a>
      <a href="{escape(sun_page, quote=True)}">Open Sunday</a>
      <a href="{escape(large_href(city), quote=True)}">100-lb / RV / forklift</a>
    </nav>
    <div id="fills">{block("Fills — they put propane in your cylinder", fills)}</div>
    <div id="both">{block("Both — fill and exchange at the same shop", boths)}</div>
    <div id="exchange">{block("Exchange only — do not come here to fill", exchanges, '<p class="note">This cage is listed so you can see what Google often ranks as “propane.” It will not fill the tank you already own.</p>')}</div>
"""
    brand = data["site"]["name"]
    tagline = data["site"]["tagline"]
    return page_shell(
        f"{city['metro_name']} propane fill stations — {brand}",
        nav_html(city["slug"], data["cities"]),
        body,
        last,
        footer,
        brand=brand,
        tagline=tagline,
    )


def is_fill_capable(listing: dict) -> bool:
    return listing.get("service_type") in ("fill", "both")


def is_sunday_open(listing: dict) -> bool:
    cls, _ = sunday_status(listing)
    return cls == "open"


def city_fill_rows(data: dict, city: dict) -> list[dict]:
    return [
        l
        for l in data["listings"]
        if l.get("city_slug") == city["slug"] and is_fill_capable(l)
    ]


def sunday_open_rows(data: dict, city: dict) -> list[dict]:
    rows = [l for l in city_fill_rows(data, city) if is_sunday_open(l)]
    rows.sort(
        key=lambda l: (
            SERVICE_ORDER.get(l.get("service_type"), 9),
            l.get("city") or "",
            l.get("name") or "",
        )
    )
    return rows


def sunday_excluded_rows(data: dict, city: dict) -> list[dict]:
    rows = [l for l in city_fill_rows(data, city) if not is_sunday_open(l)]
    rows.sort(key=lambda l: (l.get("city") or "", l.get("name") or ""))
    return rows


def build_sunday(data: dict, city: dict) -> str:
    last = data["last_updated"]
    footer = data["site"]["footer_note"]
    rows = sunday_open_rows(data, city)
    fills = [l for l in rows if l.get("service_type") == "fill"]
    boths = [l for l in rows if l.get("service_type") == "both"]
    excluded = sunday_excluded_rows(data, city)
    city_page = f"{city['slug']}.html"

    def block(title: str, items: list[dict]) -> str:
        if not items:
            return ""
        inner = "\n".join(listing_html(l, call_first=True) for l in items)
        return f'<h2 class="section-label">{escape(title)}</h2>\n{inner}'

    excluded_bits = [
        f'<p class="note">Weekday-only fills (closed or unknown Sunday) stay on the '
        f'<a href="{escape(city_page, quote=True)}">full {escape(city["metro_name"])} directory</a>. '
        f'This page does not invent hours. Need a cage? '
        f'<a href="{escape(city_page, quote=True)}#exchange">Exchange-only listings</a>.</p>'
    ]
    if excluded:
        items = []
        for l in excluded:
            _cls, sun_text = sunday_status(l)
            st = l.get("service_type") or "fill"
            items.append(
                f'<li><a href="{escape(city_page, quote=True)}#{escape(l["id"], quote=True)}">'
                f'{escape(l["name"])}</a> — {escape(l.get("city") or "")} · '
                f'{escape(SERVICE_LABEL.get(st, st))} · Sunday {escape(sun_text)}</li>'
            )
        excluded_bits.append('<h2 class="section-label">Closed or unknown Sunday</h2>')
        excluded_bits.append(
            "<p>These fill-capable shops are omitted here because Sunday is closed or unknown.</p>"
        )
        excluded_bits.append("<ul class=\"plain\">\n      " + "\n      ".join(items) + "\n    </ul>")
    excluded_html = "\n    ".join(excluded_bits)

    body = f"""
    <h1>Sunday propane fill — {escape(city["metro_name"])}</h1>
    <p class="lede">Tank died mid-cookout? These {escape(city["metro_name"])} shops have posted Sunday hours and they fill the cylinder you already own. Exchange-only cages are not on this page.</p>
    <p class="count">{len(rows)} shops · {len(fills)} fill · {len(boths)} both. Sunday hours posted and not closed or unknown. Not ranked.</p>
    <p class="legend">
      {badge("fill")} they fill your tank
      {badge("both")} fill and exchange on the same lot
    </p>
    <p class="note">Sunday times below are <em>store or office hours from the shop’s own page</em>. The certified attendant may leave before close. Call first. Need a cage instead? See <a href="{escape(city_page, quote=True)}#exchange">exchange-only listings</a> on the {escape(city["metro_name"])} directory.</p>
    <nav class="filters" aria-label="Jump">
      <a href="#fills">Fills</a>
      <a href="#both">Both</a>
      <a href="{escape(city_page, quote=True)}">{escape(city["metro_name"])} directory</a>
    </nav>
    <div id="fills">{block("Fills open Sunday", fills)}</div>
    <div id="both">{block("Both — fill and exchange, open Sunday", boths)}</div>
    {excluded_html}
"""
    brand = data["site"]["name"]
    tagline = data["site"]["tagline"]
    return page_shell(
        f"Sunday propane fill — {city['metro_name']} — {brand}",
        nav_html(f"{city['slug']}-sunday", data["cities"]),
        body,
        last,
        footer,
        description=(
            f"{brand}: {city['metro_name']} propane fills open Sunday. Fill and fill+exchange only — "
            "not exchange cages. Call first; the attendant may leave before close."
        ),
        brand=brand,
        tagline=tagline,
    )


def mentions_100(listing: dict) -> bool:
    """True if tank_sizes mentions 100 lb / 100-lb / 100lb (en-dash ok)."""
    raw = listing.get("tank_sizes") or ""
    t = raw.lower().replace("–", "-").replace("—", "-")
    if re.search(r"100\s*-?\s*lb", t):
        return True
    if "100lb" in t.replace(" ", ""):
        return True
    return False


def mentions_forklift(listing: dict) -> bool:
    return "forklift" in (listing.get("tank_sizes") or "").lower()


def rv_onboard_yes(listing: dict) -> bool:
    return str(listing.get("fills_rv_onboard") or "").strip().lower() == "yes"


def qualifies_large(listing: dict) -> bool:
    if not is_fill_capable(listing):
        return False
    return mentions_100(listing) or mentions_forklift(listing) or rv_onboard_yes(listing)


def large_omit_why(listing: dict) -> str:
    reasons = []
    sizes = listing.get("tank_sizes") or ""
    unknown_sizes = (not sizes.strip()) or "unknown" in sizes.lower()
    if not mentions_100(listing):
        reasons.append("sizes unknown" if unknown_sizes else "no 100")
    rv = str(listing.get("fills_rv_onboard") or "").strip().lower()
    if rv == "yes":
        pass
    elif rv in ("", "unknown"):
        reasons.append("RV unknown")
    else:
        reasons.append(f"RV {rv}")
    if not mentions_forklift(listing):
        reasons.append("not forklift")
    return " / ".join(reasons) or "did not match 100-lb, RV, or forklift"


def large_sort_key(listing: dict):
    return (
        SERVICE_ORDER.get(listing.get("service_type"), 9),
        listing.get("city") or "",
        listing.get("name") or "",
    )


def large_rows(data: dict, city: dict) -> list[dict]:
    rows = [
        l
        for l in data["listings"]
        if l.get("city_slug") == city["slug"] and qualifies_large(l)
    ]
    rows.sort(key=large_sort_key)
    return rows


def large_omitted_rows(data: dict, city: dict) -> list[dict]:
    rows = [
        l
        for l in city_fill_rows(data, city)
        if not qualifies_large(l)
    ]
    rows.sort(key=lambda l: (l.get("city") or "", l.get("name") or ""))
    return rows


def build_large(data: dict, city: dict) -> str:
    last = data["last_updated"]
    footer = data["site"]["footer_note"]
    rows = large_rows(data, city)
    lb100 = [l for l in rows if mentions_100(l)]
    rv = [l for l in rows if rv_onboard_yes(l)]
    forklift = [l for l in rows if mentions_forklift(l)]
    omitted = large_omitted_rows(data, city)
    city_page = f"{city['slug']}.html"
    sun_page = sunday_href(city)

    def block(title: str, items: list[dict], suffix: str) -> str:
        if not items:
            return ""
        inner = "\n".join(
            listing_html(l, call_first=True, html_id=f"{l['id']}-{suffix}")
            for l in items
        )
        return f'<h2 class="section-label">{escape(title)}</h2>\n{inner}'

    omitted_bits = [
        f'<p class="note">Fill-capable shops that did not match 100-lb, RV onboard = yes, or forklift stay on the '
        f'<a href="{escape(city_page, quote=True)}">full {escape(city["metro_name"])} directory</a>. '
        f'This page does not invent tank sizes. Need a cage? '
        f'<a href="{escape(city_page, quote=True)}#exchange">Exchange-only listings</a>.</p>'
    ]
    if omitted:
        items = []
        for l in omitted:
            st = l.get("service_type") or "fill"
            items.append(
                f'<li><a href="{escape(city_page, quote=True)}#{escape(l["id"], quote=True)}">'
                f'{escape(l["name"])}</a> — {escape(l.get("city") or "")} · '
                f'{escape(SERVICE_LABEL.get(st, st))} · {escape(large_omit_why(l))}</li>'
            )
        omitted_bits.append('<h2 class="section-label">Omitted fill/both shops</h2>')
        omitted_bits.append(
            "<p>These shops fill (or fill and exchange) but did not qualify for 100-lb, RV onboard, or forklift on this page.</p>"
        )
        omitted_bits.append("<ul class=\"plain\">\n      " + "\n      ".join(items) + "\n    </ul>")
    omitted_html = "\n    ".join(omitted_bits)

    body = f"""
    <h1>100-lb, RV, and forklift fills — {escape(city["metro_name"])}</h1>
    <p class="lede">Google still ranks locked 20-lb exchange cages for “propane refill.” This page is the query it fails: who will fill a <strong>100-lb cylinder</strong>, an <strong>onboard RV tank</strong>, or a <strong>forklift</strong> bottle. A shop may appear in more than one section. Exchange cages are not listed here.</p>
    <p class="count">{len(rows)} shops on this page · {len(lb100)} in 100-lb · {len(rv)} RV onboard yes · {len(forklift)} forklift. A shop can count in more than one section. Not ranked.</p>
    <p class="legend">
      {badge("fill")} they fill your tank
      {badge("both")} fill and exchange on the same lot
    </p>
    <p class="note">Call first. Lot access for a big rig is often <em>unknown</em> — only a shop that described drive-in / drive-out is labeled that way. Tractor Supply 100-lb is chain policy; RV onboard at those stores is still unknown, not store-confirmed.</p>
    <nav class="filters" aria-label="Jump">
      <a href="#lb100">100-lb</a>
      <a href="#rv">RV onboard</a>
      <a href="#forklift">Forklift</a>
      <a href="#omitted">Omitted</a>
      <a href="{escape(city_page, quote=True)}">{escape(city["metro_name"])} directory</a>
      <a href="{escape(sun_page, quote=True)}">Open Sunday</a>
    </nav>
    <div id="lb100">{block("100-lb cylinders", lb100, "100lb")}</div>
    <div id="rv">{block("RV onboard tanks", rv, "rv")}</div>
    <div id="forklift">{block("Forklift cylinders", forklift, "forklift")}</div>
    <div id="omitted">{omitted_html}</div>
"""
    brand = data["site"]["name"]
    tagline = data["site"]["tagline"]
    return page_shell(
        f"100-lb, RV, and forklift fills — {city['metro_name']} — {brand}",
        nav_html(f"{city['slug']}-large", data["cities"]),
        body,
        last,
        footer,
        description=(
            f"{brand}: {city['metro_name']} shops that fill 100-lb cylinders, onboard RV tanks, "
            "or forklift bottles. Fill and fill+exchange only — not 20-lb exchange cages. Call first."
        ),
        brand=brand,
        tagline=tagline,
    )


def main() -> None:
    data = load()
    (ROOT / "index.html").write_text(build_index(data), encoding="utf-8")
    print(f"wrote {ROOT / 'index.html'}")
    for city in data["cities"]:
        out = ROOT / f"{city['slug']}.html"
        out.write_text(build_city(data, city), encoding="utf-8")
        print(f"wrote {out}")
        sun_out = ROOT / sunday_href(city)
        sun_out.write_text(build_sunday(data, city), encoding="utf-8")
        open_n = len(sunday_open_rows(data, city))
        excl_n = len(sunday_excluded_rows(data, city))
        print(f"wrote {sun_out} ({open_n} Sunday fills, {excl_n} fill/both excluded closed/unknown)")
        large_out = ROOT / large_href(city)
        large_out.write_text(build_large(data, city), encoding="utf-8")
        large_n = len(large_rows(data, city))
        omit_n = len(large_omitted_rows(data, city))
        lb_n = sum(1 for l in large_rows(data, city) if mentions_100(l))
        rv_n = sum(1 for l in large_rows(data, city) if rv_onboard_yes(l))
        fk_n = sum(1 for l in large_rows(data, city) if mentions_forklift(l))
        print(
            f"wrote {large_out} ({large_n} unique shops; "
            f"{lb_n} 100-lb / {rv_n} RV yes / {fk_n} forklift; {omit_n} fill/both omitted)"
        )
    print(f"{len(data['listings'])} listings, {len(data['cities'])} cities")


if __name__ == "__main__":
    main()
