#!/usr/bin/env python3
"""
qadmus_one_day.py  --  Prayer time comparison tool for Al-Qadmus, Tartus, Syria.

Calculates Fajr, Sunrise, Dhuhr, Asr, Maghrib, and Isha for one day using
multiple Syrian-relevant methods (via ephem) and the Aladhan API. Compare
the output to the Roznama Android app to find the closest matching method.

Usage:
    python qadmus_one_day.py                                          # today
    python qadmus_one_day.py 2026-06-27                               # specific date
    python qadmus_one_day.py 2026-06-27 03:37 12:39 16:27 19:56 21:34  # + Roznama times
                                        ^Fajr ^Dhuhr ^Asr ^Maghrib ^Isha
"""

import sys
import math
import json
from datetime import datetime, timedelta
from urllib.request import urlopen
from urllib.parse import urlencode
import ephem

# ---------------------------------------------------------------------------
# Location: Al-Qadmus, Tartus Governorate, Syria
# ---------------------------------------------------------------------------
LAT  = 35.10138   # degrees N  ← adjust here to test different coordinates
LON  = 36.16111   # degrees E  ← adjust here to test different coordinates
ELEV = 380        # approximate elevation in metres
TZ   = 3          # Syria UTC+3 (year-round since 2022)

# ---------------------------------------------------------------------------
# Local ephem methods
# mgh = minutes added to raw Maghrib (Syrian احتياط / precautionary delay)
# dhr = minutes added to Dhuhr   (Roznama convention: sun must clear zenith)
# asr = minutes added to Asr     (Roznama rounding convention)
# ---------------------------------------------------------------------------
METHODS = [
    # Standard reference methods
    {'name': 'Syrian Ministry (18/17)',          'fajr': '-18',   'isha': '-17',   'isha_90': False, 'mgh': 0, 'dhr': 0, 'asr': 0},
    {'name': 'Syrian Hashimi (20/18)',           'fajr': '-20',   'isha': '-18',   'isha_90': False, 'mgh': 0, 'dhr': 0, 'asr': 0},
    {'name': 'Egyptian (19.5/17.5)',             'fajr': '-19.5', 'isha': '-17.5', 'isha_90': False, 'mgh': 0, 'dhr': 0, 'asr': 0},
    {'name': 'Umm Al-Qura (18.5/90min)',        'fajr': '-18.5', 'isha': None,    'isha_90': True,  'mgh': 0, 'dhr': 0, 'asr': 0},
    # Angle variants
    {'name': 'Syrian 17.5/17',                  'fajr': '-17.5', 'isha': '-17',   'isha_90': False, 'mgh': 0, 'dhr': 0, 'asr': 0},
    {'name': 'Syrian 18/17 + Mgh+3',            'fajr': '-18',   'isha': '-17',   'isha_90': False, 'mgh': 3, 'dhr': 0, 'asr': 0},
    {'name': 'Syrian 17.5/17 + Mgh+3',          'fajr': '-17.5', 'isha': '-17',   'isha_90': False, 'mgh': 3, 'dhr': 0, 'asr': 0},
    # Best-guess Roznama match: 17.5/17, Mgh+3, Dhuhr+1, Asr+1
    {'name': '*** Roznama optimized ***',        'fajr': '-17.5', 'isha': '-17',   'isha_90': False, 'mgh': 3, 'dhr': 1, 'asr': 1},
]

# Aladhan API methods
ALADHAN = [
    (3,  'Aladhan MWL (18/17)'),          # Muslim World League
    (5,  'Aladhan Egypt (19.5/17.5)'),    # Egyptian General Authority
    (13, 'Aladhan Diyanet'),              # Turkey Diyanet
]


# ---------------------------------------------------------------------------
# Calculation helpers
# ---------------------------------------------------------------------------

def _new_obs(utc_datetime):
    obs = ephem.Observer()
    obs.lat = str(LAT)
    obs.lon = str(LON)
    obs.elevation = ELEV
    obs.date = utc_datetime
    return obs


def _fmt(utc_dt):
    """Convert UTC datetime to local Syria time string 'HH:MM'."""
    return (utc_dt + timedelta(hours=TZ)).strftime('%H:%M')


def calc_asr(utc_midnight):
    """
    Accurate Asr time using Shafi method (shadow = 1x object height).
    Returns UTC datetime.
    """
    obs = _new_obs(utc_midnight)
    sun = ephem.Sun()

    # Solar noon provides an accurate declination reference
    obs.horizon = '0'
    transit = obs.next_transit(sun)

    # Declination at transit
    obs2 = _new_obs(transit.datetime())
    sun.compute(obs2)
    dec = float(sun.dec)   # radians
    lat = float(obs.lat)   # radians (ephem stores angles in radians)

    # Asr altitude: atan(1 / (shadow_factor + tan(|lat - dec|)))
    asr_alt = math.atan(1.0 / (1.0 + math.tan(abs(lat - dec))))

    # Hour angle when sun reaches that altitude
    cos_h = ((math.sin(asr_alt) - math.sin(lat) * math.sin(dec)) /
             (math.cos(lat) * math.cos(dec)))
    cos_h = max(-1.0, min(1.0, cos_h))
    h_hours = math.acos(cos_h) * 12.0 / math.pi

    asr_ephem = ephem.Date(float(transit) + h_hours * ephem.hour)
    return asr_ephem.datetime()


def calc_method(date, fajr_horizon, isha_horizon, isha_90=False,
                mgh_adj=0, dhr_adj=0, asr_adj=0):
    """
    Calculate prayer times for one method.
    mgh_adj : minutes added to Maghrib (احتياط precautionary delay)
    dhr_adj : minutes added to Dhuhr   (sun-past-zenith convention)
    asr_adj : minutes added to Asr     (rounding convention)
    Returns dict of prayer name -> 'HH:MM' local time strings (including Sunrise).
    """
    utc_midnight = datetime(date.year, date.month, date.day, 0, 0, 0)
    obs = _new_obs(utc_midnight)
    sun = ephem.Sun()

    # Fajr (sun rising to fajr_horizon)
    obs.horizon = fajr_horizon
    fajr = _fmt(obs.next_rising(sun).datetime())

    # Sunrise
    obs.date = utc_midnight
    obs.horizon = '0'
    sunrise = _fmt(obs.next_rising(sun).datetime())

    # Dhuhr (solar transit / noon) + optional offset
    obs.date = utc_midnight
    obs.horizon = '0'
    dhuhr_utc = obs.next_transit(sun).datetime()
    dhuhr = _fmt(dhuhr_utc + timedelta(minutes=dhr_adj))

    # Asr + optional offset
    asr = _fmt(calc_asr(utc_midnight) + timedelta(minutes=asr_adj))

    # Maghrib (sunset) + احتياط adjustment
    obs.date = utc_midnight
    obs.horizon = '0'
    maghrib_utc = obs.next_setting(sun).datetime()
    maghrib = _fmt(maghrib_utc + timedelta(minutes=mgh_adj))

    # Isha
    if isha_90:
        isha = _fmt(maghrib_utc + timedelta(minutes=90))
    else:
        obs.date = utc_midnight
        obs.horizon = isha_horizon
        isha = _fmt(obs.next_setting(sun).datetime())

    return {
        'Fajr': fajr, 'Sunrise': sunrise, 'Dhuhr': dhuhr,
        'Asr': asr, 'Maghrib': maghrib, 'Isha': isha,
    }


def fetch_aladhan(date, method_id):
    """Query Aladhan API for one method. Returns dict or None on failure."""
    try:
        date_str = date.strftime('%d-%m-%Y')
        params = urlencode({
            'latitude':        LAT,
            'longitude':       LON,
            'method':          method_id,
            'school':          0,              # 0 = Shafi (shadow factor 1)
            'timezonestring':  'Asia/Damascus',
        })
        url = f'http://api.aladhan.com/v1/timings/{date_str}?{params}'
        with urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        t = data['data']['timings']
        return {
            'Fajr':    t['Fajr'][:5],
            'Sunrise': t['Sunrise'][:5],
            'Dhuhr':   t['Dhuhr'][:5],
            'Asr':     t['Asr'][:5],
            'Maghrib': t['Maghrib'][:5],
            'Isha':    t['Isha'][:5],
        }
    except Exception as e:
        print(f'  [Aladhan method {method_id} unavailable: {e}]')
        return None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def hm_to_min(hhmm):
    h, m = map(int, hhmm.split(':'))
    return h * 60 + m


def print_table(results, roznama=None):
    # Roznama doesn't include Sunrise in the comparison diff (it's not a prayer)
    prayers  = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
    all_cols = ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
    NW, CW = 34, 9

    header = f"{'Method':<{NW}}" + ''.join(f'{c:>{CW}}' for c in all_cols)
    sep    = '-' * len(header)

    print(header)
    print(sep)
    for name, times in results.items():
        if times is None:
            print(f'{name:<{NW}}  (unavailable)')
        else:
            row = f'{name:<{NW}}'
            for c in all_cols:
                row += f'{times.get(c, "N/A"):>{CW}}'
            print(row)

    if roznama:
        roz_row = f"{'Roznama (reference)':<{NW}}"
        for c in all_cols:
            roz_row += f'{roznama.get(c, "  --  "):>{CW}}'
        print(sep)
        print(roz_row)
        print()
        print('Deviation from Roznama in minutes  (+ = later, - = earlier):')
        print('(Sunrise excluded — not a prayer time)')
        sep2 = '-' * (NW + CW * len(prayers))
        print(sep2)

        totals = {}
        for name, times in results.items():
            if times is None:
                continue
            diffs = {p: hm_to_min(times[p]) - hm_to_min(roznama[p])
                     for p in prayers if p in times and p in roznama}
            total = sum(abs(v) for v in diffs.values())
            totals[name] = total
            diff_str = ''.join(f'{diffs.get(p, 0):>+{CW}}' for p in prayers)
            print(f'{name:<{NW}}{diff_str}   |total|={total}min')

        if totals:
            best = min(totals, key=totals.get)
            print(f'\n  Best match: {best}  (total deviation = {totals[best]} min)')


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def prompt_date():
    today = datetime.now()
    default_str = today.strftime('%Y-%m-%d')
    while True:
        raw = input(f'  Date [YYYY-MM-DD, Enter = {default_str}]: ').strip()
        if raw == '':
            return datetime(today.year, today.month, today.day)
        try:
            return datetime.strptime(raw, '%Y-%m-%d')
        except ValueError:
            print('  Invalid format — please use YYYY-MM-DD (e.g. 2026-06-27)')


def prompt_roznama():
    prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
    print('  Enter Roznama times to compare (HH:MM), or press Enter to skip:')
    times = {}
    for p in prayers:
        while True:
            raw = input(f'    {p}: ').strip()
            if raw == '':
                return None      # user skipped — abort comparison
            try:
                datetime.strptime(raw, '%H:%M')
                times[p] = raw
                break
            except ValueError:
                print('    Invalid format — use HH:MM (e.g. 03:37)')
    return times


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print('=' * 65)
    print('  Al-Qadmus Prayer Time Calculator')
    print(f'  LAT={LAT}°N  LON={LON}°E  Elev~{ELEV}m  UTC+{TZ}')
    print(f'  (To test different coordinates, edit LAT/LON at top of script)')
    print('=' * 65)

    while True:
        print()
        date = prompt_date()

        print()
        want_roznama = input('  Compare with Roznama times? [y/N]: ').strip().lower()
        roznama = prompt_roznama() if want_roznama == 'y' else None

        print(f'\nCalculating for {date.strftime("%A %d %B %Y")}...')

        results = {}
        for m in METHODS:
            results[m['name']] = calc_method(
                date, m['fajr'], m.get('isha'), m['isha_90'],
                mgh_adj=m.get('mgh', 0),
                dhr_adj=m.get('dhr', 0),
                asr_adj=m.get('asr', 0))

        print('Fetching Aladhan API...', end=' ', flush=True)
        for mid, label in ALADHAN:
            results[label] = fetch_aladhan(date, mid)
        print('done\n')

        print_table(results, roznama)

        print()
        again = input('  Try another date? [y/N]: ').strip().lower()
        if again != 'y':
            break

    print('\nDone.')


if __name__ == '__main__':
    main()
