import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html import escape
from time import time
from typing import Any
from urllib.request import Request, urlopen

FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/xml",
}

_cache: list[dict[str, Any]] | None = None
_cache_time: float = 0
_CACHE_TTL: float = 300  # 5 minutes


def _parse_time(date_str: str, time_str: str) -> datetime | None:
    try:
        dt_str = f"{date_str} {time_str}"
        for fmt in ["%m-%d-%Y %I:%M%p", "%m-%d-%Y %I%p"]:
            try:
                dt = datetime.strptime(dt_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    except Exception:
        pass
    return None


def fetch_calendar_events_forexfactory() -> list[dict[str, Any]]:
    global _cache, _cache_time
    now = time()
    if _cache is not None and (now - _cache_time) < _CACHE_TTL:
        return _cache
    req = Request(FF_CALENDAR_URL, headers=REQUEST_HEADERS)
    with urlopen(req, timeout=15) as r:
        root = ET.fromstring(r.read())
    events: list[dict[str, Any]] = []
    for el in root.findall("event"):
        title = (el.findtext("title") or "").strip()
        if not title:
            continue
        event = {
            "title": title,
            "country": (el.findtext("country") or "ALL").strip().upper(),
            "date": (el.findtext("date") or "").strip(),
            "time": (el.findtext("time") or "").strip(),
            "impact": (el.findtext("impact") or "Low").strip().lower(),
            "forecast": (el.findtext("forecast") or "N/A").strip(),
            "previous": (el.findtext("previous") or "N/A").strip(),
            "actual": (el.findtext("actual") or "N/A").strip(),
        }
        event["datetime"] = _parse_time(event["date"], event["time"])
        events.append(event)
    _cache = events
    _cache_time = now
    return events


def fetch_calendar_events(
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch calendar events from TradingView API for arbitrary date range.
    Falls back to Forex Factory XML parser if date range is empty and request fails.
    """
    if from_dt is None or to_dt is None:
        # Default to this week
        now = datetime.now(timezone.utc)
        start_of_week = now - timedelta(days=now.weekday() + 1 if now.weekday() != 6 else 0)
        from_dt = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        to_dt = from_dt + timedelta(days=7)

    url = "https://economic-calendar.tradingview.com/events"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
    }
    params = {
        "from": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": to_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        events = []
        for t_ev in data.get("result", []):
            date_str = t_ev.get("date")
            if not date_str:
                continue
            try:
                dt = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                continue

            importance = t_ev.get("importance", -1)
            impact = "low"
            if importance == 0:
                impact = "medium"
            elif importance == 1:
                impact = "high"

            events.append({
                "title": t_ev.get("title", ""),
                "country": (t_ev.get("country") or "ALL").strip().upper(),
                "date": dt.strftime("%m-%d-%Y"),
                "time": dt.strftime("%H:%M"),
                "impact": impact,
                "forecast": t_ev.get("forecast") or "N/A",
                "previous": t_ev.get("previous") or "N/A",
                "actual": t_ev.get("actual") or "N/A",
                "datetime": dt,
            })
        events.sort(key=lambda e: e["datetime"] or datetime.max)
        return events
    except Exception as e:
        print(f"[CALENDAR ERROR] TradingView fetch failed: {e}. Falling back to Forex Factory XML feed.")
        try:
            return fetch_calendar_events_forexfactory()
        except Exception as ex:
            print(f"[CALENDAR ERROR] Forex Factory XML fallback failed: {ex}")
            return []


def get_upcoming_high_impact(
    hours_ahead: int = 4,
    target_currencies: set[str] | None = None,
) -> list[dict[str, Any]]:
    if target_currencies is None:
        target_currencies = {"USD"}
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=hours_ahead)
    try:
        events = fetch_calendar_events()
    except Exception:
        return []
    result = []
    for ev in events:
        dt = ev.get("datetime")
        if not dt:
            continue
        if dt < now or dt > cutoff:
            continue
        if ev["country"] not in target_currencies:
            continue
        if ev["impact"] not in {"high", "medium"}:
            continue
        result.append(ev)
    result.sort(key=lambda e: e["datetime"] or datetime.max)
    return result


def format_calendar_alert(events: list[dict[str, Any]]) -> str | None:
    if not events:
        return None
    lines = [
        "<b>ECONOMIC CALENDAR</b>",
        "----------------------------------------",
    ]
    now = datetime.now(timezone.utc)
    for ev in events:
        dt = ev.get("datetime")
        if not dt:
            continue
        mins_until = int((dt - now).total_seconds() / 60)
        if mins_until <= 0:
            time_str = "NOW"
        elif mins_until < 60:
            time_str = f"in {mins_until}m"
        else:
            hours = mins_until // 60
            mins_left = mins_until % 60
            time_str = f"in {hours}h {mins_left}m" if mins_left else f"in {hours}h"
        icon = "HIGH" if ev["impact"] == "high" else "MED"
        title = escape(ev["title"])
        country = ev["country"]
        forecast = escape(ev.get("forecast", "N/A"))
        previous = escape(ev.get("previous", "N/A"))
        lines.append(
            f"{icon} <b>{country}</b> {title}"
            f"\n    <b>Time:</b> {time_str} | <b>Forecast:</b> {forecast} | <b>Previous:</b> {previous}"
        )
    if len(lines) == 2:
        return None
    return "\n".join(lines)
