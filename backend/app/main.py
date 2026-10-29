import collections, os, time
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import hours, nlp, places, planner, store, webhours

app = FastAPI(title='Wayfarer 2.1')
HITS = collections.defaultdict(collections.deque)


@app.middleware('http')
async def rate_limit(request: Request, call_next):
    path = request.url.path
    if path.startswith('/api/') and path != '/api/health':
        ip = (request.headers.get('x-forwarded-for') or (request.client.host if request.client else 'x')).split(',')[0].strip()
        if len(HITS) > 5000:
            HITS.clear()
        q, now = HITS[ip], time.time()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= int(os.getenv('WAYFARER_RATE_PER_MIN', '60')):
            return JSONResponse({'detail': 'Too many requests. Please wait a minute.'}, status_code=429)
        q.append(now)
    return await call_next(request)


class Pt(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class CandIn(Pt):
    name: str = Field('', max_length=200)
    oh: str | None = Field(None, max_length=300)


class TaskIn(BaseModel):
    id: str = Field(max_length=40)
    title: str = Field(max_length=120)
    cat: str | None = None
    dur: int = Field(15, ge=1, le=480)
    before: int | None = Field(None, ge=0, le=2880)
    pin: int | None = None
    cands: list[CandIn] = Field(max_length=20)


class PlanReq(BaseModel):
    start: Pt
    now: int = Field(ge=0, le=1440)
    weekday: int = Field(default_factory=lambda: datetime.now().weekday(), ge=0, le=6)
    mode: str = 'car'
    tasks: list[TaskIn] = Field(max_length=12)


class PlaceReq(BaseModel):
    f: list[str] | None = None
    q: str = Field('', max_length=120)
    cat: str = ''
    lat: float
    lon: float
    radius: int = Field(3000, ge=200, le=8000)


class ParseReq(BaseModel):
    text: str = Field(max_length=500)


class HoursReq(BaseModel):
    name: str = Field(max_length=200)
    addr: str = Field('', max_length=200)
    lat: float
    lon: float


class EventReq(BaseModel):
    kind: str
    cat: str | None = None
    dwell: int | None = None


@app.get('/api/health')
def health():
    return {'ok': True, 'gemini': bool(os.getenv('GEMINI_API_KEY') and os.getenv('GEMINI_MODEL'))}


@app.post('/api/parse')
async def parse(r: ParseReq):
    tasks, source = await nlp.parse(r.text)
    return {'tasks': tasks, 'source': source}


@app.post('/api/places')
async def find(r: PlaceReq):
    try:
        if r.f:
            return {'cands': await places.search(r.f, r.q, r.cat, r.lat, r.lon, r.radius)}
        return {'cands': await places.search_named(r.q, await nlp.place_queries(r.q), r.lat, r.lon, r.radius)}
    except Exception as e:
        raise HTTPException(502, f'Place search unavailable: {type(e).__name__}')


@app.post('/api/plan')
async def plan(r: PlanReq):
    tasks = []
    for t in r.tasks:
        dur = store.estimate(t.cat, t.dur) if t.cat else t.dur
        cands = [planner.Cand(c.lat, c.lon, c.name, hours.open_intervals(c.oh, r.weekday)) for c in t.cands[:8]]
        tasks.append(planner.Task(t.id, t.title, dur, cands, t.before, t.pin))
    start = (r.start.lat, r.start.lon)
    nodes, _ = planner.build_nodes(r.now, tasks)
    matrix = await places.osrm_table(planner.points(start, nodes), r.mode) if nodes else None
    return planner.plan(start, r.now, tasks, r.mode, matrix)


@app.post('/api/hours')
async def web_hours(r: HoursReq):
    return await webhours.lookup(r.name, r.addr, r.lat, r.lon)


@app.post('/api/event')
def event(r: EventReq):
    if r.kind == 'done' and r.cat and r.dwell:
        store.record(r.cat, r.dwell)
    return {'ok': True}


web = Path(__file__).resolve().parents[2] / 'frontend'
if web.exists():
    app.mount('/', StaticFiles(directory=web, html=True), name='web')
