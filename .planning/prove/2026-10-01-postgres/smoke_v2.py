"""Prova funzionale della v2 sul Postgres migrato dalla v1 (dati creati dalla v1.0)."""
import json, sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from app.main import app

ESITI = []
def ok(nome, cond, info=""):
    ESITI.append((nome, bool(cond)))
    print(("PASS " if cond else "FAIL ") + nome + (f"  [{info}]" if info and not cond else ""))
def leak(obj):
    s = json.dumps(obj).lower()
    return [k for k in ("impresa", "coefficiente", "effett") if f'"{k}' in s or k + '"' in s]

pg = create_engine("postgresql+psycopg://postgres@127.0.0.1:55432/renovio_prova")
def login(email):
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"email": email, "password": "provaprova1"})
    ok(f"login v1 {email}", r.status_code == 200, r.text[:200])
    return c

free, pro = login("free@renovio-prova.it"), login("pro@renovio-prova.it")
ok("utente Pro resta Pro", pro.get("/api/v1/auth/me").json().get("pro") is True, pro.get("/api/v1/auth/me").text[:200])

# 1. Stime salvate dalla v1: lista, apertura, PDF (route), dettaglio Pro
for nome, c in [("free", free), ("pro", pro)]:
    lst = c.get("/api/v1/me/stime"); ok(f"lista stime v1 ({nome})", lst.status_code == 200 and len(lst.json()) == 4, lst.text[:200])
    for it in lst.json():
        r = c.get(f"/api/v1/me/stime/{it['id']}")
        ok(f"apri stima v1 #{it['id']} ({nome})", r.status_code == 200 and not leak(r.json()), r.text[:200])
for it in pro.get("/api/v1/me/stime").json():
    r = pro.get(f"/api/v1/me/stime/{it['id']}/dettaglio-pro")
    ok(f"dettaglio Pro su stima v1 #{it['id']}", r.status_code == 200 and not leak(r.json()), r.text[:300])
r = free.get(f"/api/v1/me/stime/{free.get('/api/v1/me/stime').json()[0]['id']}/dettaglio-pro")
ok("dettaglio Pro negato al Free", r.status_code in (401, 402, 403), r.status_code)

# 2. Nuovo percorso v2: wizard con risposte, finiture Alte, arredo
risposte = {"livello_finiture": "alto", "bagni": 2, "porte": 7, "ambienti_arredo": ["cucina", "soggiorno"], "tipo_immobile": "appartamento"}
s = pro.post("/api/v1/stima", json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale", "risposte": risposte})
if s.status_code == 422:
    risposte.pop("tipo_immobile"); s = pro.post("/api/v1/stima", json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale", "risposte": risposte})
ok("POST /stima v2 con risposte", s.status_code == 200 and not leak(s.json()), s.text[:300])
s = s.json(); ok("arredo presente a range", bool(s.get("arredo")), str(s.get("arredo"))[:200])
snap = {k: s[k] for k in ("input", "fallback", "disclaimer", "valuta", "categorie", "extra", "totale", "bonus", "arredo") if k in s}
cr = pro.post("/api/v1/me/stime", json={**snap, "budget_eur": 60000}); ok("salva stima v2 con budget", cr.status_code == 201, cr.text[:300])
sid = cr.json()["id"]
d = pro.get(f"/api/v1/me/stime/{sid}/dettaglio-pro"); dj = d.json()
ok("dettaglio Pro stima v2", d.status_code == 200 and not leak(dj), d.text[:300])
ok("M2 su Postgres: finiture Alte -> livelli 'alto'", "alto" in json.dumps(dj.get("livelli") or dj.get("livelli_applicati") or dj), json.dumps(dj)[:300])
r = pro.post(f"/api/v1/me/stime/{sid}/dettaglio-pro/risposte", json={"risposte": {"tipo_pavimento": "parquet", "bagni": 3}, "livelli": {"B-FINITURE": "medio"}})
ok("ricalcolo Pro (parquet, bagni 3, B medio)", r.status_code == 200 and not leak(r.json()), r.text[:300])
r = pro.patch(f"/api/v1/me/stime/{sid}/budget", json={"budget_eur": 50000}); ok("PATCH budget", r.status_code == 200, r.text[:200])
ok("riapertura: budget persistito", pro.get(f"/api/v1/me/stime/{sid}").json().get("budget_eur") == 50000)

# 3. WR-06 su Postgres: PUT con input non valido -> 422 e riga invariata
prima = pro.get(f"/api/v1/me/stime/{sid}").json()
for etichetta, mod in [("mq 0", {"mq": 0}), ("mq -5", {"mq": -5}), ("mq 2001", {"mq": 2001}), ("mq 2^31", {"mq": 2**31}),
                       ("citta vuota", {"citta": ""}), ("citta 101", {"citta": "x" * 101})]:
    body = json.loads(json.dumps(snap)); body["input"].update(mod)
    r = pro.put(f"/api/v1/me/stime/{sid}", json=body)
    ok(f"WR-06 PUT {etichetta} -> 422", r.status_code == 422, f"{r.status_code} {r.text[:150]}")
dopo = pro.get(f"/api/v1/me/stime/{sid}").json()
ok("WR-06 riga invariata dopo i 422", prima == dopo)
body = json.loads(json.dumps(snap)); body["input"]["mq"] = 2000
r = pro.put(f"/api/v1/me/stime/{sid}", json=body); ok("PUT valido mq 2000 -> 200", r.status_code == 200, r.text[:200])
body["input"]["mq"] = 0
r = pro.post("/api/v1/me/stime", json=body); ok("WR-06 POST mq 0 -> 422", r.status_code == 422, r.status_code)

# 4. Lead nuovo e Free
r = free.post("/api/v1/lead", json={"nome": "Lead v2", "email": "free@renovio-prova.it", "preferenza_contatto": "telefono", "telefono": "3330000000",
    "citta": "Reggio Emilia", "mq": 85, "tipo": "totale", "totale_min": 1, "totale_max": 2})
ok("lead v2", r.status_code == 201, r.text[:200])
r = free.post("/api/v1/stima", json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"})
t = r.json()["totale"]
ok("oracolo Free 85 m2 totale RE = 47.985-70.575", (round(float(t["totale_min"])), round(float(t["totale_max"]))) == (47985, 70575), t)

# 5. Admin su Postgres (export Excel e export_log)
with pg.begin() as cx: cx.execute(text("update \"user\" set role='admin' where email='pro@renovio-prova.it'"))
paths = [p for p, ops in app.openapi()["paths"].items() if "/admin/" in p and "get" in ops and "{" not in p]
bad = []
for p in paths:
    r = pro.get(p)
    if r.status_code >= 500: bad.append((p, r.status_code))
ok(f"GET admin senza 500 ({len(paths)} route)", not bad, bad)
with pg.connect() as cx: n = cx.execute(text("select count(*) from export_log")).scalar()
ok("export tracciati in export_log", n > 0, n)
with pg.begin() as cx: cx.execute(text("update \"user\" set role='user' where email='pro@renovio-prova.it'"))

f = sum(not e for _, e in ESITI); print(f"\n{len(ESITI)-f}/{len(ESITI)} PASS"); sys.exit(1 if f else 0)
