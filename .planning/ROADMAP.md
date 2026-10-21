# Roadmap — ristruttura-stima

**Milestone attiva:** v3.0 — computo parametrico (fase 11).

**Regola di numerazione GSD:** le fasi non ripartono da 01 a ogni milestone. La v1 ha usato
01–04, la v2 05–10; la prossima parte da **11**.

## Milestones

- ✅ **v1.0 MVP** — fasi 01–04 (shipped 2026-09-09, in produzione)
- ✅ **v2.0 domande e motore parametrico** — fasi 05–10 (completata 2026-10-01, push in attesa)
- 🚧 **v3.0 computo parametrico** — fase 11 (aperta 2026-10-21)

## Phases

<details>
<summary><strong>✅ Milestone v1.0 — MVP (fasi 01–04, 30 piani) — SHIPPED 2026-09-09</strong></summary>

Dal computo Excel di Reggio Emilia a una stima self-service a range: quattro categorie, IVA
differenziata, extra, account con Google, PDF brandizzato Free e Pro, lead al professionista,
pannello admin completo. In produzione dal 2026-09-09 (backend su Render, frontend su Vercel).

| Fase | Nome | Piani | Requisiti |
|------|------|-------|-----------|
| 01 | Stima Free end-to-end | 4/4 | EST-01..06, ENG-01..03 |
| 02 | Account & PDF | 9/9 | AUTH-01..04, PDF-01 |
| 03 | Pro & dettaglio sottocategorie | 6/6 | PRO-01..03, PDF-02 |
| 04 | Lead & pannello admin | 11/11 | LEAD-01..03, ADM-01..04 |

Dettaglio completo, decisioni chiave e debito tecnico ereditato:
[`.planning/milestones/v1.0-ROADMAP.md`](milestones/v1.0-ROADMAP.md).
Requisiti archiviati: [`.planning/milestones/v1.0-REQUIREMENTS.md`](milestones/v1.0-REQUIREMENTS.md).

</details>

<details>
<summary><strong>✅ Milestone v2.0 — domande e motore parametrico (fasi 05–10, 53 piani) — COMPLETATA 2026-10-01</strong></summary>

La stima risponde a com'e' fatta la casa e cosa si vuole farci: catalogo domande, opzioni ed
effetti come dati curabili dal pannello e da Excel, wizard unico, arredo, configuratore Pro
senza alternative sommate, risultato leggibile con budget. Audit `passed` 30/30. **Non ancora
in produzione**: il push e' in attesa dei passi elencati in `STATE.md`.

| Fase | Nome | Piani | Requisiti |
|------|------|-------|-----------|
| 05 | Catalogo domande + motore Free parametrico | 1/1 (retro) | QST-01..04, PAR-01..03, PAR-05 |
| 06 | Wizard unico, domande servite dal DB | 1/1 (retro) | WIZ-01..03 |
| 07 | Arredo | 1/1 | ARR-01..04 |
| 08 | Export/import Excel dal pannello admin | 8/8 | CUR-01..04, PAR-04 |
| 08.1 | Catalogo domande: pagina CRUD e file Excel | 6/6 | CUR-01..02 |
| 09 | Configuratore Pro e chiusura del bug dei cataloghi | 14/14 | QST-05, CFG-01..04, WIZ-04 |
| 10 | Risultato leggibile e tetto di budget | 24/24 | RIS-01..04 |

Dettaglio completo e debito tecnico:
[`.planning/milestones/v2.0-ROADMAP.md`](milestones/v2.0-ROADMAP.md).
Requisiti archiviati: [`.planning/milestones/v2.0-REQUIREMENTS.md`](milestones/v2.0-REQUIREMENTS.md).

</details>

### 🚧 Milestone v3.0 — computo parametrico (aperta 2026-10-21)

Free e Pro diventano lo stesso computo, guidato da grandezze della casa, interventi (con il tipo
come preset) e una regola di quantità per voce presa dalle colonne T/U del nuovo Excel. Fonte:
[`docs/proposta-computo-parametrico.md`](../docs/proposta-computo-parametrico.md).

| Fase | Nome | Requisiti |
|------|------|-----------|
| 11 | Computo parametrico | GRD-01..03, RGL-01..05, INT-01..03, MOT-01..04, CUR3-01 |

---

## Dopo la v2

Non ancora schedulate: progetti come contenitore di piu' stime · indirizzo e geocoding · AI
come **parser** del testo libero, mai come stimatore · igiene (test runner frontend, `tsc -b`
ufficiale) · debito tecnico della v2.0 elencato nel suo archivio.
