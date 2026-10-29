"""SQLite memory: how long you really spend per kind of stop. Plain averaging, shrunk toward
the default until there are enough observations. No hidden model."""
import os, sqlite3, time
from contextlib import closing


def _conn():
    c = sqlite3.connect(os.getenv('WAYFARER_DB', 'wayfarer.db'))
    c.execute('create table if not exists obs(cat text, minutes integer, ts integer)')
    return c


def record(cat, minutes):
    if not cat or not 1 <= minutes <= 180:
        return
    with closing(_conn()) as c, c:
        c.execute('insert into obs values(?,?,?)', (cat, int(minutes), int(time.time())))


def estimate(cat, default, prior=3, window=20):
    with closing(_conn()) as c:
        rows = [r[0] for r in c.execute('select minutes from obs where cat=? order by ts desc limit ?', (cat, window))]
    if not rows:
        return default
    return max(1, round((sum(rows) + prior * default) / (len(rows) + prior)))
