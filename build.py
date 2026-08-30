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
