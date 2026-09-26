"""Generatore del file Excel di taratura Pro (D-04/D-08, 09-01-PLAN.md) +
lettore delle decisioni compilate.

Il file riusa `build_workbook_parametri()` (export_excel/parametri.py,
`con_margine=False`): stessi cinque fogli, stesso foglio `ISTRUZIONI` con
timestamp, nessuna colonna di margine, nessun foglio `AVVISO` — regola di
dominio #1 (CLAUDE.md). A quel workbook si aggiungono, SENZA toccare
`COLONNE_COEFF_PRO` di `import_excel/parametri.py` (Pitfall 3 del
09-RESEARCH.md), colonne extra di curatela sul foglio `coefficienti_pro` e
tre fogli nuovi: `assi_proposti`, `dati_richiesti`, `LEGGIMI_TARATURA`. Il
file resta ricaricabile in anteprima da `/admin/import-excel/parametri`
senza scarti: le colonne extra sono ignorate in lettura, i tre fogli nuovi
non fanno parte dei cinque fogli noti al handler `parametri`.

Vincolo di Riccardo del 2026-09-26: le fasi 09 e 10 si eseguono di fila
senza fermarsi sulla sua compilazione. `accetta_bozza()` produce, accanto al
file vero, una bozza accettata in blocco (stato "bozza-accettata") che i
piani successivi (09-06, 09-07) possono leggere via `leggi_decisioni()`
finche' Riccardo non restituisce il file compilato davvero — vedi
`.planning/phases/09-configuratore-pro/09-TARATURA-TODO.md`.
"""

from __future__ import annotations

import argparse
import io
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

# Allow `python scripts/genera_excel_taratura.py` direct execution, stesso
# bootstrap di scripts/seed.py.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import openpyxl  # noqa: E402
from openpyxl.workbook import Workbook  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce  # noqa: E402
from app.services.computo_parsing import proponi_coefficiente  # noqa: E402
from app.services.export_excel.parametri import build_workbook_parametri  # noqa: E402

FOGLIO_COEFF_PRO = "coefficienti_pro"
FOGLIO_ASSI = "assi_proposti"
FOGLIO_DATI = "dati_richiesti"
FOGLIO_LEGGIMI = "LEGGIMI_TARATURA"

STATI_AMMESSI = {"da-compilare", "bozza-accettata", "compilato"}

_AVVISO_BOZZA_ACCETTATA = (
    "FILE NON RIVISTO DA RICCARDO: bozza di Claude accettata in blocco per "
    "non bloccare le fasi 09-10. La taratura vera si fa con "
    "09-TARATURA-TODO.md."
)

_NOTE_BOZZA_ACCETTATA = "bozza accettata automaticamente, non rivista da Riccardo"

COLONNE_COEFF_PRO_EXTRA = [
    "categoria_code",
    "sottocategoria",
    "codice_voce",
    "um",
    "prezzo_unitario_cliente",
    "coefficiente_attuale",
    "default_conteggio_attuale",
    "coefficiente_proposto",
    "default_conteggio_proposto",
    "motivazione",
    "decisione",
    "note",
]

COLONNE_ASSI_PROPOSTI = [
    "voce_id",
    "categoria_code",
    "sottocategoria",
    "codice_voce",
    "descrizione",
    "um",
    "prezzo_unitario_cliente",
    "livello_attuale",
    "asse_proposto",
    "opzione_proposta",
    "valore_per_unita",
    "fattore_quantita",
    "famiglia_alternativa",
    "motivo",
    "decisione",
    "note",
]

COLONNE_DATI_RICHIESTI = [
    "codice_dato",
    "domanda",
    "perche_serve",
    "voci_interessate",
    "valore_proposto_claude",
    "valore_riccardo",
    "note",
]


# --- (a) coefficienti_pro esteso --------------------------------------------


@dataclass(frozen=True)
class VoceTaraturaInfo:
    """Contesto di una voce, letto una sola volta dal DB, riusato sia per
    l'estensione del foglio `coefficienti_pro` sia per `proponi_assegnazione()`."""

    voce_id: int
    categoria_code: str
    sottocategoria_codice: str | None
    sottocategoria_nome: str
    famiglia: str
    codice_voce: str | None
    descrizione: str
    um: str
    prezzo_unitario_cliente: Decimal
    livello_attuale: str | None
    domanda_mirata_key: str | None


def _carica_voci_taratura(db: Session) -> dict[int, VoceTaraturaInfo]:
    righe = (
        db.query(Voce, Sottocategoria)
        .join(Sottocategoria, Voce.sottocategoria_id == Sottocategoria.id)
        .order_by(Voce.id)
        .all()
    )
    # domanda_mirata_key vive su CoefficienteQuantitaVoce, non su Voce: una
    # voce puo' avere piu' righe (una per tipo), la chiave e' la stessa su
    # tutte per costruzione (proponi_coefficiente/coefficienti_per_voce la
    # assegnano per voce, non per tipo) — si prende la prima non nulla.
    chiavi_mirate: dict[int, str] = {}
    for c in db.query(CoefficienteQuantitaVoce).order_by(CoefficienteQuantitaVoce.id).all():
        if c.domanda_mirata_key and c.voce_id not in chiavi_mirate:
            chiavi_mirate[c.voce_id] = c.domanda_mirata_key

    info: dict[int, VoceTaraturaInfo] = {}
    for voce, sotto in righe:
        info[voce.id] = VoceTaraturaInfo(
            voce_id=voce.id,
            categoria_code=sotto.categoria_code,
            sottocategoria_codice=sotto.codice,
            sottocategoria_nome=sotto.nome,
            famiglia=sotto.famiglia,
            codice_voce=voce.codice,
            descrizione=voce.descrizione,
            um=voce.um,
            prezzo_unitario_cliente=voce.prezzo_unitario_cliente,
            livello_attuale=voce.livello,
            domanda_mirata_key=chiavi_mirate.get(voce.id),
        )
    return info


def _estendi_coefficienti_pro(wb: Workbook, db: Session, voci: dict[int, VoceTaraturaInfo]) -> None:
    ws = wb[FOGLIO_COEFF_PRO]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    for colonna in COLONNE_COEFF_PRO_EXTRA:
        header.append(colonna)
    for indice, nome in enumerate(header, start=1):
        ws.cell(row=1, column=indice, value=nome)

    idx = {nome: i for i, nome in enumerate(header)}
    coeff_db = {c.id: c for c in db.query(CoefficienteQuantitaVoce).all()}

    for riga_excel in ws.iter_rows(min_row=2):
        coeff_id = riga_excel[idx["id"]].value
        if coeff_id is None:
            continue
        coeff = coeff_db.get(int(coeff_id))
        if coeff is None:
            continue
        v = voci.get(coeff.voce_id)
        if v is None:
            continue

        proposta = proponi_coefficiente(v.um, v.descrizione, v.sottocategoria_nome, v.categoria_code)
        coeff_proposto, conteggio_proposto = proposta.per_tipo.get(coeff.tipo_code, (None, None))
        motivazione = proposta.motivazione

        if coeff.domanda_mirata_key:
            # La quantita' viene dallo stepper omonimo (bagni/porte/
            # condizionatori): il coefficiente per m2 resta vuoto, il
            # default_conteggio proposto resta quello a DB (nessun
            # cambiamento), la motivazione lo spiega esplicitamente.
            coeff_proposto = None
            conteggio_proposto = coeff.default_conteggio
            motivazione = (
                f"quantita' governata dallo stepper '{coeff.domanda_mirata_key}' "
                "(effetto quantita_per_unita, migrazione 09-02/09-03): il "
                "coefficiente per m2 resta vuoto; default_conteggio vale solo "
                "quando manca sia la risposta dell'utente sia l'atteso per i m2."
            )

        def _riga(nome_colonna: str, valore) -> None:
            riga_excel[idx[nome_colonna]].value = valore

        # Colonne core: coefficiente_qta_per_mq/default_conteggio portano il
        # valore PROPOSTO (round-trip-safe: domanda_mirata_key resta
        # invariata, id/voce_id/tipo_code non si toccano mai).
        _riga("coefficiente_qta_per_mq", float(coeff_proposto) if coeff_proposto is not None else None)
        _riga("default_conteggio", conteggio_proposto)

        # Colonne extra di curatela (ignorate in lettura dall'handler di
        # import: Pitfall 3 09-RESEARCH.md).
        _riga("categoria_code", v.categoria_code)
        _riga("sottocategoria", v.sottocategoria_nome)
        _riga("codice_voce", v.codice_voce)
        _riga("um", v.um)
        _riga("prezzo_unitario_cliente", float(v.prezzo_unitario_cliente))
        _riga(
            "coefficiente_attuale",
            float(coeff.coefficiente_qta_per_mq) if coeff.coefficiente_qta_per_mq is not None else None,
        )
        _riga("default_conteggio_attuale", coeff.default_conteggio)
        _riga("coefficiente_proposto", float(coeff_proposto) if coeff_proposto is not None else None)
        _riga("default_conteggio_proposto", conteggio_proposto)
        _riga("motivazione", motivazione)
        _riga("decisione", None)
        _riga("note", None)


# --- (b) assi_proposti -------------------------------------------------------


@dataclass(frozen=True)
class PropostaAsse:
    voce_id: int
    categoria_code: str
    sottocategoria: str
    codice_voce: str | None
    descrizione: str
    um: str
    prezzo_unitario_cliente: Decimal
    livello_attuale: str | None
    asse_proposto: str
    opzione_proposta: str | None
    valore_per_unita: Decimal | None
    fattore_quantita: Decimal | None
    famiglia_alternativa: str
    motivo: str
    decisione: str = ""
    note: str = ""


_MAPPA_A6_TIPO_PAVIMENTO = {
    "A.6.1": "gres",
    "A.6.2": "parquet",
    "A.6.5": "maxi_lastra",
    "A.6.6": "mosaico",
}

# Quota di m2 del bagno sul totale (D-02, dato_richiesto "mq_pavimento_bagno"):
# fattore_quantita proposto per le righe fattore_pavimento su A.6.1.
_FATTORE_BAGNO_PROPOSTO = Decimal("0.12")

_FAMIGLIE_ALTERNATIVE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("sanitari_vaso", ("vaso igienico",)),
    ("sanitari_bidet", ("bidet",)),
    ("sanitari_cassetta", ("cassetta d",)),
    ("sanitari_doccia_vasca", ("piatto doccia", "vasca in acrilico", "cabina per piatto doccia")),
    ("porte_apertura", ("tamburata", "scorrevole")),
    ("condizionatori_marca", ("condizionatore",)),
)


def _famiglia_alternativa_di(v: VoceTaraturaInfo) -> str | None:
    testo = v.descrizione.lower()
    for nome, keywords in _FAMIGLIE_ALTERNATIVE_KEYWORDS:
        if any(kw in testo for kw in keywords):
            return nome
    return None


def _righe_famiglie_alternative(voci: list[VoceTaraturaInfo]) -> list[PropostaAsse]:
    """Alternative della stessa famiglia (vaso a terra/sospeso, bidet,
    cassetta 9L x2, piatto doccia/vasca, porte tamburate/scorrevoli,
    condizionatori per marca) -> finitura base/medio/alto sulla voce piu'
    economica / intermedia / piu' cara della famiglia; eccedenze -> escludi_sempre."""
    gruppi: dict[str, list[VoceTaraturaInfo]] = {}
    for v in voci:
        famiglia = _famiglia_alternativa_di(v)
        if famiglia is not None:
            gruppi.setdefault(famiglia, []).append(v)

    righe: list[PropostaAsse] = []
    for famiglia, membri in gruppi.items():
        ordinati = sorted(membri, key=lambda v: v.prezzo_unitario_cliente)
        n = len(ordinati)
        tier_per_voce_id: dict[int, str] = {ordinati[0].voce_id: "base"}
        if n >= 2:
            tier_per_voce_id[ordinati[-1].voce_id] = "alto"
        if n >= 3:
            tier_per_voce_id[ordinati[n // 2].voce_id] = "medio"

        for v in ordinati:
            opzione = tier_per_voce_id.get(v.voce_id)
            if opzione is not None:
                motivo = (
                    f"famiglia di alternative '{famiglia}': prezzo cliente "
                    f"{v.prezzo_unitario_cliente} -> livello '{opzione}' per "
                    "posizione nella fascia di prezzo della famiglia (D-08, "
                    "bozza da confermare)."
                )
                asse_proposto = "finitura"
            else:
                motivo = (
                    f"famiglia di alternative '{famiglia}': eccedenza rispetto "
                    "ai tre livelli base/medio/alto, esclusa di default dal "
                    "computo (D-08, bozza da confermare)."
                )
                asse_proposto = "escludi_sempre"
            righe.append(
                PropostaAsse(
                    voce_id=v.voce_id,
                    categoria_code=v.categoria_code,
                    sottocategoria=v.sottocategoria_nome,
                    codice_voce=v.codice_voce,
                    descrizione=v.descrizione,
                    um=v.um,
                    prezzo_unitario_cliente=v.prezzo_unitario_cliente,
                    livello_attuale=v.livello_attuale,
                    asse_proposto=asse_proposto,
                    opzione_proposta=opzione,
                    valore_per_unita=None,
                    fattore_quantita=None,
                    famiglia_alternativa=famiglia,
                    motivo=motivo,
                )
            )
    return righe


def proponi_assegnazione(voci: list[VoceTaraturaInfo]) -> list[PropostaAsse]:
    """Pura: nessun accesso a DB. Propone l'assegnazione delle voci agli
    assi (finitura / tipo_pavimento / stepper) con una colonna motivo,
    seguendo le regole di partenza dell'azione del Task 2 (09-01-PLAN.md)."""
    righe: list[PropostaAsse] = []
    coperte: set[int] = set()

    def _aggiungi(v: VoceTaraturaInfo, **kwargs) -> None:
        righe.append(
            PropostaAsse(
                voce_id=v.voce_id,
                categoria_code=v.categoria_code,
                sottocategoria=v.sottocategoria_nome,
                codice_voce=v.codice_voce,
                descrizione=v.descrizione,
                um=v.um,
                prezzo_unitario_cliente=v.prezzo_unitario_cliente,
                livello_attuale=v.livello_attuale,
                valore_per_unita=None,
                fattore_quantita=None,
                **kwargs,
            )
        )
        coperte.add(v.voce_id)

    # 1) livello_attuale valorizzato -> asse finitura.
    for v in voci:
        if v.livello_attuale:
            _aggiungi(
                v,
                asse_proposto="finitura",
                opzione_proposta=v.livello_attuale,
                famiglia_alternativa=f"finitura:{v.sottocategoria_nome}",
                motivo=(
                    f"livello curato a DB ('{v.livello_attuale}') migrato "
                    "all'asse finitura senza cambiare l'esito (CFG-03: "
                    "migrazione senza perdita)."
                ),
            )

    # 2) A.6.1/A.6.2/A.6.5/A.6.6 -> asse tipo_pavimento; A.6.1 riceve anche
    #    la riga fattore_pavimento (D-02: il bagno resta sempre gres).
    for v in voci:
        if v.codice_voce in _MAPPA_A6_TIPO_PAVIMENTO:
            opzione = _MAPPA_A6_TIPO_PAVIMENTO[v.codice_voce]
            _aggiungi(
                v,
                asse_proposto="tipo_pavimento",
                opzione_proposta=opzione,
                famiglia_alternativa="posa_pavimento_A6",
                motivo=f"posa A.6 alternativa: governata dall'opzione '{opzione}' dell'asse tipo_pavimento.",
            )
            if v.codice_voce == "A.6.1":
                for altra_opzione in ("parquet", "maxi_lastra", "mosaico"):
                    righe.append(
                        PropostaAsse(
                            voce_id=v.voce_id,
                            categoria_code=v.categoria_code,
                            sottocategoria=v.sottocategoria_nome,
                            codice_voce=v.codice_voce,
                            descrizione=v.descrizione,
                            um=v.um,
                            prezzo_unitario_cliente=v.prezzo_unitario_cliente,
                            livello_attuale=v.livello_attuale,
                            asse_proposto="fattore_pavimento",
                            opzione_proposta=altra_opzione,
                            valore_per_unita=None,
                            fattore_quantita=_FATTORE_BAGNO_PROPOSTO,
                            famiglia_alternativa="posa_pavimento_A6",
                            motivo=(
                                "D-02: il bagno resta sempre gres/rivestimento a "
                                "prescindere dalla scelta del pavimento del resto "
                                f"della casa; fattore_quantita {_FATTORE_BAGNO_PROPOSTO} "
                                "stima la quota di m2 di posa gres del bagno quando "
                                f"e' scelta l'opzione '{altra_opzione}' (dato_richiesto "
                                "mq_pavimento_bagno)."
                            ),
                        )
                    )

    # 3) Sottocategoria PAVIMENTI PARQUET -> tipo_pavimento parquet.
    for v in voci:
        if v.sottocategoria_nome == "PAVIMENTI PARQUET":
            _aggiungi(
                v,
                asse_proposto="tipo_pavimento",
                opzione_proposta="parquet",
                famiglia_alternativa="fornitura_pavimento_parquet",
                motivo="fornitura coerente con la posa parquet A.6.2 dell'asse tipo_pavimento.",
            )

    # 4) Tesserine/mosaico, lastre di bassissimo spessore, battiscopa.
    for v in voci:
        if v.voce_id in coperte:
            continue
        testo = v.descrizione.lower()
        if "tesserine" in testo or "mosaico" in testo:
            _aggiungi(
                v,
                asse_proposto="tipo_pavimento",
                opzione_proposta="mosaico",
                famiglia_alternativa="fornitura_pavimento_mosaico",
                motivo="fornitura coerente con la posa a mosaico A.6.6 dell'asse tipo_pavimento.",
            )
        elif "bassissimo spessore" in testo:
            _aggiungi(
                v,
                asse_proposto="tipo_pavimento",
                opzione_proposta="maxi_lastra",
                famiglia_alternativa="fornitura_pavimento_maxi_lastra",
                motivo="fornitura coerente con la posa MAXI LASTRA A.6.5 dell'asse tipo_pavimento.",
            )
        elif v.sottocategoria_nome == "BATTISCOPA":
            if "legno" in testo:
                _aggiungi(
                    v,
                    asse_proposto="tipo_pavimento",
                    opzione_proposta="parquet",
                    famiglia_alternativa="battiscopa",
                    motivo="battiscopa in legno coerente con il pavimento parquet.",
                )
            elif "gres" in testo or "ceramica" in testo:
                _aggiungi(
                    v,
                    asse_proposto="tipo_pavimento",
                    opzione_proposta="gres",
                    famiglia_alternativa="battiscopa",
                    motivo="battiscopa in gres/ceramica coerente con il pavimento gres.",
                )

    # 5) Voci con domanda_mirata_key -> lo stepper omonimo.
    for v in voci:
        if v.domanda_mirata_key:
            righe.append(
                PropostaAsse(
                    voce_id=v.voce_id,
                    categoria_code=v.categoria_code,
                    sottocategoria=v.sottocategoria_nome,
                    codice_voce=v.codice_voce,
                    descrizione=v.descrizione,
                    um=v.um,
                    prezzo_unitario_cliente=v.prezzo_unitario_cliente,
                    livello_attuale=v.livello_attuale,
                    asse_proposto=v.domanda_mirata_key,
                    opzione_proposta=None,
                    valore_per_unita=Decimal("1"),
                    fattore_quantita=None,
                    famiglia_alternativa=f"stepper_{v.domanda_mirata_key}",
                    motivo=(
                        f"quantita' governata dallo stepper '{v.domanda_mirata_key}' "
                        "(migrazione QST-05: da domanda_mirata_key a Domanda "
                        "stepper con effetto quantita_per_unita=1)."
                    ),
                )
            )
            coperte.add(v.voce_id)

    # 6) Famiglie di alternative (finitura base/medio/alto per fascia di prezzo).
    righe_famiglie = _righe_famiglie_alternative(voci)
    for r in righe_famiglie:
        coperte.add(r.voce_id)
    righe.extend(righe_famiglie)

    # 7) Voci comuni non governate da alcun asse -> sempre_inclusa.
    for v in voci:
        if v.famiglia == "catalogo" and v.voce_id not in coperte:
            _aggiungi(
                v,
                asse_proposto="sempre_inclusa",
                opzione_proposta=None,
                famiglia_alternativa="comune",
                motivo=(
                    "voce comune non governata da alcun asse nel perimetro "
                    "D-01 di questa fase: resta sempre inclusa nel computo "
                    "(materiali di posa, montaggi, accessori)."
                ),
            )

    return righe


def _scrivi_assi_proposti(wb: Workbook, righe: list[PropostaAsse]) -> None:
    ws = wb.create_sheet(FOGLIO_ASSI)
    ws.append(list(COLONNE_ASSI_PROPOSTI))
    for r in righe:
        ws.append(
            [
                r.voce_id,
                r.categoria_code,
                r.sottocategoria,
                r.codice_voce,
                r.descrizione,
                r.um,
                float(r.prezzo_unitario_cliente),
                r.livello_attuale,
                r.asse_proposto,
                r.opzione_proposta,
                float(r.valore_per_unita) if r.valore_per_unita is not None else None,
                float(r.fattore_quantita) if r.fattore_quantita is not None else None,
                r.famiglia_alternativa,
                r.motivo,
                r.decisione,
                r.note,
            ]
        )


# --- (c) dati_richiesti ------------------------------------------------------

DATI_RICHIESTI_PROPOSTI: list[dict[str, str]] = [
    {
        "codice_dato": "quota_calpestabile",
        "domanda": "Quale quota dei m2 commerciali dell'appartamento e' davvero calpestabile/pavimentabile?",
        "perche_serve": "e' il coefficiente della classe 'pavimento' (0.85 proposto per il tipo totale)",
        "voci_interessate": "A.6.1 (posa pavimentazione), forniture B-FINITURE pavimenti/parquet/gres",
        "valore_proposto_claude": "0.85",
    },
    {
        "codice_dato": "mq_pavimento_bagno",
        "domanda": "Quanti m2 medi di pavimento ha un bagno tipo, come quota sul totale dell'appartamento?",
        "perche_serve": "fattore_quantita delle righe fattore_pavimento su A.6.1 (D-02: il bagno resta sempre gres)",
        "voci_interessate": "A.6.1, foglio assi_proposti righe fattore_pavimento",
        "valore_proposto_claude": "0.12",
    },
    {
        "codice_dato": "mq_rivestimento_bagno",
        "domanda": "Quanti m2 di rivestimento a parete ha un bagno tipo (altezza x perimetro)?",
        "perche_serve": "coefficiente della classe 'rivestimento' (0.25 proposto per il tipo totale, fallback senza numero di bagni)",
        "voci_interessate": "A.6.3, A.6.4 (posa rivestimenti)",
        "valore_proposto_claude": "circa 20 m2 per bagno su un appartamento di riferimento di 85 m2",
    },
    {
        "codice_dato": "rivestimento_cucina",
        "domanda": "La cucina ha un rivestimento a parete da conteggiare separatamente? Se si', quanti m2?",
        "perche_serve": "oggi ignorato: nessuna voce/coefficiente distingue il rivestimento cucina da quello del bagno",
        "voci_interessate": "A.6.3, A.6.4 (posa rivestimenti)",
        "valore_proposto_claude": "nessuno, ignorato in questa bozza",
    },
    {
        "codice_dato": "ml_battiscopa_per_mq",
        "domanda": "Quanti ml di battiscopa ci sono per m2 di pavimento in un appartamento tipo?",
        "perche_serve": "coefficiente della classe 'battiscopa' (0.9 ml/m2 proposto per il tipo totale)",
        "voci_interessate": "A.6.7, A.6.8, sottocategoria BATTISCOPA",
        "valore_proposto_claude": "0.9",
    },
    {
        "codice_dato": "quota_massetto",
        "domanda": "Quale quota dei m2 viene rifatta a massetto, per tipo di intervento (leggera/moderata/totale)?",
        "perche_serve": "coefficiente della classe 'massetto' (0.85 proposto per il tipo totale)",
        "voci_interessate": "A.2 MASSETTI",
        "valore_proposto_claude": "0.85 per il tipo totale (0.34/0.595 per leggera/moderata via TIPO_FACTOR)",
    },
    {
        "codice_dato": "mq_pareti_soffitti_per_mq",
        "domanda": "Quanti m2 di pareti+soffitto ci sono per m2 di pavimento in un appartamento tipo?",
        "perche_serve": "coefficiente della classe 'pareti_soffitti' (2.7 proposto per il tipo totale)",
        "voci_interessate": "A.4 INTONACI, A.11 OPERE DA PITTORE",
        "valore_proposto_claude": "2.7",
    },
    {
        "codice_dato": "quota_demolizioni",
        "domanda": "Quale quota dei m2 viene demolita/rimossa, per tipo di intervento?",
        "perche_serve": "coefficiente della classe 'demolizione' (0.5 proposto per il tipo totale)",
        "voci_interessate": "A.1 DEMOLIZIONI - RIMOZIONI - TRASPORTO",
        "valore_proposto_claude": "0.5 per il tipo totale",
    },
    {
        "codice_dato": "mq_controsoffitto",
        "domanda": "Quanti m2 di controsoffitto per m2 di pavimento, quando presente?",
        "perche_serve": "oggi nessuna classe dedicata: rientra nella bozza generica 'altro_mq' (0.4)",
        "voci_interessate": "A.5 CONTROSOFFITTI e SOPPALCHI",
        "valore_proposto_claude": "0.4 (bozza generica altro_mq, da confermare)",
    },
    {
        "codice_dato": "superficie_finestrata",
        "domanda": "Quanti m2 di superficie finestrata (finestre + porte finestra) per m2 dell'appartamento?",
        "perche_serve": "coefficiente della classe 'serramento_mq' (0.12 proposto per il tipo totale)",
        "voci_interessate": "finestre, porte finestra, tapparelle, zanzariere (C-SERRAMENTI)",
        "valore_proposto_claude": "0.12",
    },
    {
        "codice_dato": "ml_cassonetti_per_mq",
        "domanda": "Quanti ml di cassonetti tapparelle per m2 dell'appartamento?",
        "perche_serve": "oggi nessuna classe dedicata: rientra nella bozza generica 'lineare' (0.3)",
        "voci_interessate": "cassonetti coibentati (C-SERRAMENTI)",
        "valore_proposto_claude": "0.3 (bozza generica lineare, da confermare)",
    },
    {
        "codice_dato": "radiatori_per_locale",
        "domanda": "I radiatori/scaldasalviette si contano per m2 o per locale? Quanti in un bagno tipo?",
        "perche_serve": "oggi solo un default_conteggio bozza (1, o 2 per radiatori/termosifoni), nessuna regola per m2/locale",
        "voci_interessate": "radiatori e scaldasalviette (RUBINETTERIE/PRODOTTI)",
        "valore_proposto_claude": "default_conteggio 1 (2 per radiatori/termosifoni)",
    },
    {
        "codice_dato": "punti_impianto_per_mq",
        "domanda": "I punti impianto (A.8 IMPIANTI, A.10 MONTAGGI E ALLACCI) si contano per m2 o per locale?",
        "perche_serve": "oggi solo un default_conteggio forfait generico (0/1/2 per tipo leggera/moderata/totale)",
        "voci_interessate": "A.8 IMPIANTI, A.10 MONTAGGI E ALLACCI",
        "valore_proposto_claude": "default_conteggio 0/1/2 per leggera/moderata/totale",
    },
    {
        "codice_dato": "scala_tipo_factor",
        "domanda": "La scala leggera 0.4 / moderata 0.7 / totale 1.0 e' quella giusta per far crescere ogni coefficiente con l'intensita' dell'intervento?",
        "perche_serve": "TIPO_FACTOR e' il moltiplicatore comune a ogni coefficiente proposto in questo file",
        "voci_interessate": "tutte le voci a coefficiente_qta_per_mq",
        "valore_proposto_claude": "0.4 / 0.7 / 1.0 (leggera/moderata/totale)",
    },
    {
        "codice_dato": "famiglie_alternative_livelli",
        "domanda": "Per ogni famiglia di alternative (sanitari, porte, condizionatori) quale voce e' base, quale medio, quale alto?",
        "perche_serve": "D-08: l'assegnazione proposta oggi e' per fascia di prezzo cliente, non per un giudizio qualitativo",
        "voci_interessate": "RUBINETTERIE (sanitari), PORTE (C-SERRAMENTI), PRODOTTI (condizionatori)",
        "valore_proposto_claude": "vedi foglio assi_proposti, colonna opzione_proposta per famiglia_alternativa",
    },
]


def _scrivi_dati_richiesti(wb: Workbook, righe: list[dict[str, str]]) -> None:
    ws = wb.create_sheet(FOGLIO_DATI)
    ws.append(list(COLONNE_DATI_RICHIESTI))
    for r in righe:
        ws.append(
            [
                r["codice_dato"],
                r["domanda"],
                r["perche_serve"],
                r["voci_interessate"],
                r["valore_proposto_claude"],
                r.get("valore_riccardo", ""),
                r.get("note", ""),
            ]
        )


# --- (d) LEGGIMI_TARATURA ----------------------------------------------------

_TESTI_LEGGIMI: tuple[tuple[str, str], ...] = (
    (
        "regole_decisione",
        "Foglio coefficienti_pro/assi_proposti, colonna decisione: OK (accetto il "
        "proposto), ATTUALE (tengo il valore attuale a DB), MODIFICATO (ho "
        "scritto io il valore nelle celle coefficiente_qta_per_mq / "
        "default_conteggio, o nelle celle di assi_proposti), NO (solo su "
        "assi_proposti: escludi questa riga dalla proposta).",
    ),
    (
        "regole_non_toccare",
        "Non modificare le colonne id, voce_id, tipo_code: sono le chiavi con cui "
        "il file viene riletto.",
    ),
    (
        "regole_upload",
        "Il file si puo' caricare in anteprima da /admin/parametri per "
        "controllare che non ci siano scarti, ma NON va applicato dal "
        "pannello: lo applica la fase con una migrazione dedicata (piano "
        "09-06, scripts/applica_taratura.py).",
    ),
    (
        "regole_riservatezza",
        "Il file non contiene dati riservati all'impresa: nessuna colonna di "
        "margine, nessun foglio dedicato all'avviso di riservatezza.",
    ),
)


def _scrivi_leggimi_taratura(wb: Workbook, *, stato: str, avviso_testo: str | None = None) -> None:
    if stato not in STATI_AMMESSI:
        raise ValueError(f"stato non riconosciuto: {stato!r}")
    if FOGLIO_LEGGIMI in wb.sheetnames:
        del wb[FOGLIO_LEGGIMI]
    ws = wb.create_sheet(FOGLIO_LEGGIMI)
    ws.append(["sezione", "testo"])
    for sezione, testo in _TESTI_LEGGIMI:
        ws.append([sezione, testo])
    ws.append(["stato", stato])
    if avviso_testo:
        ws.append(["avviso", avviso_testo])


# --- costruzione del workbook completo --------------------------------------


def costruisci_workbook_taratura(db: Session) -> Workbook:
    """Costruisce il workbook di taratura (D-04): i cinque fogli
    dell'export parametri reale (`build_workbook_parametri`, con_margine
    sempre False), il foglio coefficienti_pro esteso con le colonne di
    curatela, e i tre fogli nuovi assi_proposti / dati_richiesti /
    LEGGIMI_TARATURA. Stato iniziale: 'da-compilare'."""
    file_bytes, _n_righe = build_workbook_parametri(db, con_margine=False)
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes))

    voci = _carica_voci_taratura(db)
    _estendi_coefficienti_pro(wb, db, voci)

    righe_assi = proponi_assegnazione(list(voci.values()))
    _scrivi_assi_proposti(wb, righe_assi)

    _scrivi_dati_richiesti(wb, DATI_RICHIESTI_PROPOSTI)
    _scrivi_leggimi_taratura(wb, stato="da-compilare")

    return wb


def accetta_bozza(wb: Workbook) -> Workbook:
    """Copia del workbook di taratura con ogni proposta accettata in blocco
    (vincolo di Riccardo del 2026-09-26: le fasi 09-10 non si fermano sulla
    sua compilazione). NON modifica i valori proposti (coefficiente_qta_per_mq
    / default_conteggio restano quelli proposti): marca solo decisione='OK'
    (coefficienti_pro/assi_proposti), valore_riccardo=valore_proposto_claude
    (dati_richiesti) e stato='bozza-accettata' con una riga 'avviso' esplicita
    in LEGGIMI_TARATURA."""
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    copia = openpyxl.load_workbook(buffer)

    for nome_foglio, colonne_decisione_note in (
        (FOGLIO_COEFF_PRO, ("decisione", "note")),
        (FOGLIO_ASSI, ("decisione", "note")),
    ):
        ws = copia[nome_foglio]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        col_decisione = header.index(colonne_decisione_note[0])
        col_note = header.index(colonne_decisione_note[1])
        col_id = header.index("id") if "id" in header else header.index("voce_id")
        for riga in ws.iter_rows(min_row=2):
            if riga[col_id].value is None:
                continue
            riga[col_decisione].value = "OK"
            riga[col_note].value = _NOTE_BOZZA_ACCETTATA

    ws_dati = copia[FOGLIO_DATI]
    header_dati = [c.value for c in next(ws_dati.iter_rows(min_row=1, max_row=1))]
    col_codice = header_dati.index("codice_dato")
    col_proposto = header_dati.index("valore_proposto_claude")
    col_riccardo = header_dati.index("valore_riccardo")
    for riga in ws_dati.iter_rows(min_row=2):
        if riga[col_codice].value is None:
            continue
        riga[col_riccardo].value = riga[col_proposto].value

    _scrivi_leggimi_taratura(copia, stato="bozza-accettata", avviso_testo=_AVVISO_BOZZA_ACCETTATA)
    return copia


# --- (e) leggi_decisioni ------------------------------------------------------


@dataclass(frozen=True)
class CoeffDeciso:
    voce_id: int
    tipo_code: str
    coefficiente_qta_per_mq: Decimal | None
    default_conteggio: int | None
    decisione: str
    note: str


@dataclass(frozen=True)
class AsseDeciso:
    voce_id: int
    asse: str
    opzione: str | None
    valore_per_unita: Decimal | None
    fattore_quantita: Decimal | None
    famiglia_alternativa: str
    decisione: str
    note: str


@dataclass(frozen=True)
class DecisioniTaratura:
    stato: str
    coefficienti: list[CoeffDeciso] = field(default_factory=list)
    assi: list[AsseDeciso] = field(default_factory=list)
    dati: dict[str, str] = field(default_factory=dict)


def _decimal_o_none(valore) -> Decimal | None:
    if valore is None:
        return None
    return Decimal(str(valore))


def _intero_o_none(valore) -> int | None:
    if valore is None:
        return None
    return int(valore)


def _leggi_stato(wb: Workbook) -> str:
    if FOGLIO_LEGGIMI not in wb.sheetnames:
        # File restituito a mano senza il foglio LEGGIMI_TARATURA: si
        # assume compilato davvero (comportamento di fallback esplicito).
        return "compilato"
    ws = wb[FOGLIO_LEGGIMI]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    if "sezione" not in header or "testo" not in header:
        return "compilato"
    col_sezione = header.index("sezione")
    col_testo = header.index("testo")
    for riga in ws.iter_rows(min_row=2, values_only=True):
        if riga[col_sezione] == "stato":
            valore = riga[col_testo]
            if valore not in STATI_AMMESSI:
                raise ValueError(f"stato non riconosciuto in {FOGLIO_LEGGIMI}: {valore!r}")
            return valore
    return "compilato"


def _leggi_coefficienti(wb: Workbook) -> list[CoeffDeciso]:
    ws = wb[FOGLIO_COEFF_PRO]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {nome: i for i, nome in enumerate(header)}
    risultato: list[CoeffDeciso] = []
    for numero_riga, riga in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        voce_id = riga[idx["voce_id"]]
        if voce_id is None:
            continue
        tipo_code = riga[idx["tipo_code"]]
        decisione_raw = riga[idx["decisione"]] if "decisione" in idx else None
        decisione = str(decisione_raw).strip().upper() if decisione_raw not in (None, "") else "OK"
        note = riga[idx["note"]] if "note" in idx and riga[idx["note"]] is not None else ""

        if decisione in ("OK", "MODIFICATO"):
            coeff = riga[idx["coefficiente_qta_per_mq"]]
            conteggio = riga[idx["default_conteggio"]]
        elif decisione == "ATTUALE":
            coeff = riga[idx["coefficiente_attuale"]]
            conteggio = riga[idx["default_conteggio_attuale"]]
        else:
            raise ValueError(
                f"{FOGLIO_COEFF_PRO} riga {numero_riga}: decisione non riconosciuta {decisione_raw!r}"
            )

        risultato.append(
            CoeffDeciso(
                voce_id=int(voce_id),
                tipo_code=tipo_code,
                coefficiente_qta_per_mq=_decimal_o_none(coeff),
                default_conteggio=_intero_o_none(conteggio),
                decisione=decisione,
                note=note,
            )
        )
    return risultato


def _leggi_assi(wb: Workbook) -> list[AsseDeciso]:
    if FOGLIO_ASSI not in wb.sheetnames:
        return []
    ws = wb[FOGLIO_ASSI]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {nome: i for i, nome in enumerate(header)}
    risultato: list[AsseDeciso] = []
    for numero_riga, riga in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        voce_id = riga[idx["voce_id"]]
        if voce_id is None:
            continue
        decisione_raw = riga[idx["decisione"]] if "decisione" in idx else None
        decisione = str(decisione_raw).strip().upper() if decisione_raw not in (None, "") else "OK"
        if decisione not in ("OK", "NO", "MODIFICATO"):
            raise ValueError(f"{FOGLIO_ASSI} riga {numero_riga}: decisione non riconosciuta {decisione_raw!r}")
        if decisione == "NO":
            continue
        note = riga[idx["note"]] if "note" in idx and riga[idx["note"]] is not None else ""
        risultato.append(
            AsseDeciso(
                voce_id=int(voce_id),
                asse=riga[idx["asse_proposto"]],
                opzione=riga[idx["opzione_proposta"]],
                valore_per_unita=_decimal_o_none(riga[idx["valore_per_unita"]]),
                fattore_quantita=_decimal_o_none(riga[idx["fattore_quantita"]]),
                famiglia_alternativa=riga[idx["famiglia_alternativa"]],
                decisione=decisione,
                note=note,
            )
        )
    return risultato


def _leggi_dati_richiesti(wb: Workbook) -> dict[str, str]:
    if FOGLIO_DATI not in wb.sheetnames:
        return {}
    ws = wb[FOGLIO_DATI]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {nome: i for i, nome in enumerate(header)}
    dati: dict[str, str] = {}
    for riga in ws.iter_rows(min_row=2, values_only=True):
        codice = riga[idx["codice_dato"]]
        if codice is None:
            continue
        valore_riccardo = riga[idx["valore_riccardo"]] if "valore_riccardo" in idx else None
        valore_proposto = riga[idx["valore_proposto_claude"]] if "valore_proposto_claude" in idx else None
        dati[codice] = valore_riccardo if valore_riccardo not in (None, "") else valore_proposto
    return dati


def leggi_decisioni(wb: Workbook) -> DecisioniTaratura:
    """Rilegge un workbook di taratura (compilato da Riccardo o accettato
    in blocco da `accetta_bozza()`) e ne estrae le decisioni finali."""
    return DecisioniTaratura(
        stato=_leggi_stato(wb),
        coefficienti=_leggi_coefficienti(wb),
        assi=_leggi_assi(wb),
        dati=_leggi_dati_richiesti(wb),
    )


# --- (g) main -----------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(_BACKEND_DIR.parent / "docs" / "taratura" / "09-taratura-pro.xlsx"),
        help="percorso del file di taratura per Riccardo (default: docs/taratura/09-taratura-pro.xlsx)",
    )
    parser.add_argument(
        "--bozza-accettata",
        default=None,
        help="se presente, salva anche la bozza accettata in blocco (stato bozza-accettata) in questo percorso",
    )
    args = parser.parse_args()

    from app.db import SessionLocal  # import tardivo: serve solo qui, mai nei test unitari puri

    with SessionLocal() as db:
        wb = costruisci_workbook_taratura(db)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"scritto {out_path}")

    if args.bozza_accettata:
        bozza = accetta_bozza(wb)
        bozza_path = Path(args.bozza_accettata)
        bozza_path.parent.mkdir(parents=True, exist_ok=True)
        bozza.save(bozza_path)
        print(f"scritta bozza accettata {bozza_path}")


if __name__ == "__main__":
    main()
