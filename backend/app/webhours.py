"""Optional: ask Gemini (with Google Search grounding) for a place's opening hours.
The answer is only accepted if it parses as OpenStreetMap-style hours, and the app labels it
'from the web, unverified'. A daily cap protects your free quota. Google pages are NOT scraped."""
import os, re
from datetime import date
import httpx
from . import hours

_count, _cache = {}, {}


def clean_hours(text):
    for line in reversed([l.strip(' `"*\t') for l in (text or '').splitlines() if l.strip()]):
        if len(line) <= 200 and hours.open_intervals(line, 0) is not None:
            return line
    return None


def _safe(s):
    return re.sub(r'[\x00-\x1f"]', ' ', s or '')[:100]


async def lookup(name, addr, lat, lon):
    key, model = os.getenv('GEMINI_API_KEY'), os.getenv('GEMINI_MODEL')
    if not key or not model:
        return {'oh': None, 'note': 'Web lookup needs a Gemini key on the server.'}
    ck = (name, round(lat, 4), round(lon, 4))
    if ck in _cache:
        return _cache[ck]
    today, cap = date.today().isoformat(), int(os.getenv('WAYFARER_WEB_HOURS_DAILY', '20'))
    if _count.get(today, 0) >= cap:
        return {'oh': None, 'note': 'Daily web-lookup limit reached. This protects your free quota.'}
    _count[today] = _count.get(today, 0) + 1
    prompt = ('Using Google Search, find the current opening hours of the place named "%s" (%s) near latitude %.4f, longitude %.4f. '
              'Reply with ONLY one final line in OpenStreetMap opening_hours format, for example '
              '"Mo-Fr 09:00-17:00; Sa 09:00-13:00", or the single word UNKNOWN if you cannot find reliable hours.'
              % (_safe(name), _safe(addr), lat, lon))
    body = {'contents': [{'parts': [{'text': prompt}]}], 'tools': [{'google_search': {}}],
            'generationConfig': {'maxOutputTokens': 4096}}
    try:
        async with httpx.AsyncClient(timeout=40) as c:
            r = await c.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                             headers={'x-goog-api-key': key}, json=body)
        r.raise_for_status()
        text = ' \n'.join(p.get('text', '') for p in r.json()['candidates'][0]['content'].get('parts', []))
    except Exception:
        return {'oh': None, 'note': 'Web lookup is unavailable right now.'}
    out = {'oh': clean_hours(text), 'note': None if clean_hours(text) else 'No reliable hours found online.'}
    _cache[ck] = out
    return out
