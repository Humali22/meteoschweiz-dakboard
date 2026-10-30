"""MeteoSchweiz E4 forecast for Kriens; create static GitHub Pages dashboard."""
import csv
import io
import math
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
MEASUREMENTS_URL = 'https://data.geo.admin.ch/ch.meteoschweiz.messwerte-aktuell/VQHA80.csv'
MEASUREMENT_STATION = 'LUZ'  # Luzern; Messstation in der Nähe von Kriens


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
    """Eigene weisse SVG-Liniensymbole nach MeteoSchweiz-Piktogrammcode."""
    try:
        n = int(code)
    except (TypeError, ValueError):
        n = 3
    if n >= 100:
        n -= 100  # Tages- und Nachtvarianten mit gleicher Wetterart
    rain_codes = {6, 9, 14, 17, 20, 29, 32, 33}
    snow_codes = {8, 11, 16, 19, 22, 30, 34}
    sleet_codes = {7, 10, 15, 18, 21, 31}
    thunder_rain_codes = {12, 13, 23, 24, 25, 36, 38, 40, 41}
    thunder_snow_codes = {37, 39, 42}
    if n == 1:
        kind, title = 'sun', 'Sonnig'
    elif n in (2, 3, 4, 26):
        kind, title = 'partly', 'Teilweise sonnig'
    elif n == 5:
        kind, title = 'cloud', 'Bewölkt'
    elif n == 35:
        kind, title = 'overcast', 'Bedeckt'
    elif n in (27, 28):
        kind, title = 'fog', 'Hochnebel oder Nebel'
    elif n in snow_codes:
        kind, title = 'snow', 'Schnee'
    elif n in sleet_codes:
        kind, title = 'sleet', 'Schneeregen'
    elif n in thunder_snow_codes:
        kind, title = 'storm_snow', 'Gewitter mit Schnee'
    elif n in thunder_rain_codes:
        kind, title = 'storm_rain', 'Gewitter mit Regen'
    elif n in rain_codes:
        kind, title = 'rain', 'Regen'
    else:
        kind, title = 'cloud', 'Bewölkt'
    # Einheitliche Wolkenform: links grosser Bogen, rechts kleiner.
    # Alle SVG-Pfade sind eigens gezeichnet, keine externen Grafiken.
    sun = ('<circle cx="12" cy="12" r="4"/>'
           '<path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/>')
    # Offene Unterseite, damit Striche und Schneeflocken von der Wolke wegfallen.
    cloud_open = '<path d="M7.2 17.5C4.4 17.5 2.8 15.7 2.8 13.1c0-2.8 2-4.7 4.7-4.8C8.3 4.3 11.4 2.7 14.2 3.2c3.2.5 5 2.9 5.1 5.9 2.9.1 4.2 2 4.2 4.3 0 2.5-1.7 4.1-4.2 4.1"/>'
    cloud = cloud_open + '<path d="M7.2 17.5h12.1"/>'
    # Bewölkt: zwei überlappende Wolken, kleine versetzt rechts unten.
    second_cloud = '<path d="M15.9 18.7c.8-1.1 2-1.7 3.4-1.7 2.1 0 3.6 1.3 3.8 3.1 1.7.1 2.8 1.4 2.8 3 0 1.7-1.3 2.8-3.1 2.8h-8.2" transform="translate(-2 -1) scale(.94)"/>'
    rain = '<path d="M7.7 19.3v3.3M13.2 19.3v3.3M18.7 19.3v3.3"/>'
    rain_two = '<path d="M8 19.3v3.3M19 19.3v3.3"/>'
    # Dreifach-Schneeflocke (kleine gekreuzte Striche statt Punkte).
    def flake(x):
        return (f'<path d="M{x} 19.6v4.4m-2.2-2.2h4.4m-1.6-1.6 3.2 3.2m0-3.2-3.2 3.2" '
                'stroke-width=".95"/>')
    snow = ''.join(flake(x) for x in (7.5, 13.2, 18.9))
    sleet = flake(7.4) + '<path d="M14.4 19.3v3.5M19.8 19.3v3.5"/>'
    hail = '<circle cx="8" cy="21.5" r="1"/><circle cx="13.2" cy="21.5" r="1"/><circle cx="18.6" cy="21.5" r="1"/>'
    # Blitz als EIN Linienzug, mittig zwischen zwei Regenstrichen.
    lightning = '<path d="m13.8 17.2-3 4.1h3.1l-2.1 3.9"/>'
    fog = '<path d="M3 20h18M5 23h16"/>'
    if kind == 'sun':
        shapes = sun
    elif kind == 'partly':
        shapes = ('<circle cx="7.1" cy="6.2" r="3"/>'
                  '<path d="M7.1 1v1.5M1.7 6.2h1.7M3.3 2.5l1.1 1.1M11.1 2.5 10 3.6"/>' + cloud)
    elif kind == 'cloud':
        shapes = cloud + second_cloud
    elif kind == 'overcast':
        shapes = cloud
    elif kind == 'fog':
        shapes = cloud_open + fog
    elif kind == 'rain':
        shapes = cloud_open + rain
    elif kind == 'snow':
        shapes = cloud_open + snow
    elif kind == 'sleet':
        shapes = cloud_open + sleet
    elif kind == 'storm_snow':
        shapes = cloud_open + lightning + flake(7.2) + flake(19.3)
    else:
        shapes = cloud_open + lightning + rain_two
    return ('<svg viewBox="0 0 24 26" aria-label="' + escape(title) + '" '
            'role="img" xmlns="http://www.w3.org/2000/svg" fill="none" '
            'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
            'stroke-linejoin="round">' + shapes + '</svg>')


def fmt_temp(n):
    # Klassisches kaufmännisches Runden statt Pythons Rundung auf gerade Zahlen.
    if n is None:
        return '–'
    rounded = math.floor(n + 0.5) if n >= 0 else math.ceil(n - 0.5)
    return f'{rounded}°'


def _observation_from_csv(raw):
    """Read latest valid Luzern temperature, allowing legacy and OGD CSV formats."""
    decoded = raw.decode('utf-8-sig', errors='replace')
    lines = decoded.splitlines()
    header_idx = next((i for i, line in enumerate(lines)
                       if re.match(r'\s*(?:stn|station_abbr|station)\s*;', line, re.I)), None)
    if header_idx is None:
        raise ValueError('CSV-Spaltenkopf nicht gefunden')
    rows = csv.DictReader(io.StringIO('\n'.join(lines[header_idx:])), delimiter=';')
    best = None
    for original in rows:
        row = {str(k).strip().lower(): (v or '').strip() for k, v in original.items() if k is not None}
        station = row.get('stn') or row.get('station_abbr') or row.get('station') or ''
        if station.upper() != MEASUREMENT_STATION:
            continue
        value = convert(row.get('tre200s0'))
        stamp = row.get('time') or row.get('reference_timestamp') or row.get('date') or ''
        if value is None:
            continue
        try:
            if re.fullmatch(r'\d{12}', stamp):
                at = local_datetime(stamp)
            else:
                at = datetime.strptime(stamp, '%d.%m.%Y %H:%M').replace(tzinfo=timezone.utc).astimezone(TZ)
        except (ValueError, TypeError):
            continue
        age = (datetime.now(TZ) - at).total_seconds()
        if not (-900 <= age <= 4 * 3600):
            continue
        if best is None or at > best[0]:
            best = (at, value)
    return ({'temperature_c': best[1], 'station': 'Luzern',
             'measured_at': best[0].isoformat()} if best else None)


def read_current_measurement():
    """MeteoSchweiz measurement, trying the legacy snapshot and official OGD files."""
    try:
        result = _observation_from_csv(fetch(MEASUREMENTS_URL))
        if result:
            return result
        print('Keine aktuelle LUZ-Temperatur in der Messwert-Sammeldatei')
    except Exception as err:
        print('Alte Messwert-URL fehlgeschlagen:', repr(err))
    # Documented MeteoSchweiz SwissMetNet OGD dataset, station's 10-minute now file.
    collection = 'https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-smn'
    try:
        response = json.loads(fetch(collection + '/items?limit=100'))
        for item in sorted(response.get('features', []), key=lambda x: x.get('id', ''), reverse=True):
            for asset in item.get('assets', {}).values():
                href = asset.get('href', '')
                if re.search(r'ogd-smn_luz_t_now\.csv(?:\?|$)', href, re.I):
                    result = _observation_from_csv(fetch(href))
                    if result:
                        return result
        print('Keine aktuelle LUZ-Messwertdatei im OGD-Katalog gefunden')
    except Exception as err:
        print('OGD-Messwert-Abfrage fehlgeschlagen:', repr(err))
    return None


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
            'label': 'Heute' if offset == 0 else labels[cur.weekday()],
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
    current = read_current_measurement()
    payload = {'location': 'Kriens', 'source': 'MeteoSchweiz Open Data', 'forecast_item': item['id'],
               'updated': updated.isoformat(), 'current_measurement': current, 'days': days}
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
        max_probability = (f'Max. {max(available_probabilities):g}%' if available_probabilities else 'k. A.')
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
    # Das Symbol ist eine Kriens-Tagesprognose, keine gemessene Wetterbeobachtung.
    # Die Temperatur stammt aus einer echten MeteoSchweiz-Messung in Luzern.
    if current:
        measured_time = datetime.fromisoformat(current['measured_at']).strftime('%H:%M')
        current_header = ('<span class="current-weather" title="Temperatur-Messstation Luzern, ' +
                          escape(measured_time) + ' Uhr; Symbol: heutige Prognose für Kriens">' +
                          '<span class="current-icon">' + weather_symbol(days[0]['symbol_code']) + '</span>' +
                          '<span class="current-temp">' + fmt_temp(current['temperature_c']) + '</span>' +
                          '<span class="measured-at">Luzern · ' + escape(measured_time) + '</span></span>')
    else:
        current_header = '<span class="measured-at">Messwert derzeit nicht verfügbar</span>'
    html = '''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="3600"><meta name="source" content="MeteoSchweiz Open Data"><title>Wetter Kriens – MeteoSchweiz</title>
<!-- Design: Dunkel & gemuetlich, weisse Wetter-Icons, kompakte Windzeile -->
<style>
*{box-sizing:border-box}
body{font-family:system-ui,Arial,sans-serif;background:#263740;color:#f7f3eb;margin:0;padding:12px}
header{display:flex;justify-content:space-between;gap:10px;align-items:center}
.header-left{display:flex;align-items:center;gap:15px;min-width:0}
.current-weather{display:inline-flex;gap:8px;align-items:center;color:#fff;white-space:nowrap}
.current-icon svg{display:block;width:31px;height:31px;color:#fff}
.current-temp{font-size:24px;font-weight:800}
.measured-at{font-size:10px;color:#b7c9d2;white-space:nowrap}
header h1{font-size:24px;margin:0;font-weight:800;color:#fff;white-space:nowrap}
.days{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:4px;margin-top:28px}
.day{background:#334b59;border:1px solid #536975;border-radius:11px;padding:9px 5px 8px;text-align:center;min-width:0;display:flex;flex-direction:column;align-items:center}
.day:nth-child(2){background:#435048;border-color:#607064}
.day:nth-child(3){background:#554a4b;border-color:#776367}
.day:nth-child(4){background:#374c59;border-color:#567080}
.day:nth-child(5){background:#47534f;border-color:#64756d}
.day h2{margin:0;font-size:38px;font-weight:750;color:#fff}
.icon{height:95px;display:flex;align-items:center;justify-content:center;color:#fff;margin:3px auto 1px}
.icon svg{width:88px;height:88px;display:block;color:#fff}
.day strong{font-size:32px;white-space:nowrap;color:#fff;font-weight:750}
.wind{font-size:29px;color:#fff;white-space:nowrap;margin-top:4px;line-height:1.2;min-height:20px}
.wind .arrow{font-size:33px;line-height:1;vertical-align:-1px;font-weight:700}
.probability{font-size:32px;font-weight:700;color:#a8e1f7;margin-top:5px;white-space:nowrap}
.bars{height:20px;width:70%;display:flex;align-items:flex-end;gap:0.5px;border-bottom:1px solid #899fa7;margin:5px auto 0}
.bar{display:block;background:#7ecae8;flex:1;border-radius:2px 2px 0 0;min-width:0}
.bar.missing{background:#61727a;height:2px}
.hours{width:72%;display:flex;justify-content:space-between;font-size:9px;color:#d0dbdd;padding:2px 2px 0}
.rain{font-size:29px;font-weight:700;color:#a8e1f7;margin-top:5px;white-space:nowrap}
.radar{display:inline-flex;align-items:center;justify-content:center;background:#415b69;color:#f1fbff;border:1px solid #7095a5;padding:6px 10px;border-radius:8px;font-size:12px;text-decoration:none;font-weight:600;white-space:nowrap}
.radar:focus,.radar:hover{background:#527487}
/* Keine Fusszeile oder Erklärung unter den Wetterkacheln. */
/* Auf kleinen DAKboard-Blöcken werden die Grössen begrenzt, damit alle fünf Kacheln lesbar bleiben. */
@media(max-width:850px){
body{padding:6px}header h1{font-size:clamp(17px,3vw,24px)}.radar{padding:5px 7px;font-size:11px}.header-left{gap:7px}.current-weather{gap:4px}.current-temp{font-size:clamp(17px,3vw,24px)}.current-icon svg{width:clamp(22px,3.8vw,31px);height:clamp(22px,3.8vw,31px)}.measured-at{font-size:9px}
.days{gap:3px;margin-top:22px}.day{padding:7px 1px 6px}
.day h2{font-size:clamp(15px,3.2vw,30px)}
.icon{height:clamp(40px,10vw,77px)}.icon svg{width:clamp(38px,9.5vw,73px);height:clamp(38px,9.5vw,73px)}
.day strong{font-size:clamp(11px,3.1vw,27px);letter-spacing:-.55px}
.wind{font-size:clamp(10px,2.9vw,25px);min-height:0}.wind .arrow{font-size:1.1em}
.probability{font-size:clamp(11px,3.1vw,27px);letter-spacing:-.5px}
.rain{font-size:clamp(10px,2.95vw,25px)}
.bars{height:20px;width:80%;gap:0.5px}.hours{font-size:8px;width:85%}
}

</style></head><body><header><div class="header-left"><h1>Wetter Kriens aktuell</h1>''' + current_header + '''</div><a class="radar" target="_blank" rel="noopener" href="''' + RADAR + '''">Regenradar</a></header><main class="days">''' + ''.join(cards) + '''</main></body></html>'''
    Path('index.html').write_text(html, encoding='utf-8')
    print('Generated five-day forecast:', item['id'])


if __name__ == '__main__':
    main()
