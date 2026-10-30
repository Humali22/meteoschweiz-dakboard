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
HOURLY = ('rp0003i0', 'fu3010h0', 'fu3010h1', 'dkl010h0')
PARAMS = DAILY + HOURLY
POINT_ID, POINT_TYPE = '601000', '2'
TZ = ZoneInfo('Europe/Zurich')
RADAR = 'https://www.meteoschweiz.admin.ch/service-und-publikationen/applikationen/niederschlag.html'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'KriensFamilyWeather/2.1', 'Accept': '*/*'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def asset_url(item, name):
    for asset in item.get('assets', {}).values():
        url = asset.get('href', '')
        if re.search(r'\.' + re.escape(name) + r'\.csv(?:\?|$)', url, flags=re.I):
            return url
    return None


def latest_item():
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
    return {local_datetime(stamp).date().isoformat(): convert(val) for stamp, val in data.items()}


def symbol_emoji(code):
    if code is None:
        return '🌤️'
    try:
        n = int(code)
    except (ValueError, TypeError):
        return '🌤️'
    return '🌤️' if n < 5 else ('☁️' if n < 10 else '🌧️')


def rain_slots(data, day):
    slots = [None] * 8
    for stamp, raw in data.items():
        at = local_datetime(stamp)
        if at.minute != 0 or at.hour % 3 != 0:
            continue
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


def cardinal_from_degrees(deg):
    """Meteorological degrees identify where the wind comes FROM.

    The white arrow points towards that compass direction (not the direction
    in which the air is travelling).
    """
    if deg is None:
        return None, '·'
    directions = ['N', 'NO', 'O', 'SO', 'S', 'SW', 'W', 'NW']
    arrows = ['↑', '↗', '→', '↘', '↓', '↙', '←', '↖']
    idx = int(((deg % 360) + 22.5) // 45) % 8
    return directions[idx], arrows[idx]


def wind_peak_and_direction(speed_series, direction_series, day):
    """Strongest hourly mean wind, paired with the direction at that hour."""
    entries = [(stamp, convert(value)) for stamp, value in speed_series.items()
               if local_datetime(stamp).date().isoformat() == day]
    entries = [(stamp, speed) for stamp, speed in entries if speed is not None]
    if not entries:
        return None, None
    peak_stamp, peak_speed = max(entries, key=lambda entry: entry[1])
    direction = convert(direction_series.get(peak_stamp))
    return round(peak_speed), direction


def weather_symbol(code):
    """White, minimal line icons (own SVGs, not MeteoSwiss artwork)."""
    try:
        number = int(code)
    except (TypeError, ValueError):
        number = 2
    if number >= 100:
        number -= 100  # MeteoSwiss night-symbol variants
    if number == 1:
        kind, title = 'sun', 'Sonnig'
    elif number in (2, 3, 4, 26):
        kind, title = 'partly', 'Sonne und Wolken'
    elif number in (5, 27, 28, 35):
        kind, title = 'cloud', 'Bewölkt'
    elif number in (8, 11, 16, 19, 22, 30, 34):
        kind, title = 'snow', 'Schnee'
    elif number in (7, 10, 15, 18, 21, 31):
        kind, title = 'sleet', 'Schnee und Regen'
    elif number in (12, 13, 23, 24, 25, 36, 37, 38, 39, 40, 41, 42):
        kind, title = 'storm', 'Gewitter'
    else:
        kind, title = 'rain', 'Regen'
    sun = ('<circle cx="12" cy="12" r="4"/>'
           '<path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/>')
    cloud = '<path d="M7.5 18h11A4.5 4.5 0 0 0 19 9a6.5 6.5 0 0 0-12.1-1.8A5.4 5.4 0 0 0 7.5 18Z"/>'
    shower = '<path d="m8 20-1 2m6-2-1 2m6-2-1 2"/>'
    snowfall = '<path d="M7 21h2m-1-1v2m4-1h2m-1-1v2m5-1h2m-1-1v2"/>'
    bolt = '<path d="m13 18-2 4 4-2-1 3"/>'
    if kind == 'sun':
        shapes = sun
    elif kind == 'cloud':
        shapes = cloud
    elif kind == 'partly':
        shapes = ('<circle cx="8" cy="7" r="3"/>'
                  '<path d="M8 1v2M2 7h2m6.8-4.8L12 1M3.2 3.2 4.7 4.7"/>' + cloud)
    else:
        shapes = cloud + (shower if kind in ('rain', 'sleet') else '')
        if kind in ('snow', 'sleet'):
            shapes += snowfall
        if kind == 'storm':
            shapes += bolt
    return ('<svg viewBox="0 0 24 24" aria-label="' + escape(title) + '" '
            'role="img" xmlns="http://www.w3.org/2000/svg" fill="none" '
            'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
            'stroke-linejoin="round">' + shapes + '</svg>')


def fmt_temp(n):
    return '–' if n is None else f'{n:g}°'


def fmt_num(n):
    return '–' if n is None else f'{n:g}'


def main():
    item = latest_item()
    all_data = {param: load_parameter(item, param) for param in PARAMS}
    daily = {param: by_day(all_data[param]) for param in DAILY}
    today = datetime.now(TZ).date()
    labels = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    daily_symbols = {local_datetime(stamp).date().isoformat(): code for stamp, code in all_data['jp2000d0'].items()}
    days = []
    for offset in range(5):
        cur = today + timedelta(days=offset)
        date = cur.isoformat()
        wind_speed, wind_dir_deg = wind_peak_and_direction(
            all_data['fu3010h0'], all_data['dkl010h0'], date)
        wind_cardinal, wind_arrow = cardinal_from_degrees(wind_dir_deg)
        day = {
            'date': date,
            'label': ['Heute', 'Morgen'][offset] if offset < 2 else labels[cur.weekday()] + cur.strftime(' %d.%m.'),
            'symbol': symbol_emoji(daily_symbols.get(date)),
            'symbol_code': daily_symbols.get(date),
            'min_c': daily['tre200pn'].get(date),
            'max_c': daily['tre200px'].get(date),
            'rain_mm': daily['rka150p0'].get(date),
            'rain_probability_3h': rain_slots(all_data['rp0003i0'], date),
            'wind_max_kmh': wind_speed,
            'gust_max_kmh': wind_day(all_data['fu3010h1'], date),
            'wind_dir_deg': wind_dir_deg,
            'wind_dir_cardinal': wind_cardinal,
            'wind_dir_arrow': wind_arrow,
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
        available_probabilities = [p for p in day['rain_probability_3h'] if p is not None]
        max_probability = (f'Max. {max(available_probabilities):g}%' if available_probabilities else 'Regen k. A.')
        wind_speed = '–' if day['wind_max_kmh'] is None else f"{day['wind_max_kmh']} km/h"
        wind_dir_text = day['wind_dir_cardinal'] or 'unbekannt'
        wind_title = f"Stärkster stündlicher Mittelwind: {wind_speed}; Herkunftsrichtung: {wind_dir_text}"
        if day['gust_max_kmh'] is not None and day['gust_max_kmh'] >= 40:
            wind_title += f"; Böen bis {day['gust_max_kmh']} km/h"
        icon = weather_symbol(day['symbol_code'])
        cards.append(f'''<section class="day"><h2>{escape(day['label'])}</h2><div class="icon">{icon}</div>
            <strong>{fmt_temp(day['min_c'])} / {fmt_temp(day['max_c'])}</strong>
            <div class="wind" title="{escape(wind_title)}"><span class="arrow">{escape(day['wind_dir_arrow'])}</span> {wind_speed}</div>
            <div class="probability">{max_probability}</div>
            <div class="bars" role="img" aria-label="Regenwahrscheinlichkeit in drei-Stunden-Schritten">{''.join(bars)}</div>
            <div class="hours"><span>0</span><span>12</span><span>24 h</span></div>
            <div class="rain" title="Niederschlagsmenge pro Tag">💧 {fmt_num(day['rain_mm'])} mm</div></section>''')
    header_icon = weather_symbol(2)
    radar_icon = weather_symbol(14)
    html = '''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="3600"><title>Wetter Kriens – MeteoSchweiz</title>
<!-- Design: Dunkel & gemuetlich, weisse Wetter-Icons, kompakte Windzeile -->
<style>
*{box-sizing:border-box}
body{font-family:system-ui,Arial,sans-serif;background:#263740;color:#f7f3eb;margin:0;padding:12px}
header{display:flex;justify-content:space-between;gap:8px;align-items:center}
header .heading{display:flex;align-items:center;gap:7px;min-width:0}
header .heading svg{width:22px;height:22px;flex-shrink:0;color:#fff;}
header h1{font-size:18px;margin:0;font-weight:520;color:#fff;white-space:nowrap}
.source{font-size:11px;color:#c0d0d4;white-space:nowrap}
.days{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin-top:10px}
.day{background:#334b59;border:1px solid #536975;border-radius:11px;padding:9px 5px 8px;text-align:center;min-width:0;display:flex;flex-direction:column;align-items:center}
.day:nth-child(2){background:#435048;border-color:#607064}
.day:nth-child(3){background:#554a4b;border-color:#776367}
.day:nth-child(4){background:#374c59;border-color:#567080}
.day:nth-child(5){background:#47534f;border-color:#64756d}
.day h2{margin:0;font-size:13px;font-weight:550;color:#fff}
.icon{height:40px;display:flex;align-items:center;justify-content:center;color:#fff;margin:3px auto 1px}
.icon svg{width:34px;height:34px;display:block;color:#fff}
.day strong{font-size:15px;white-space:nowrap;color:#fff;font-weight:650}
.wind{font-size:10px;color:#fff;white-space:nowrap;margin-top:4px;line-height:1.2;min-height:14px}
.wind .arrow{font-size:13px;line-height:1;vertical-align:-1px;font-weight:700}
.probability{font-size:11px;font-weight:700;color:#a8e1f7;margin-top:5px;white-space:nowrap}
.bars{height:40px;width:calc(100% - 4px);display:flex;align-items:flex-end;gap:2px;border-bottom:1px solid #899fa7;margin:6px 2px 0}
.bar{display:block;background:#7ecae8;flex:1;border-radius:2px 2px 0 0;min-width:0}
.bar.missing{background:#61727a;height:2px}
.hours{width:100%;display:flex;justify-content:space-between;font-size:9px;color:#d0dbdd;padding:2px 2px 0}
.rain{font-size:10px;color:#fff;margin-top:5px;white-space:nowrap}
.radar{display:flex;align-items:center;justify-content:center;gap:8px;background:#415b69;color:#fff;border:1px solid #7095a5;padding:8px;border-radius:9px;margin-top:7px;font-size:13px;text-decoration:none;font-weight:550}
.radar svg{height:20px;width:20px;color:#fff}
.radar:focus,.radar:hover{background:#527487}
footer{font-size:10px;color:#c0d0d4;margin-top:8px}
@media(max-width:600px){body{padding:6px}.days{gap:3px;margin-top:8px}.day{padding:7px 2px 6px}.day h2{font-size:10px}.icon{height:33px}.icon svg{width:29px;height:29px}.day strong{font-size:12px}.wind{font-size:9px}.wind .arrow{font-size:11px}.probability{font-size:9px}.rain{font-size:9px}.bars{gap:1px}.hours{font-size:8px}}
</style></head><body><header><div class="heading">''' + header_icon + '''<h1>Wetter Kriens</h1></div><div class="source">MeteoSchweiz</div></header><main class="days">''' + ''.join(cards) + '''</main><a class="radar" target="_blank" rel="noopener" href="''' + RADAR + '''">''' + radar_icon + '''<span>Regenradar öffnen</span></a><footer>Quelle: MeteoSchweiz Open Data · Aktualisiert: ''' + escape(updated.strftime('%d.%m.%Y %H:%M')) + '''</footer></body></html>'''
    Path('index.html').write_text(html, encoding='utf-8')
    print('Generated five-day forecast:', item['id'])


if __name__ == '__main__':
    main()
