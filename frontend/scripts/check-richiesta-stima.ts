// Prove senza backend per G12 (10-22). Esecuzione: `node scripts/check-richiesta-stima.ts` da frontend/.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MutationObserver, QueryClient } from "@tanstack/query-core";
import { domandeVisibili, normalizeCatalogo, risposteIniziali } from "../src/lib/domande.ts";
import {
  risposteDopoCatalogo,
  soloVisibili,
  stessaRichiesta,
  azioneSalvataggio,
} from "../src/lib/richiestaStima.ts";

type Risposte = Record<string, number | string | string[]>;

const raw = JSON.parse(
  readFileSync(new URL("./fixtures/catalogo-free-85.json", import.meta.url), "utf-8")
);
const catalogo = normalizeCatalogo(raw);
const defaults = risposteIniziali(catalogo);

function richiesta(risposte: Risposte, extra: Record<string, unknown> = {}) {
  return {
    citta: "Reggio Emilia",
    mq: 85,
    tipo: "totale",
    destinazione: "prima_casa",
    risposte,
    ...extra,
  } as never;
}

// (a) stessaRichiesta ----------------------------------------------------------
{
  const a = richiesta({ ambienti_arredo: ["cucina", "bagno"], bagni: 2 });
  const b = richiesta({ bagni: 2, ambienti_arredo: ["bagno", "cucina"] }, { citta: " Reggio Emilia " });
  assert.equal(stessaRichiesta(a, b), true, "ordine chiavi/array e spazi non contano");
  assert.equal(stessaRichiesta(a, richiesta(a.risposte, { mq: 86 })), false, "mq diverso");
  assert.equal(
    stessaRichiesta(a, richiesta({ ambienti_arredo: ["cucina", "bagno", "camera"], bagni: 2 })),
    false,
    "un ambiente in piu'"
  );
  assert.equal(stessaRichiesta(a, richiesta(a.risposte, { destinazione: "altro" })), false);
  assert.equal(
    stessaRichiesta(richiesta(a.risposte, { destinazione: undefined }), a),
    true,
    "destinazione assente = prima_casa"
  );
}

// (b) giro Modifica col catalogo reale -------------------------------------------
function primoMontaggio(): Risposte {
  // Wizard nuovo: risposte {} -> arriva il catalogo -> default.
  return risposteDopoCatalogo(defaults, {}, new Set(), undefined, true);
}

function sottomissione(risposte: Risposte): Risposte {
  return soloVisibili(risposte, domandeVisibili(catalogo.domande, risposte));
}

function rimontaggio(r: Risposte): Risposte {
  // Wizard rimontato con risposteDiPartenza = r: stato iniziale = r, poi il catalogo.
  const toccate = new Set<string>();
  const dopo = risposteDopoCatalogo(defaults, r, toccate, r, true);
  return sottomissione(dopo);
}

const utente = primoMontaggio();
utente.ambienti_arredo = ["cucina", "bagno"];
utente.muri_lavori = "si";
utente.muri_da_recuperare = 4;
utente.muri_da_rifare_mq = 12;
utente.bagni = 2;
utente.impianti = ["elettrico", "idrico"];
utente.efficientamento = "si";
utente.interventi_efficientamento = ["cappotto_esterno"];
const r1 = sottomissione(utente);
assert.ok("muri_da_recuperare" in r1, "domanda condizionale visibile inviata");
assert.ok(!("classe_energetica_obiettivo" in r1) === false, "gate energia aperto");

const r2 = rimontaggio(r1);
assert.deepEqual(
  new Set(Object.keys(r2)),
  new Set(Object.keys(r1)),
  "stesse chiavi dopo il rimontaggio"
);
assert.equal(stessaRichiesta(richiesta(r1), richiesta(r2)), true, "giro Modifica: richiesta identica");
assert.equal(
  stessaRichiesta(richiesta(r1), richiesta(rimontaggio(r2))),
  true,
  "secondo giro Modifica: ancora identica"
);

// Regressione G12: tutti i default, nessuna scelta (caso 'Modifica senza cambiare nulla').
{
  const soloDefault = sottomissione(primoMontaggio());
  assert.equal(
    stessaRichiesta(richiesta(soloDefault), richiesta(rimontaggio(soloDefault))),
    true,
    "regressione G12: giro Modifica sui soli default"
  );
}

// Regressione G12: scelta multipla svuotata dall'utente ([] non e' un default).
{
  const u = primoMontaggio();
  u.ambienti_arredo = ["cucina"];
  u.ambienti_arredo = [];
  const s1 = sottomissione(u);
  assert.equal(stessaRichiesta(richiesta(s1), richiesta(rimontaggio(s1))), true, "[] svuotato");
}

// (c) Meccanismo della race: TanStack Query v5, callback per-call dopo reset() ---
async function attesa(ms: number) {
  await new Promise((r) => setTimeout(r, ms));
}

{
  const client = new QueryClient();
  const chiamate = { perCall: 0, opzioni: 0 };
  const observer = new MutationObserver(client, {
    mutationFn: async (_: string) => {
      await attesa(30);
      return { id: 1 };
    },
    onSuccess: () => {
      chiamate.opzioni += 1;
    },
  });
  observer.subscribe(() => {});

  // Senza reset il callback per-call parte.
  observer.mutate("x", { onSuccess: () => (chiamate.perCall += 1) });
  await attesa(80);
  assert.equal(chiamate.perCall, 1, "controllo: senza reset il callback per-call parte");

  // Con reset() mentre il POST e' in volo, il callback per-call NON parte;
  // quello definito nelle opzioni di useMutation parte comunque.
  observer.mutate("y", { onSuccess: () => (chiamate.perCall += 1) });
  observer.reset();
  await attesa(80);
  assert.equal(chiamate.perCall, 1, "G12: reset() in volo perde il callback per-call");
  assert.equal(chiamate.opzioni, 2, "il callback nelle opzioni della mutation parte sempre");
}

// (d) G14: PUT vs POST vs attesa ---
{
  const base = { stimaInModifica: true, idEsistente: 7, postInVolo: false };
  assert.equal(azioneSalvataggio(base), "put", "dopo Modifica con id: PUT");
  assert.equal(azioneSalvataggio({ ...base, postInVolo: true }), "put", "con id il POST in volo non conta");
  assert.equal(
    azioneSalvataggio({ stimaInModifica: false, idEsistente: null, postInVolo: false }),
    "post",
    "stima da zero: POST"
  );
  assert.equal(
    azioneSalvataggio({ stimaInModifica: false, idEsistente: 7, postInVolo: false }),
    "post",
    "senza Modifica si ignora un id vecchio: POST"
  );
  assert.equal(
    azioneSalvataggio({ stimaInModifica: true, idEsistente: null, postInVolo: true }),
    "attendi",
    "Modifica con primo POST in volo: attendi"
  );
  assert.equal(
    azioneSalvataggio({ stimaInModifica: true, idEsistente: null, postInVolo: false }),
    "post",
    "Modifica ma primo POST fallito: ripiego sul POST"
  );
  assert.equal(
    azioneSalvataggio({ ...base, putInVolo: true }),
    "attendi",
    "WR-01: PUT gia' in volo sulla stessa stima: attendi, mai due PUT paralleli"
  );
  assert.equal(
    azioneSalvataggio({ ...base, putInVolo: false }),
    "put",
    "WR-01: PUT precedente concluso: PUT"
  );
  assert.equal(
    azioneSalvataggio({ stimaInModifica: false, idEsistente: null, postInVolo: false, putInVolo: true }),
    "post",
    "senza Modifica un PUT in volo non blocca il POST di una stima nuova"
  );
}

console.log("check-richiesta-stima: OK");
