Ältere Nachrichten werden geladen…
Benutzeranhang

Sehr gut, die neue Wetteranzeige funktioniert! ✅ Die fünf Tage, Temperaturen, Windgeschwindigkeiten, Regenbalken und Niederschlagsmengen werden angezeigt.

Mir fallen auf deinem Screenshot allerdings noch ein paar Dinge auf, die ich vor der Einbindung ins DAKboard verbessern würde.
Was ich noch optimieren würde

    Wochentage auf Deutsch: Statt «Tue», «Wed», «Thu» sollten «Di», «Mi», «Do» erscheinen.

    Regenwahrscheinlichkeit direkt ablesbar: Momentan sieht man die Balken, aber die genauen Prozentwerte erst, wenn man mit der Maus darüberfährt. Das ist für euren Touchscreen nicht ideal.

    Wind verständlicher darstellen: Die Angabe ~ 17 km/h · Böen 58 würde ich beispielsweise als Wind 17 km/h · Böen 58 km/h schreiben.

    Platz sparen: Die fünf Wetterkarten könnten insgesamt etwas flacher werden, damit mehr Platz für den Familienkalender und die Ämtliliste bleibt.

Besonders wichtig: die Regenbalken

Bei deinem heutigen Wetter sehe ich hohe Balken am frühen Morgen und am Nachmittag. Das ist genau die Information, die du wolltest.

Ich würde zusätzlich den höchsten Prozentwert jedes Tages anzeigen. Zum Beispiel:

Heute

Beispiel

7° / 14°

Max. 85 % Regen

Die Balken darunter zeigen, zu welcher Tageszeit Regen wahrscheinlich ist.

Die 85 % sind ein Beispielwert, nicht aus deinem Screenshot ausgelesen.

Meine Empfehlung: Wir nehmen diese vier kleinen Anpassungen noch vor und integrieren danach die Wetteranzeige in DAKboard. Technisch haben wir die schwierige Arbeit inzwischen geschafft.

Eine Frage zum Schluss: Möchtest du bei fünf Tagen bleiben, oder sollen es sechs Tage sein wie bei deinem ursprünglichen MeteoSchweiz-Beispiel?
5 it okay und ja gerne anpassungen machen

Die überarbeitete Version ist bereit! Ich habe deine funktionierende Wetteranzeige gezielt angepasst, ohne die MeteoSchweiz-Datenabfrage zu verändern.
Das ist jetzt verbessert

Wetter Kriens

MeteoSchweiz

Heute

7° / 14°

17 km/h

Max. 90%

Morgen

5° / 12°

5 km/h

Max. 10%

Di 27.10.

6° / 16°

4 km/h

Max. 5%

Mi 28.10.

8° / 13°

5 km/h

Max. 40%

Do 29.10.

6° / 11°

5 km/h

Max. 25%

Regenwahrscheinlichkeit je 3 Stunden · höchste Wahrscheinlichkeit zusätzlich als Zahl.
Gestaltungsvorschau mit Beispielwerten; die tatsächlichen Daten werden aus MeteoSchweiz geladen.

Die endgültige Version enthält weiterhin die täglichen Niederschlagsmengen, Windböen ab 40 km/h und den Regenradar-Button. Sie ist etwas flacher und für euren DAKboard-Bildschirm platzsparender.
Schritt 1 – Neue Datei herunterladen

update_weather.py

Korrigierte Version für 5 Tage, deutsche Wochentage und kompaktere Anzeige.

 Überarbeitete Wetterdatei herunterladen
Schritt 2 – In GitHub ersetzen

    Lade die Datei herunter und öffne sie mit dem Windows-Editor.

    Kopiere den gesamten Inhalt mit Strg + A und Strg + C.

    Öffne Deine GitHub-Wetterdatei.

    Klicke auf das Stiftsymbol.

    Ersetze den gesamten bisherigen Code durch den neuen (Strg + A, dann Strg + V).

    Klicke auf Commit changes und bestätige.

Schritt 3 – Aktualisierung starten

Öffne MeteoSchweiz-Wetter aktualisieren und starte über Run workflow einen neuen Durchlauf.

Die Datei ist auf Python-Syntax geprüft, aber noch nicht mit Live-Wetterdaten getestet.

Sobald der Durchlauf grün ist, öffne wieder deine Wetteranzeige für Kriens.

Danach kommt der letzte Schritt: Wir integrieren das kompakte Wetter-Widget in die Hauptseite deines DAKboards und prüfen, ob der Regenradar-Button am Touchscreen funktioniert.
update_weather.pyCode
Benutzeranhang

Auf deinem Screenshot sehe ich, dass noch die alte Wetteranzeige dargestellt wird:

    Die Wochentage stehen weiterhin auf Englisch (Tue, Wed, Thu).

    Die maximale Regenwahrscheinlichkeit in Prozent fehlt.

    Die Windangaben sind noch nicht ausgeschrieben.

Auch wenn GitHub einen grünen Haken anzeigt, ist die neue Darstellung offenbar noch nicht auf deiner Wetterseite angekommen.

Wir prüfen jetzt zuerst, ob es nur am Browser-Cache liegt oder ob die neue Version noch nicht veröffentlicht wurde.
Schritt 1 – Seite neu laden

    Öffne deine Wetteranzeige für Kriens.

    Drücke auf deinem Windows-PC Strg + F5.

    Prüfe, ob nun die deutschen Wochentage und die Prozentangaben erscheinen.

Falls nach Strg + F5 noch immer die alte Version erscheint, liegt es wahrscheinlich nicht am Browser.

Ich habe gerade die öffentlich abrufbare GitHub-Datei geprüft. Dort sehe ich noch eine ältere Version von update_weather.py, die lediglich drei Tage erzeugt. Das passt nicht zur Fünf-Tage-Anzeige auf deinem Screenshot. Möglicherweise ist die öffentliche Datei noch nicht auf dem neuesten Stand. 
GitHub

Schritt 2 – Prüfen, ob die neue Datei gespeichert ist

    Öffne update_weather.py auf GitHub.

    Drücke Strg + F und suche nach Max. oder Regenwahrscheinlichkeit.

    Wenn du die neuen Texte im Code nicht findest, müssen wir kontrollieren, welche Dateiversion zuletzt gespeichert wurde.

Schicke mir am besten einen Screenshot vom oberen Bereich der Datei mit dem letzten Änderungsdatum. Dann können wir feststellen, ob wir die Datei nochmals ersetzen müssen oder ob nur die Veröffentlichung hinterherhinkt.
Benutzeranhang
Benutzeranhang

Jetzt sehe ich auf deinen Screenshots, weshalb noch die alte Darstellung erscheint. Auf GitHub liegt noch die vorherige Version mit 190 Codezeilen. Die korrigierte Version hat 193 Zeilen.

Du hast also nichts falsch eingerichtet – wir müssen nur sicherstellen, dass die neueste Datei tatsächlich auf GitHub gespeichert wird.
Schritt 1 – Richtige Datei herunterladen

update_weather.py – korrigierte Version

193 Zeilen, deutsche Wochentage, maximale Regenwahrscheinlichkeit und kompaktere Darstellung

Korrigierte Python-Datei herunterladen
Schritt 2 – Auf GitHub ersetzen

    Öffne die heruntergeladene Datei auf deinem Computer im Windows-Editor.

    Drücke Strg + A und Strg + C.

    Öffne Deine GitHub-Datei.

    Klicke auf das Stiftsymbol rechts oben.

    Klicke in den Code und drücke Strg + A, danach Strg + V.

    Klicke auf Commit changes und bestätige nochmals.

Kontrolle: Nach dem Speichern sollte GitHub ungefähr 193 lines anzeigen, nicht mehr 190.
Schritt 3 – Wetteranzeige aktualisieren

Öffne MeteoSchweiz-Wetter aktualisieren.

Starte mit Run workflow → main → Run workflow einen neuen Durchlauf.

Wenn der grün ist, öffne deine Wetteranzeige und aktualisiere mit Strg + F5.

Danach sollten die Wochentage deutsch sein und oberhalb der Regenbalken beispielsweise «Max. 75 % Regen» stehen.

Die Wetterdatenabfrage, fünf Tage und der Regenradar-Button bleiben unverändert.
update_weather.pyCode
ich kann die korrigierte python datei nicht herunterladnden
1m 17s nachgedacht

Kein Problem! 😊 Ich habe die korrigierte Datei nochmals neu bereitgestellt – diesmal auch als ZIP-Datei, falls der direkte Python-Download nicht funktioniert.

MeteoSchweiz – korrigierte Wetterdatei

5 Tage, deutsche Wochentage, Regenwahrscheinlichkeit und Wind

Alternativ: Python-Datei direkt herunterladen
So gehst du vor

    Lade die ZIP-Datei herunter.

    Öffne deinen Downloads-Ordner.

    Rechtsklick auf die ZIP-Datei → Alle extrahieren.

    Im entpackten Ordner findest du update_weather.py.

    Öffne diese mit dem Windows-Editor und kopiere den gesamten Inhalt.

    Öffne deine GitHub-Datei und ersetze dort über das Stiftsymbol den bisherigen Code.

Danach mit Commit changes speichern.

Falls auch die ZIP-Datei nicht heruntergeladen werden kann, sag mir das. Dann machen wir die notwendigen Korrekturen direkt im GitHub-Editor, ohne eine Datei herunterzuladen.
meteoschweiz_kriens_5tage_korrigiert.pyCode



    
  
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

