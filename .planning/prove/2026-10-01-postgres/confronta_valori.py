import sys
from decimal import Decimal
from sqlalchemy import create_engine, inspect, text
pg = create_engine("postgresql+psycopg://postgres@127.0.0.1:55432/renovio_prova")
sq = create_engine(sys.argv[1])
SKIP = {"id", "created_at", "updated_at"}
UTENTE = {"lead", "stima", "subscription", "user", "user_session", "alembic_version", "export_log", "avatar_blob", "password_reset_token"}
import datetime
def norm(v):
    if isinstance(v, (datetime.date, datetime.datetime)): return v.isoformat()[:10]
    if isinstance(v, (float, Decimal)): return round(float(v), 6)
    if isinstance(v, str):
        try: return round(float(v), 6)
        except ValueError: return v
    return v
tot = 0
for t in sorted(set(inspect(pg).get_table_names()) - UTENTE):
    cols = [c["name"] for c in inspect(pg).get_columns(t) if c["name"] not in SKIP and not c["name"].endswith("_id")]
    q = text("select " + ",".join(f'"{c}"' for c in cols) + f' from "{t}"')
    def rows(e):
        with e.connect() as c: return sorted((tuple(norm(x) for x in r) for r in c.execute(q)), key=repr)
    a, b = rows(pg), rows(sq)
    if a != b:
        tot += 1
        sa, sb = set(a), set(b)
        print(f"{t}: {len(sa - sb)} righe solo su pg, {len(sb - sa)} solo su fresh")
        for r in list(sa - sb)[:3]: print("   pg   ", dict(zip(cols, r)))
        for r in list(sb - sa)[:3]: print("   fresh", dict(zip(cols, r)))
print("tabelle con valori diversi:", tot)
