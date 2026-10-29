"""Parse a practical subset of OpenStreetMap `opening_hours` into minute intervals.
Minutes count from midnight today; tomorrow's hours are shifted by 1440.
Returns None when hours are missing or unreadable (we never guess)."""
import re

DAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
RULE = re.compile(r'^([A-Za-z,\- ]*?)\s*(off|(?:\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\s*,?\s*)+)$')


def _day_in(spec, d):
    ok = False
    for part in spec.split(','):
        q = [x.strip() for x in part.strip().split('-')]
        if any(x not in DAYS for x in q):
            continue  # e.g. "PH" (public holidays) is ignored
        i = [DAYS.index(x) for x in q]
        ok = ok or (i[0] == d if len(i) == 1 else (d - i[0]) % 7 <= (i[1] - i[0]) % 7)
    return ok


def day_intervals(oh, d):
    if re.search(r'24/7', oh):
        return [(0, 1440)]
    seen, res = False, None
    for raw in oh.split(';'):
        m = RULE.match(raw.strip())
        if not m:
            continue
        seen = True
        spec = m.group(1).strip()
        if spec and not _day_in(spec, d):
            continue
        if m.group(2) == 'off':
            res = []
            continue
        res = []
        for a, b, c, e in re.findall(r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})', m.group(2)):
            s, t = int(a) * 60 + int(b), int(c) * 60 + int(e)
            res.append((s, t if t > s else t + 1440))
    return res if res is not None else ([] if seen else None)


def open_intervals(oh, weekday):
    """weekday: Monday=0. Covers today and tomorrow."""
    if not oh:
        return None
    today = day_intervals(oh, weekday)
    if today is None:
        return None
    tomorrow = day_intervals(oh, (weekday + 1) % 7) or []
    return today + [(s + 1440, e + 1440) for s, e in tomorrow]
