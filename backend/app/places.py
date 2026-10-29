"""Free map data: Overpass (shops + opening hours), Nominatim (named search), OSRM table (travel times).
Results are cached for 10 minutes to stay inside the free fair-use limits."""
import asyncio, math, os, re, time
import httpx

UA = {'User-Agent': 'Wayfarer/2.1 (%s)' % os.getenv('WAYFARER_CONTACT', 'student project')}
OVERPASS = 'https://overpass-api.de/api/interpreter'
NOMINATIM = 'https://nominatim.openstreetmap.org/search'
_cache, _lock = {}, asyncio.Lock()
FILTER = re.compile(r'^[a-z_]+=[a-z_]+$')


def _km(a, b):
    r = math.pi / 180
    x = math.sin((b[0] - a[0]) * r / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin((b[1] - a[1]) * r / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


async def search(f, q, cat, lat, lon, radius):
    if not f:
        return await search_named(q, [], lat, lon, radius)
    key = (tuple(f or ()), '' if f else q, round(lat, 3), round(lon, 3), radius)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    out = []
    async with httpx.AsyncClient(timeout=25, headers=UA) as c:
        if f:
            parts = ''
            for item in f:
                if not FILTER.match(item):
                    raise ValueError('bad filter')
                k, v = item.split('=')
                parts += f'nwr["{k}"="{v}"](around:{int(radius)},{lat},{lon});'
            r = await c.post(OVERPASS, data={'data': f'[out:json][timeout:20];({parts});out center tags 80;'})
            r.raise_for_status()
            for e in r.json().get('elements', []):
                tg, la, lo = e.get('tags', {}), e.get('lat', e.get('center', {}).get('lat')), e.get('lon', e.get('center', {}).get('lon'))
                if la is None:
                    continue
                out.append({'lat': la, 'lon': lo, 'name': tg.get('name') or tg.get('brand') or f'{cat} (unnamed)',
                            'addr': tg.get('addr:street') or tg.get('addr:suburb') or '', 'oh': tg.get('opening_hours'),
                            'ph': tg.get('phone') or tg.get('contact:phone') or ''})
    seen, res = set(), []
    for c in sorted(out, key=lambda c: _km((lat, lon), (c['lat'], c['lon']))):
        k = (c['name'], round(c['lat'], 3), round(c['lon'], 3))
        if k not in seen:
            seen.add(k)
            res.append(c)
    _cache[key] = (time.time(), res[:10])
    return res[:10]


async def osrm_table(pts, mode):
    """Minutes matrix from the free OSRM demo servers, or None if unavailable."""
    if len(pts) > 100:
        return None
    prof = 'routed-car' if mode == 'car' else 'routed-foot'
    coords = ';'.join(f'{lon},{lat}' for lat, lon in pts)
    try:
        async with httpx.AsyncClient(timeout=6, headers=UA) as c:
            j = (await c.get(f'https://routing.openstreetmap.de/{prof}/table/v1/driving/{coords}',
                             params={'annotations': 'duration'})).json()
        if j.get('code') != 'Ok':
            return None
        return [[None if x is None else math.ceil(x / 60) for x in row] for row in j['durations']]
    except Exception:
        return None


# ---------- named places: several free sources, scored by how many words match, then by distance ----------
STOP = {'the', 'of', 'in', 'at', 'near', 'to', 'and', 'for', 'my', 'go', 'want', 'i', 'is'}


def norm(s):
    return re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower().replace("'", '').replace('\u2019', ''))


def toks(q):
    return [w for w in norm(q).split() if w not in STOP]


def score(ts, text):
    words, hit = set(norm(text).split()), 0
    for t in ts:
        if t in words or (len(t) >= 3 and any(w.startswith(t) or (len(w) >= 3 and t.startswith(w)) for w in words)):
            hit += 1
    return hit / len(ts) if ts else 0.0


async def _overpass_named(ts, lat, lon, radius):
    alt = '|'.join(t for t in ts if len(t) >= 3)
    if not alt:
        return []
    ql = (f'[out:json][timeout:25];(nwr["name"~"{alt}",i](around:{int(radius)},{lat},{lon});'
          f'nwr["alt_name"~"{alt}",i](around:{int(radius)},{lat},{lon}););out center tags 200;')
    async with httpx.AsyncClient(timeout=30, headers=UA) as c:
        r = await c.post(OVERPASS, data={'data': ql})
    r.raise_for_status()
    out = []
    for e in r.json().get('elements', []):
        tg, la, lo = e.get('tags', {}), e.get('lat', e.get('center', {}).get('lat')), e.get('lon', e.get('center', {}).get('lon'))
        if la is None:
            continue
        out.append({'lat': la, 'lon': lo, 'name': tg.get('name') or tg.get('alt_name') or 'Unnamed place',
                    'addr': tg.get('addr:street') or '', 'oh': tg.get('opening_hours'),
                    'text': ' '.join(tg.get(k, '') for k in ('name', 'alt_name', 'short_name', 'addr:housename', 'operator'))})
    return out


async def _nominatim(q, lat, lon):
    async with _lock:  # policy: at most one request per second
        async with httpx.AsyncClient(timeout=15, headers=UA) as c:
            r = await c.get(NOMINATIM, params={'format': 'jsonv2', 'limit': 8, 'q': q,
                                               'viewbox': f'{lon-.3},{lat+.3},{lon+.3},{lat-.3}'})
        await asyncio.sleep(1.1)
    r.raise_for_status()
    out = []
    for e in r.json():
        dn = e.get('display_name', '')
        out.append({'lat': float(e['lat']), 'lon': float(e['lon']), 'name': e.get('name') or dn.split(',')[0],
                    'addr': ','.join(dn.split(',')[1:3]), 'oh': None, 'text': dn})
    return out


async def _photon(q, lat, lon):
    async with httpx.AsyncClient(timeout=12, headers=UA) as c:
        r = await c.get('https://photon.komoot.io/api/', params={'q': q, 'lat': lat, 'lon': lon, 'limit': 8})
    r.raise_for_status()
    out = []
    for f in r.json().get('features', []):
        p, (lo, la) = f.get('properties', {}), f['geometry']['coordinates']
        txt = ' '.join(str(p.get(k, '')) for k in ('name', 'street', 'district', 'city', 'state'))
        out.append({'lat': la, 'lon': lo, 'name': p.get('name') or p.get('street') or 'Place',
                    'addr': ', '.join(x for x in (p.get('street'), p.get('district') or p.get('city')) if x), 'oh': None, 'text': txt})
    return out


async def search_named(q, hints, lat, lon, radius):
    key = ('n', q, tuple(hints), round(lat, 3), round(lon, 3))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    ts, parts, variants = toks(q), [x.strip() for x in q.split(',') if x.strip()], []
    for v in [q, *hints, ' '.join(parts[1:]) if len(parts) > 1 else '', ' '.join(parts[-2:]) if len(parts) > 2 else '']:
        if v and v not in variants:
            variants.append(v)
    jobs = [_overpass_named(ts, lat, lon, max(radius, 3000)), _photon(q, lat, lon)] + [_nominatim(v, lat, lon) for v in variants[:3]]
    got = await asyncio.gather(*jobs, return_exceptions=True)
    if all(isinstance(g, Exception) for g in got):
        raise RuntimeError('all place sources failed')
    best = {}
    for g in got:
        if isinstance(g, Exception):
            continue
        for c in g:
            sc = score(ts, c['name'] + ' ' + c['text'])
            d = _km((lat, lon), (c['lat'], c['lon']))
            k = (round(c['lat'], 4), round(c['lon'], 4))
            if k not in best or sc > best[k]['match']:
                best[k] = {'lat': c['lat'], 'lon': c['lon'], 'name': c['name'], 'addr': c['addr'], 'oh': c['oh'],
                           'ph': '', 'match': round(sc, 2), 'rank': 100 * sc - min(d, 100) * 1.5}
    res = sorted(best.values(), key=lambda c: -c['rank'])
    res = [c for c in res if c['match'] > 0][:10] or res[:5]
    for c in res:
        c.pop('rank')
    _cache[key] = (time.time(), res)
    return res
