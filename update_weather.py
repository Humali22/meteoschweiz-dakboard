"""MeteoSchweiz E4 forecast for Kriens; create static GitHub Pages dashboard."""
import csv
import io
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = 'https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-local-forecasting'
DAILY = ('jp2000d0', 'tre200pn', 'tre200px', 'rka150p0')
HOURLY = ('rp0003i0', 'fu3010h0', 'fu3010h1')
PARAMS = DAILY + HOURLY
POINT_ID, POINT_TYPE = '601000', '2'
TZ = ZoneInfo('Europe/Zurich')
RADAR = 'https://www.meteoschweiz.admin.ch/service-und-publikationen/applikationen/niederschlag.html'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'KriensFamilyWeather/2.0', 'Accept': '*/*'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def asset_url(item, name):
    for asset in item.get('assets', {}).values():
        url = asset.get('href', '')
        if re.search(r'\.' + re.escape(name) + r'\.csv(?:\?|$)', url, flags=re.I):
            return url
    return None


def latest_item():
    # STAC can publish partially updated runs; require every needed parameter.
    data = json.loads(fetch(BASE + '/items?limit=100'))
    candidates = data.get('features', [])
    for item in sorted(candidates, key=lambda x: x['id'], reverse=True):
        if all(asset_url(item, name) for name in PARAMS):
            return item
    raise RuntimeError('Kein kompletter Prognose-Datensatz gefunden')


def load_parameter(item, param):
    url = asset_url(item, param)
    if not url:
        raise RuntimeError('Fehlende Datei: ' + param)
    data = fetch(url).decode('latin-1')
    reader = csv.DictReader(io.StringIO(data), delimiter=';')
    expected = {'point_id', 'point_type_id', 'date', param.lower()}
    headers = {name.strip().lower(): name for name in (reader.fieldnames or [])}
    if not expected.issubset(headers):
        raise RuntimeError('Unerwartete CSV-Spalten in ' + param + ': ' + str(reader.fieldnames))
    result = {}
    for row in reader:
        if row[headers['point_id']].strip() == POINT_ID and row[headers['point_type_id']].strip() == POINT_TYPE:
            stamp = row[headers['date']].strip()
            value = row[headers[param.lower()]].strip()
            if stamp and value and value.lower() not in ('-', 'na', 'nan'):
                result[stamp] = value
    if not result:
        raise RuntimeError('Keine Werte für Kriens in ' + param)
    return result


def convert(value):
    try:
        return round(float(value.replace(',', '.')), 1)
    except (ValueError, AttributeError):
        return None


def local_datetime(timestamp):
    return datetime.strptime(timestamp, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).astimezone(TZ)


def by_day(data):
    # Daily local-calendar parameters have a reference timestamp at the start of their local day.
    return {local_datetime(stamp).date().isoformat(): convert(val) for stamp, val in data.items()}


def symbol_emoji(code):
    if code is None:
        return '🌤️'
    # Deliberately simplified neutral icons, not proprietary MeteoSwiss artwork.
    try:
        n = int(code)
    except (ValueError, TypeError):
        return '🌤️'
    return '🌤️' if n < 5 else ('☁️' if n < 10 else '🌧️')


def rain_slots(data, day):
    """Eight disjoint 3-hour windows, ends at 03,06,...24 local time.

    E4 rp0003i0 gives trailing 3-hour chance at HOURLY timestamps.
    Sampling at local hour divisible by 3 avoids overlapping windows.
    """
    slots = [None] * 8
    for stamp, raw in data.items():
        at = local_datetime(stamp)
        if at.minute != 0 or at.hour % 3 != 0:
            continue
        # 00:00 is the end of 21:00-24:00 on the previous local day.
        span_day = (at - timedelta(seconds=1)).date().isoformat()
        if span_day != day:
            continue
        index = (at.hour // 3 - 1) % 8
        slots[index] = convert(raw)
    return slots


def wind_day(data, day):
    values = [convert(raw) for stamp, raw in data.items() if local_datetime(stamp).date().isoformat() == day]
    available = [value for value in values if value is not None]
    return round(max(available)) if available else None


def fmt_temp(n):
    return '–' if n is None else f'{n:g}°'


def fmt_num(n):
    return '–' if n is None else f'{n:g}'


def main():
    item = latest_item()
    all_data = {param: load_parameter(item, param) for param in PARAMS}
    daily = {param: by_day(all_data[param]) for param in DAILY}
    today = datetime.now(TZ).date()
    days = []
    for offset in range(5):
        date = (today + timedelta(days=offset)).isoformat()
        sym_value = all_data['jp2000d0']
        daily_symbols = {local_datetime(stamp).date().isoformat(): code for stamp, code in sym_value.items()}
        day = {
            'date': date,
            'label': ['Heute', 'Morgen'][offset] if offset < 2 else ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][(today + timedelta(days=offset)).weekday()] + (today + timedelta(days=offset)).strftime(' %d.%m.'),
            'symbol': symbol_emoji(daily_symbols.get(date)),
            'min_c': daily['tre200pn'].get(date),
            'max_c': daily['tre200px'].get(date),
            'rain_mm': daily['rka150p0'].get(date),
            'rain_probability_3h': rain_slots(all_data['rp0003i0'], date),
            'wind_max_kmh': wind_day(all_data['fu3010h0'], date),
            'gust_max_kmh': wind_day(all_data['fu3010h1'], date),
        }
        days.append(day)
    if all(day['min_c'] is None and day['max_c'] is None for day in days):
        raise RuntimeError('Keine Tages-Temperaturen gefunden')
    updated = datetime.now(TZ)
    payload = {'location': 'Kriens', 'source': 'MeteoSchweiz Open Data', 'forecast_item': item['id'],
               'updated': updated.isoformat(), 'days': days}
    Path('weather.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    cards = []
    for day in days:
        bars = []
        for i, probability in enumerate(day['rain_probability_3h']):
            if probability is None:
                bars.append('<span class="bar missing" title="Keine Prognose"></span>')
            else:
                height = max(3, min(100, probability))
                bars.append(f'<span class="bar" style="height:{height}%" title="{i*3:02d}–{(i+1)*3:02d} Uhr: {probability:g}% Regenwahrscheinlichkeit"></span>')
        wind = '–' if day['wind_max_kmh'] is None else str(day['wind_max_kmh'])
        gust = (' · Böen ' + str(day['gust_max_kmh']) + ' km/h') if day['gust_max_kmh'] is not None and day['gust_max_kmh'] >= 40 else ''
        available_probabilities = [p for p in day['rain_probability_3h'] if p is not None]
        max_probability = (f'Max. {max(available_probabilities):g} % Regen' if available_probabilities else 'Regen: k. A.')
        cards.append(f'''<section class="day"><h2>{escape(day['label'])}</h2><div class="icon">{escape(day['symbol'])}</div>
            <strong>{fmt_temp(day['min_c'])} / {fmt_temp(day['max_c'])}</strong>
            <div class="wind">🌬️ Wind {wind} km/h{gust}</div>
            <div class="probability">{max_probability}</div>
            <div class="bars" role="img" aria-label="Regenwahrscheinlichkeit in drei-Stunden-Schritten">{''.join(bars)}</div>
            <div class="hours"><span>0</span><span>12</span><span>24 h</span></div>
            <div class="rain">💧 {fmt_num(day['rain_mm'])} mm / Tag</div></section>''')
    html = '''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="3600"><title>Wetter Kriens – MeteoSchweiz</title>
<style>*{box-sizing:border-box}body{font-family:system-ui,Arial,sans-serif;background:#f5f8fc;color:#243344;margin:0;padding:12px}
header{display:flex;justify-content:space-between;gap:8px;align-items:center}header h1{font-size:18px;margin:0}.source{font-size:11px;color:#60738b}
.days{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin-top:7px}.day{background:#fff;border-radius:11px;padding:8px 5px;text-align:center;min-width:0}
.day h2{margin:0;font-size:13px}.icon{font-size:27px;margin:3px 0}.day strong{font-size:16px;white-space:nowrap}.wind,.rain{font-size:11px;color:#536477;margin-top:4px}.probability{font-size:11px;font-weight:650;color:#236996;margin-top:4px}
.bars{height:40px;display:flex;align-items:flex-end;gap:2px;border-bottom:1px solid #bbc9d7;margin:6px 3px 0}.bar{display:block;background:#418fca;flex:1;border-radius:2px 2px 0 0;min-width:0}.bar.missing{background:#dce3ea;height:2px}
.hours{display:flex;justify-content:space-between;font-size:9px;color:#64748b;padding:2px 2px 0}.legend{font-size:11px;color:#536477;margin:9px 0 0}
.radar{display:block;text-align:center;background:#dce9f7;color:#17406f;padding:7px;border-radius:9px;margin-top:7px;font-size:13px;text-decoration:none;font-weight:600}
footer{font-size:10px;color:#60738b;margin-top:8px}@media(max-width:600px){body{padding:6px}.days{gap:3px}.day{padding:7px 2px}.day h2{font-size:10px}.icon{font-size:24px}.day strong{font-size:12px}.wind,.rain,.probability{font-size:9px}.bars{gap:1px}}
</style></head><body><header><h1>🌤️ Wetter Kriens</h1><div class="source">MeteoSchweiz</div></header><main class="days">''' + ''.join(cards) + '''</main><p class="legend">Blaue Balken: Regenwahrscheinlichkeit (%) für jeweils 3 Stunden · 0–24 Uhr. Höchster Wert pro Tag zusätzlich über den Balken.</p><a class="radar" target="_blank" rel="noopener" href="''' + RADAR + '''">🌧️ Regenradar öffnen</a><footer>Quelle: MeteoSchweiz Open Data · Aktualisiert: ''' + escape(updated.strftime('%d.%m.%Y %H:%M')) + '''</footer></body></html>'''
    Path('index.html').write_text(html, encoding='utf-8')
    print('Generated five-day forecast:', item['id'])


if __name__ == '__main__':
    main()
