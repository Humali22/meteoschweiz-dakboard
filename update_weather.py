"""Build static MeteoSwiss 3-day forecast for Kriens from the official STAC API."""
import csv
import io
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from html import escape

BASE = 'https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-local-forecasting'
PARAMS = ('jp2000d0', 'tre200pn', 'tre200px', 'rka150p0')
POINT_ID = '601000'
POINT_TYPE = '2'
TZ = ZoneInfo('Europe/Zurich')

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent':'KriensFamilyWeather/1.0', 'Accept':'*/*'})
    with urllib.request.urlopen(request, timeout=45) as r:
        return r.read()

def latest_item():
    data = json.loads(fetch(BASE + '/items?limit=30'))
    features = data.get('features', [])
    if not features:
        raise RuntimeError('Keine Prognosedaten gefunden')
    for item in sorted(features, key=lambda x: x['id'], reverse=True):
        if all(any(re.search(r'\.' + re.escape(p) + r'\.csv(?:\?|$)', v.get('href', ''), re.I)
                   for v in item.get('assets', {}).values()) for p in PARAMS):
            return item
    raise RuntimeError('Kein vollstaendiger Prognosedatensatz gefunden')

def find_asset(item, param):
    for key, value in item['assets'].items():
        href = value.get('href', '')
        if re.search(r'\.' + re.escape(param) + r'\.csv(?:\?|$)', href, re.I):
            return href
    raise RuntimeError('No asset for parameter: ' + param)

def forecast_row(url):
    txt = fetch(url).decode('latin-1')
    reader = csv.DictReader(io.StringIO(txt), delimiter=';')
    if not reader.fieldnames:
        raise RuntimeError('Empty CSV')
    fields = {s.strip().lower(): s for s in reader.fieldnames}
    pid = fields.get('point_id')
    ptype = fields.get('point_type_id')
    if not pid or not ptype:
        raise RuntimeError('Unexpected CSV headers: ' + repr(reader.fieldnames[:8]))
    for row in reader:
        if row[pid].strip() == POINT_ID and row[ptype].strip() == POINT_TYPE:
            return row
    raise RuntimeError('Kriens point not found in ' + url)

def daily_map(row):
    dates = {}
    for header, value in row.items():
        if header is None or not re.match(r'^\d{12}$', header.strip()):
            continue
        if value is None or value.strip() in ('', '-', 'NA', 'nan'):
            continue
        # Daily field represents Swiss local calendar day; the column timestamp
        # is UTC as documented. Convert date at the reference instant.
        dt_utc = datetime.strptime(header.strip(), '%Y%m%d%H%M').replace(tzinfo=ZoneInfo('UTC'))
        day = dt_utc.astimezone(TZ).date().isoformat()
        dates[day] = value.strip()
    return dates

def number(value):
    try:
        return round(float(value.replace(',', '.')), 1)
    except (ValueError, AttributeError):
        return None

def symbol_emoji(code):
    try:
        n = int(float(code))
    except (ValueError, TypeError):
        return '🌤️'
    # Generic, non-MeteoSwiss graphics; for codes not mapped show a neutral icon.
    # Avoid incorrectly representing proprietary MeteoSwiss icons.
    return '🌤️' if n < 5 else ('☁️' if n < 10 else '🌧️')

def main():
    item = latest_item()
    values = {p: daily_map(forecast_row(find_asset(item, p))) for p in PARAMS}
    today = datetime.now(TZ).date()
    from datetime import timedelta
    days = []
    for offset in range(3):
        day = (today + timedelta(days=offset)).isoformat()
        sym = values['jp2000d0'].get(day)
        days.append({
            'date':day,
            'label':['Heute','Morgen','Übermorgen'][offset],
            'symbol_code':sym,
            'symbol':symbol_emoji(sym),
            'min_c':number(values['tre200pn'].get(day)),
            'max_c':number(values['tre200px'].get(day)),
            'rain_mm':number(values['rka150p0'].get(day)),
        })
    if all(x['min_c'] is None and x['max_c'] is None for x in days):
        raise RuntimeError('Forecast has no temperatures: inspect timestamp columns')
    output = {'location':'Kriens', 'point_id':POINT_ID,'forecast_item':item['id'], 'updated':datetime.now(TZ).isoformat(), 'days':days}
    Path('weather.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    cards = []
    for d in days:
        def fmt(x):return '–' if x is None else f'{x:g}°'
        rain = '–' if d['rain_mm'] is None else f"{d['rain_mm']:g} mm"
        cards.append(f'<section class="day"><h2>{escape(d["label"])}</h2><div class="weather-icon">{escape(d["symbol"])}</div><strong>{fmt(d["min_c"])} / {fmt(d["max_c"])}</strong><p>💧 {rain}</p></section>')
    html = '''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="3600"><title>Wetter Kriens</title><style>
    *{box-sizing:border-box}body{font-family:system-ui,Arial,sans-serif;margin:0;background:#f5f8fc;color:#243344;padding:14px}.head{display:flex;justify-content:space-between;align-items:center;gap:12px}.head h1{font-size:20px;margin:0}.source{font-size:12px;color:#536477}.days{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin-top:12px}.day{background:white;border-radius:12px;text-align:center;padding:12px 4px}.day h2{font-size:15px;margin:0}.weather-icon{font-size:40px;margin:8px 0}.day strong{font-size:18px}.day p{font-size:14px;color:#536477;margin:6px 0 0}.radar{display:block;text-decoration:none;text-align:center;padding:10px;border-radius:10px;background:#dce9f7;color:#17406f;margin-top:10px;font-weight:600;font-size:14px}footer{font-size:10px;color:#60738b;margin-top:8px}@media(max-width:480px){body{padding:8px}.day{padding:8px 2px}.day strong{font-size:15px}.weather-icon{font-size:32px}}</style></head><body>
    <div class="head"><h1>🌦️ Wetter Kriens</h1><span class="source">MeteoSchweiz</span></div><main class="days">''' + ''.join(cards) + '''</main><a class="radar" target="_blank" rel="noopener" href="https://www.meteoschweiz.admin.ch/service-und-publikationen/applikationen/niederschlag.html">🌧️ Regenradar öffnen</a><footer>Quelle: MeteoSchweiz Open Data · Stand: ''' + escape(datetime.now(TZ).strftime('%d.%m.%Y %H:%M')) + '''</footer></body></html>'''
    Path('index.html').write_text(html, encoding='utf-8')
    print('Generated 3-day forecast for', item['id'])

if __name__ == '__main__':
    main()
