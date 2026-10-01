"""Popola il Postgres di prova con dati utente creati dal codice v1.0 (come in produzione)."""
from fastapi.testclient import TestClient
from app.main import app

def check(r, *ok):
    assert r.status_code in ok, (r.request.url, r.status_code, r.text[:400])
    return r

ids = {}
for email, nome in [("free@renovio-prova.it", "Utente Free"), ("pro@renovio-prova.it", "Utente Pro")]:
    c = TestClient(app)
    check(c.post("/api/v1/auth/registrati", json={"email": email, "password": "provaprova1", "nome": nome}), 201)
    if email.startswith("pro"):
        check(c.post("/api/v1/me/pro/attiva"), 200)
    for mq, tipo in [(85, "totale"), (60, "leggera"), (120, "moderata")]:
        s = check(c.post("/api/v1/stima", json={"citta": "Reggio Emilia", "mq": mq, "tipo": tipo}), 200).json()
        snap = {k: s[k] for k in ("input", "fallback", "disclaimer", "valuta", "categorie", "extra", "totale", "bonus") if k in s}
        sid = check(c.post("/api/v1/me/stime", json=snap), 201).json()["id"]
        ids.setdefault(email, []).append(sid)
        if email.startswith("pro"):
            check(c.get(f"/api/v1/me/stime/{sid}/dettaglio-pro"), 200)
            check(c.post(f"/api/v1/me/stime/{sid}/dettaglio-pro/risposte",
                         json={"bagni": 2, "porte": 6, "condizionatori": 3}), 200)
    # stima in un comune senza listino (fallback)
    s = check(c.post("/api/v1/stima", json={"citta": "Modena", "mq": 70, "tipo": "moderata"}), 200).json()
    snap = {k: s[k] for k in ("input", "fallback", "disclaimer", "valuta", "categorie", "extra", "totale", "bonus") if k in s}
    check(c.post("/api/v1/me/stime", json=snap), 201)
    t = s["totale"]
    check(c.post("/api/v1/lead", json={"nome": nome, "email": email, "preferenza_contatto": "email",
        "citta": "Modena", "mq": 70, "tipo": "moderata", "totale_min": t["totale_min"], "totale_max": t["totale_max"]}), 201)
print("ok", ids)
