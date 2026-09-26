"""Migrazione generata da scripts/applica_taratura.py:emetti_migrazione() dal
diff fra i JSON di seed versionati e il file di decisioni (D-03/D-08). Una
migrazione e' uno snapshot immutabile: nessuna lettura di file esterni a
runtime, i valori sono costanti incorporate qui sotto. Aggiorna SOLO le
righe ancora al valore BASE (WHERE campo = vecchio): una taratura fatta a
mano dal pannello dopo questa migrazione non viene mai sovrascritta. Gli
effetti NUOVI (assenti dalla base) non sono qui: li crea il seed
create-if-missing al boot (D-41). Nessun coefficiente impresa.

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-26T15:31:40.823627
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0022'
down_revision: Union[str, Sequence[str], None] = '0021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COEFFICIENTI: tuple[tuple, ...] = (('A-EDILE', 'A.0', 'A.0.11', 'leggera', 'coefficiente_qta_per_mq', None, 0.2), ('A-EDILE', 'A.0', 'A.0.11', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.0', 'A.0.11', 'moderata', 'coefficiente_qta_per_mq', None, 0.35), ('A-EDILE', 'A.0', 'A.0.11', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.0', 'A.0.11', 'totale', 'coefficiente_qta_per_mq', None, 0.5), ('A-EDILE', 'A.0', 'A.0.11', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.0', 'A.0.13', 'leggera', 'coefficiente_qta_per_mq', None, 0.2), ('A-EDILE', 'A.0', 'A.0.13', 'leggera', 'default_conteggio', 0, None), ('A-EDILE', 'A.0', 'A.0.13', 'moderata', 'coefficiente_qta_per_mq', None, 0.35), ('A-EDILE', 'A.0', 'A.0.13', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.0', 'A.0.13', 'totale', 'coefficiente_qta_per_mq', None, 0.5), ('A-EDILE', 'A.0', 'A.0.13', 'totale', 'default_conteggio', 2, None), ('A-EDILE', 'A.0', 'A.0.14', 'leggera', 'coefficiente_qta_per_mq', None, 0.2), ('A-EDILE', 'A.0', 'A.0.14', 'leggera', 'default_conteggio', 0, None), ('A-EDILE', 'A.0', 'A.0.14', 'moderata', 'coefficiente_qta_per_mq', None, 0.35), ('A-EDILE', 'A.0', 'A.0.14', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.0', 'A.0.14', 'totale', 'coefficiente_qta_per_mq', None, 0.5), ('A-EDILE', 'A.0', 'A.0.14', 'totale', 'default_conteggio', 2, None), ('A-EDILE', 'A.0', 'A.0.15', 'leggera', 'coefficiente_qta_per_mq', None, 0.2), ('A-EDILE', 'A.0', 'A.0.15', 'leggera', 'default_conteggio', 0, None), ('A-EDILE', 'A.0', 'A.0.15', 'moderata', 'coefficiente_qta_per_mq', None, 0.35), ('A-EDILE', 'A.0', 'A.0.15', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.0', 'A.0.15', 'totale', 'coefficiente_qta_per_mq', None, 0.5), ('A-EDILE', 'A.0', 'A.0.15', 'totale', 'default_conteggio', 2, None), ('A-EDILE', 'A.0', 'A.0.18', 'leggera', 'coefficiente_qta_per_mq', None, 0.1), ('A-EDILE', 'A.0', 'A.0.18', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.0', 'A.0.18', 'moderata', 'coefficiente_qta_per_mq', None, 0.175), ('A-EDILE', 'A.0', 'A.0.18', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.0', 'A.0.18', 'totale', 'coefficiente_qta_per_mq', None, 0.25), ('A-EDILE', 'A.0', 'A.0.18', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.1.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.2), ('A-EDILE', 'A.1', 'A.1.1.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.35), ('A-EDILE', 'A.1', 'A.1.1.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.5), ('A-EDILE', 'A.1', 'A.1.1.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.2), ('A-EDILE', 'A.1', 'A.1.1.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.35), ('A-EDILE', 'A.1', 'A.1.1.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.5), ('A-EDILE', 'A.1', 'A.1.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.2), ('A-EDILE', 'A.1', 'A.1.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.35), ('A-EDILE', 'A.1', 'A.1.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.5), ('A-EDILE', 'A.1', 'A.1.3', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.1', 'A.1.3', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.1', 'A.1.3', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('A-EDILE', 'A.1', 'A.1.4', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.1', 'A.1.4', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.1', 'A.1.4', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('A-EDILE', 'A.1', 'A.1.5', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.1', 'A.1.5', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.1', 'A.1.5', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.1', 'A.1.6', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.1', 'A.1.6', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.1', 'A.1.6', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.1', 'A.1.7', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.1', 'A.1.7', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.1', 'A.1.7', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.1', 'A.1.8', 'leggera', 'coefficiente_qta_per_mq', 0.06, 0.36), ('A-EDILE', 'A.1', 'A.1.8', 'moderata', 'coefficiente_qta_per_mq', 0.105, 0.63), ('A-EDILE', 'A.1', 'A.1.8', 'totale', 'coefficiente_qta_per_mq', 0.15, 0.9), ('A-EDILE', 'A.1', 'A.1.9', 'leggera', 'coefficiente_qta_per_mq', 0.06, 0.36), ('A-EDILE', 'A.1', 'A.1.9', 'moderata', 'coefficiente_qta_per_mq', 0.105, 0.63), ('A-EDILE', 'A.1', 'A.1.9', 'totale', 'coefficiente_qta_per_mq', 0.15, 0.9), ('A-EDILE', 'A.1', 'A.1.10', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.1), ('A-EDILE', 'A.1', 'A.1.10', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.175), ('A-EDILE', 'A.1', 'A.1.10', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.25), ('A-EDILE', 'A.1', 'A.1.11.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.2), ('A-EDILE', 'A.1', 'A.1.11.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.35), ('A-EDILE', 'A.1', 'A.1.11.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.5), ('A-EDILE', 'A.1', 'A.1.11.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.2), ('A-EDILE', 'A.1', 'A.1.11.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.35), ('A-EDILE', 'A.1', 'A.1.11.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.5), ('A-EDILE', 'A.1', 'A.1.12', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.1', 'A.1.12', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.1', 'A.1.12', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.1', 'A.1.13', 'leggera', 'coefficiente_qta_per_mq', None, 0.2), ('A-EDILE', 'A.1', 'A.1.13', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.13', 'moderata', 'coefficiente_qta_per_mq', None, 0.35), ('A-EDILE', 'A.1', 'A.1.13', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.13', 'totale', 'coefficiente_qta_per_mq', None, 0.5), ('A-EDILE', 'A.1', 'A.1.13', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.14', 'leggera', 'coefficiente_qta_per_mq', None, 0.1), ('A-EDILE', 'A.1', 'A.1.14', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.14', 'moderata', 'coefficiente_qta_per_mq', None, 0.175), ('A-EDILE', 'A.1', 'A.1.14', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.14', 'totale', 'coefficiente_qta_per_mq', None, 0.25), ('A-EDILE', 'A.1', 'A.1.14', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.15', 'leggera', 'coefficiente_qta_per_mq', None, 0.2), ('A-EDILE', 'A.1', 'A.1.15', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.15', 'moderata', 'coefficiente_qta_per_mq', None, 0.35), ('A-EDILE', 'A.1', 'A.1.15', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.15', 'totale', 'coefficiente_qta_per_mq', None, 0.5), ('A-EDILE', 'A.1', 'A.1.15', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.16', 'leggera', 'coefficiente_qta_per_mq', None, 0.2), ('A-EDILE', 'A.1', 'A.1.16', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.16', 'moderata', 'coefficiente_qta_per_mq', None, 0.35), ('A-EDILE', 'A.1', 'A.1.16', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.1', 'A.1.16', 'totale', 'coefficiente_qta_per_mq', None, 0.5), ('A-EDILE', 'A.1', 'A.1.16', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.2', 'A.2.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.2', 'A.2.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.2', 'A.2.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.2', 'A.2.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.2', 'A.2.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.2', 'A.2.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.2', 'A.2.3', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.2', 'A.2.3', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.2', 'A.2.3', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.2', 'A.2.4', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.2', 'A.2.4', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.2', 'A.2.4', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.2', 'A.2.5', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.2', 'A.2.5', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.2', 'A.2.5', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.3', 'A.3.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.3', 'A.3.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.3', 'A.3.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.3', 'A.3.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.3', 'A.3.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.3', 'A.3.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.3', 'A.3.3', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.3', 'A.3.3', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.3', 'A.3.3', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.3', 'A.3.4', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.3', 'A.3.4', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.3', 'A.3.4', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.3', 'A.3.8', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.3', 'A.3.8', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.4', 'A.4.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.4', 'A.4.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.4', 'A.4.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('A-EDILE', 'A.4', 'A.4.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.1), ('A-EDILE', 'A.4', 'A.4.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.175), ('A-EDILE', 'A.4', 'A.4.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.25), ('A-EDILE', 'A.5', 'A.5.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.5', 'A.5.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.5', 'A.5.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('A-EDILE', 'A.5', 'A.5.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.5', 'A.5.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.5', 'A.5.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('A-EDILE', 'A.5', 'A.5.3', 'leggera', 'coefficiente_qta_per_mq', 0.06, 1.08), ('A-EDILE', 'A.5', 'A.5.3', 'moderata', 'coefficiente_qta_per_mq', 0.105, 1.89), ('A-EDILE', 'A.5', 'A.5.3', 'totale', 'coefficiente_qta_per_mq', 0.15, 2.7), ('A-EDILE', 'A.5', 'A.5.4', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.5', 'A.5.4', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.5', 'A.5.4', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.6', 'A.6.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.6', 'A.6.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.6', 'A.6.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.6', 'A.6.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.6', 'A.6.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.6', 'A.6.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.6', 'A.6.3', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.1), ('A-EDILE', 'A.6', 'A.6.3', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.175), ('A-EDILE', 'A.6', 'A.6.3', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.25), ('A-EDILE', 'A.6', 'A.6.4', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.1), ('A-EDILE', 'A.6', 'A.6.4', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.175), ('A-EDILE', 'A.6', 'A.6.4', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.25), ('A-EDILE', 'A.6', 'A.6.5', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.1), ('A-EDILE', 'A.6', 'A.6.5', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.175), ('A-EDILE', 'A.6', 'A.6.5', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.25), ('A-EDILE', 'A.6', 'A.6.6', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.6', 'A.6.6', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.6', 'A.6.6', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.6', 'A.6.7', 'leggera', 'coefficiente_qta_per_mq', 0.06, 0.36), ('A-EDILE', 'A.6', 'A.6.7', 'moderata', 'coefficiente_qta_per_mq', 0.105, 0.63), ('A-EDILE', 'A.6', 'A.6.7', 'totale', 'coefficiente_qta_per_mq', 0.15, 0.9), ('A-EDILE', 'A.6', 'A.6.8', 'leggera', 'coefficiente_qta_per_mq', 0.06, 0.36), ('A-EDILE', 'A.6', 'A.6.8', 'moderata', 'coefficiente_qta_per_mq', 0.105, 0.63), ('A-EDILE', 'A.6', 'A.6.8', 'totale', 'coefficiente_qta_per_mq', 0.15, 0.9), ('A-EDILE', 'A.6', 'A.6.9', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.6', 'A.6.9', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.6', 'A.6.9', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.6', 'A.6.10', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.6', 'A.6.10', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.6', 'A.6.10', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.6', 'A.6.11', 'leggera', 'coefficiente_qta_per_mq', None, 0.34), ('A-EDILE', 'A.6', 'A.6.11', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.6', 'A.6.11', 'moderata', 'coefficiente_qta_per_mq', None, 0.595), ('A-EDILE', 'A.6', 'A.6.11', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.6', 'A.6.11', 'totale', 'coefficiente_qta_per_mq', None, 0.85), ('A-EDILE', 'A.6', 'A.6.11', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.7', 'A.7.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.7', 'A.7.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.7', 'A.7.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.7', 'A.7.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.7', 'A.7.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.7', 'A.7.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.8', 'A.8.2', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.2', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.8', 'A.8.3', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.3', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.8', 'A.8.4', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.4', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.8', 'A.8.7', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.7', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.8', 'A.8.10', 'leggera', 'default_conteggio', 0, 2), ('A-EDILE', 'A.8', 'A.8.10', 'moderata', 'default_conteggio', 1, 2), ('A-EDILE', 'A.8', 'A.8.11', 'leggera', 'default_conteggio', 0, 2), ('A-EDILE', 'A.8', 'A.8.11', 'moderata', 'default_conteggio', 1, 2), ('A-EDILE', 'A.8', 'A.8.12', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.12', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.8', 'A.8.13.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.8', 'A.8.13.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.8', 'A.8.13.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.8', 'A.8.13.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('A-EDILE', 'A.8', 'A.8.13.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('A-EDILE', 'A.8', 'A.8.13.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('A-EDILE', 'A.8', 'A.8.13.3', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.13.3', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.8', 'A.8.15', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.15', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.8', 'A.8.16', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.16', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.8', 'A.8.17', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.17', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.8', 'A.8.19', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.8', 'A.8.19', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.9', 'A.9.1', 'leggera', 'coefficiente_qta_per_mq', None, 0.34), ('A-EDILE', 'A.9', 'A.9.1', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.9', 'A.9.1', 'moderata', 'coefficiente_qta_per_mq', None, 0.595), ('A-EDILE', 'A.9', 'A.9.1', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.9', 'A.9.1', 'totale', 'coefficiente_qta_per_mq', None, 0.85), ('A-EDILE', 'A.9', 'A.9.1', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.9', 'A.9.2', 'leggera', 'coefficiente_qta_per_mq', None, 0.34), ('A-EDILE', 'A.9', 'A.9.2', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.9', 'A.9.2', 'moderata', 'coefficiente_qta_per_mq', None, 0.595), ('A-EDILE', 'A.9', 'A.9.2', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.9', 'A.9.2', 'totale', 'coefficiente_qta_per_mq', None, 0.85), ('A-EDILE', 'A.9', 'A.9.2', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.9', 'A.9.3', 'leggera', 'coefficiente_qta_per_mq', None, 0.34), ('A-EDILE', 'A.9', 'A.9.3', 'leggera', 'default_conteggio', 0, None), ('A-EDILE', 'A.9', 'A.9.3', 'moderata', 'coefficiente_qta_per_mq', None, 0.595), ('A-EDILE', 'A.9', 'A.9.3', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.9', 'A.9.3', 'totale', 'coefficiente_qta_per_mq', None, 0.85), ('A-EDILE', 'A.9', 'A.9.3', 'totale', 'default_conteggio', 2, None), ('A-EDILE', 'A.9', 'A.9.4', 'leggera', 'coefficiente_qta_per_mq', None, 0.34), ('A-EDILE', 'A.9', 'A.9.4', 'leggera', 'default_conteggio', 1, None), ('A-EDILE', 'A.9', 'A.9.4', 'moderata', 'coefficiente_qta_per_mq', None, 0.595), ('A-EDILE', 'A.9', 'A.9.4', 'moderata', 'default_conteggio', 1, None), ('A-EDILE', 'A.9', 'A.9.4', 'totale', 'coefficiente_qta_per_mq', None, 0.85), ('A-EDILE', 'A.9', 'A.9.4', 'totale', 'default_conteggio', 1, None), ('A-EDILE', 'A.10', 'A.10.2', 'leggera', 'default_conteggio', 0, 2), ('A-EDILE', 'A.10', 'A.10.2', 'moderata', 'default_conteggio', 1, 2), ('A-EDILE', 'A.10', 'A.10.3', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.10', 'A.10.3', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.10', 'A.10.4', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.10', 'A.10.4', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.10', 'A.10.6', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.10', 'A.10.6', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.10', 'A.10.7', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.10', 'A.10.7', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.10', 'A.10.8', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.10', 'A.10.8', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.10', 'A.10.9', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.10', 'A.10.9', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.10', 'A.10.10', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.10', 'A.10.10', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.10', 'A.10.11', 'leggera', 'default_conteggio', 0, 1), ('A-EDILE', 'A.10', 'A.10.11', 'totale', 'default_conteggio', 2, 1), ('A-EDILE', 'A.11', 'A.11.1', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('A-EDILE', 'A.11', 'A.11.1', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('A-EDILE', 'A.11', 'A.11.1', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('A-EDILE', 'A.11', 'A.11.2', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.11', 'A.11.2', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.11', 'A.11.2', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('A-EDILE', 'A.11', 'A.11.3', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.11', 'A.11.3', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.11', 'A.11.3', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('A-EDILE', 'A.11', 'A.11.4', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.11', 'A.11.4', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.11', 'A.11.4', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('A-EDILE', 'A.11', 'A.11.5', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.11', 'A.11.5', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.11', 'A.11.5', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('A-EDILE', 'A.11', 'A.11.6', 'leggera', 'coefficiente_qta_per_mq', 0.24, 1.08), ('A-EDILE', 'A.11', 'A.11.6', 'moderata', 'coefficiente_qta_per_mq', 0.42, 1.89), ('A-EDILE', 'A.11', 'A.11.6', 'totale', 'coefficiente_qta_per_mq', 0.6, 2.7), ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('B-FINITURE', 'PAVIMENTI', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('B-FINITURE', 'PAVIMENTI', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('B-FINITURE', 'PAVIMENTI', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('B-FINITURE', 'PAVIMENTI', 'Unilin sottofondo in schiuma senza barriera vapore', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.34), ('B-FINITURE', 'PAVIMENTI', 'Unilin sottofondo in schiuma senza barriera vapore', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.595), ('B-FINITURE', 'PAVIMENTI', 'Unilin sottofondo in schiuma senza barriera vapore', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.85), ('B-FINITURE', 'MATERIALI DI POSA', 'Colle, stucchi distanziatori e cunei per la posa', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.16), ('B-FINITURE', 'MATERIALI DI POSA', 'Colle, stucchi distanziatori e cunei per la posa', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.28), ('B-FINITURE', 'MATERIALI DI POSA', 'Colle, stucchi distanziatori e cunei per la posa', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.4), ('B-FINITURE', 'RUBINETTERIE', 'Miscelatore monocomando cromato per lavabo con scarico automatico: normale', 'leggera', 'default_conteggio', 0, 1), ('B-FINITURE', 'RUBINETTERIE', 'Miscelatore monocomando cromato per lavabo con scarico automatico: normale', 'totale', 'default_conteggio', 2, 1), ('B-FINITURE', 'RUBINETTERIE', "Placca di copertura per cassette d'incasso: con tasto di comando e interruzione del risciacquo, in materiale plastico opaca", 'leggera', 'default_conteggio', 0, 1), ('B-FINITURE', 'RUBINETTERIE', "Placca di copertura per cassette d'incasso: con tasto di comando e interruzione del risciacquo, in materiale plastico opaca", 'totale', 'default_conteggio', 2, 1), ('C-SERRAMENTI', 'PORTE', 'Rimozione vecchio controtelaio e ripristino delle parti ammalorate mediante stuccatura e verciatura delle parti interessate', 'leggera', 'coefficiente_qta_per_mq', None, 0.2), ('C-SERRAMENTI', 'PORTE', 'Rimozione vecchio controtelaio e ripristino delle parti ammalorate mediante stuccatura e verciatura delle parti interessate', 'leggera', 'default_conteggio', 0, None), ('C-SERRAMENTI', 'PORTE', 'Rimozione vecchio controtelaio e ripristino delle parti ammalorate mediante stuccatura e verciatura delle parti interessate', 'moderata', 'coefficiente_qta_per_mq', None, 0.35), ('C-SERRAMENTI', 'PORTE', 'Rimozione vecchio controtelaio e ripristino delle parti ammalorate mediante stuccatura e verciatura delle parti interessate', 'moderata', 'default_conteggio', 1, None), ('C-SERRAMENTI', 'PORTE', 'Rimozione vecchio controtelaio e ripristino delle parti ammalorate mediante stuccatura e verciatura delle parti interessate', 'totale', 'coefficiente_qta_per_mq', None, 0.5), ('C-SERRAMENTI', 'PORTE', 'Rimozione vecchio controtelaio e ripristino delle parti ammalorate mediante stuccatura e verciatura delle parti interessate', 'totale', 'default_conteggio', 2, None), ('C-SERRAMENTI', 'PORTE', 'Finestre a 1/2/3 ante con profilo in PVC , telaio SL LA, colore bianco massa, (5 camere con doppia guarnizione), doppio rinforzo, comprensivo di vetro di sicurezza 2.2.1-18GA-22.1BE. Completo di anta a ribalta, microventilazione, ferramenta e maniglia satinata. La voce comprende fornitura, trasporto', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.2), ('C-SERRAMENTI', 'PORTE', 'Finestre a 1/2/3 ante con profilo in PVC , telaio SL LA, colore bianco massa, (5 camere con doppia guarnizione), doppio rinforzo, comprensivo di vetro di sicurezza 2.2.1-18GA-22.1BE. Completo di anta a ribalta, microventilazione, ferramenta e maniglia satinata. La voce comprende fornitura, trasporto', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.35), ('C-SERRAMENTI', 'PORTE', 'Finestre a 1/2/3 ante con profilo in PVC , telaio SL LA, colore bianco massa, (5 camere con doppia guarnizione), doppio rinforzo, comprensivo di vetro di sicurezza 2.2.1-18GA-22.1BE. Completo di anta a ribalta, microventilazione, ferramenta e maniglia satinata. La voce comprende fornitura, trasporto', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.5), ('C-SERRAMENTI', 'PORTE', 'Porta finestra a 1/2/3 ante con profilo in PVC , telaio SL LA, colore bianco massa, (5 camere con doppia guarnizione), doppio rinforzo, comprensivo di vetro di sicurezza 2.2.1-18GA-22.1BE. Completo di anta a ribalta, microventilazione, ferramenta e maniglia satinata. La voce comprende fornitura, tra', 'leggera', 'coefficiente_qta_per_mq', 0.24, 0.048), ('C-SERRAMENTI', 'PORTE', 'Porta finestra a 1/2/3 ante con profilo in PVC , telaio SL LA, colore bianco massa, (5 camere con doppia guarnizione), doppio rinforzo, comprensivo di vetro di sicurezza 2.2.1-18GA-22.1BE. Completo di anta a ribalta, microventilazione, ferramenta e maniglia satinata. La voce comprende fornitura, tra', 'moderata', 'coefficiente_qta_per_mq', 0.42, 0.084), ('C-SERRAMENTI', 'PORTE', 'Porta finestra a 1/2/3 ante con profilo in PVC , telaio SL LA, colore bianco massa, (5 camere con doppia guarnizione), doppio rinforzo, comprensivo di vetro di sicurezza 2.2.1-18GA-22.1BE. Completo di anta a ribalta, microventilazione, ferramenta e maniglia satinata. La voce comprende fornitura, tra', 'totale', 'coefficiente_qta_per_mq', 0.6, 0.12), ('D-PRODOTTI', 'PRODOTTI', 'Fornitura Caldaia MYNUTE RAIN GREEN E 25', 'leggera', 'default_conteggio', 0, 1), ('D-PRODOTTI', 'PRODOTTI', 'Fornitura Caldaia MYNUTE RAIN GREEN E 25', 'totale', 'default_conteggio', 2, 1), ('D-PRODOTTI', 'PRODOTTI', 'Fornitura di termosifoni tubolari NOVO 1520/500', 'leggera', 'default_conteggio', 0, 2), ('D-PRODOTTI', 'PRODOTTI', 'Fornitura di termosifoni tubolari NOVO 1520/500', 'moderata', 'default_conteggio', 1, 2), ('D-PRODOTTI', 'PRODOTTI', 'Fornitura scaldasalviette NOVO', 'leggera', 'default_conteggio', 0, 1), ('D-PRODOTTI', 'PRODOTTI', 'Fornitura scaldasalviette NOVO', 'totale', 'default_conteggio', 2, 1))
_VALORI_EFFETTO: tuple[tuple, ...] = ()
_INCLUDI_SPOSTATI: tuple[tuple, ...] = ()
_EFFETTI_RIMOSSI: tuple[tuple, ...] = (('finitura', 'base', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A):30 Ã— 60 cm, naturale o bocciardato, spessore 10'), None, None), ('finitura', 'base', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 Ã— 60 cm, spessore 15 mm'), None, None), ('finitura', 'base', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Fornitura di pavimentazione/rivestimento in gres porcelanato TIPO: Padana marmosmart pietrasanta smart honed 60 x 60 1Â° sc. (mq. 1,44x)'), None, None), ('finitura', 'base', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):dimensioni 60 Ã— 60 cm, spessore 15 mm'), None, None), ('finitura', 'base', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 Ã— 60 cm, spessore 10 mm'), None, None), ('finitura', 'base', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 Ã— 30 cm, effetto marmetta grana media antiscivolo (R11), spessore 8,5 mm'), None, None), ('finitura', 'base', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 Ã— 30 cm, superficie bocciardata antiscivolo (R12 B), spessore 8,5 mm'), None, None), ('finitura', 'medio', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 Ã— 120 cm, naturale, spessore 10 mm'), None, None), ('finitura', 'medio', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:30 Ã— 60 cm'), None, None), ('finitura', 'medio', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:60 Ã— 120 cm'), None, None), ('finitura', 'medio', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):60 Ã— 120 cm, naturale, spessore 10 mm'), None, None), ('finitura', 'medio', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 60 Ã— 120 cm, spessore 10,5 mm'), None, None), ('finitura', 'medio', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9):60 Ã— 120 cm, spessore 10,5 mm'), None, None), ('finitura', 'medio', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9): 60 Ã— 60 cm, spessore 10 mm'), None, None), ('finitura', 'alto', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 Ã— 30 cm, disegno mosaico'), None, None), ('finitura', 'alto', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto cemento:120 Ã— 120 cm, rettificato, spessore 10,5 mm'), None, None), ('finitura', 'alto', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm: 90 Ã— 90 cm'), None, None), ('finitura', 'alto', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:120 Ã— 278 cm, spessore 6 mm:effetto marmo, superficie lucida'), None, None), ('finitura', 'alto', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:160 Ã— 320 cm, spessore 6 mm:effetto marmo, superficie lucida'), None, None), ('finitura', 'alto', 'includi', ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Ceramica monocottura di pasta bianca in lastre ottenute per pressatura, rettificate, per rivestimenti ad uso residenziale, grado di assorbimento acqua gruppo BIII L a norma UNI EN 14411, delle dimensioni di 60 Ã— 180 cm:effetto cemento, strutturato, spessore 9 mm'), None, None), ('tipo_pavimento', 'gres', 'includi', ('A-EDILE', 'A.6', 'A.6.1'), None, None), ('bagni', 'valore', 'quantita_per_unita', ('B-FINITURE', 'RUBINETTERIE', 'Piatto doccia in acrilico colore bianco, scarico centrale, per installazione sopra pavimento, inclusa piletta sifonata con foro âˆ… 90 mm: rettangolare: 120 Ã— 80 Ã— 4 cm o 100 Ã— 80 Ã— 4 cm'), None, 1), ('bagni', 'valore', 'quantita_per_unita', ('B-FINITURE', 'RUBINETTERIE', 'Vasca in acrilico colore bianco, scarico centrale, per installazione ad incasso, inclusa piletta sifonata con foro âˆ… 90 mm: rettangolare: 170 Ã— 70'), None, 1), ('bagni', 'valore', 'quantita_per_unita', ('B-FINITURE', 'RUBINETTERIE', 'Bidet in porcellana dura (vetrochina): monoforo con erogazione dalla rubinetteria, 36 Ã— 54 Ã— 39 cm'), None, 1), ('bagni', 'valore', 'quantita_per_unita', ('B-FINITURE', 'RUBINETTERIE', 'Bidet in porcellana dura (vetrochina): sospeso, monoforo con erogazione dalla rubinetteria. 35 Ã— 57 Ã— 32 cm'), None, 1), ('porte', 'valore', 'quantita_per_unita', ('C-SERRAMENTI', 'PORTE', 'Porta in legno scorrevole interno muro con anta tamburata e bordi impiallacciati, spessore 8/11 mm, coprifili ad incastro in multistrato, serratura a gancio con nottolino e maniglia ad incasso, dimensioni 210 Ã— 60 Ã· 90 cm:cieca liscia, anta singola:noce tanganika'), None, 1), ('porte', 'valore', 'quantita_per_unita', ('C-SERRAMENTI', 'PORTE', 'Porta in legno scorrevole interno muro con anta tamburata e bordi impiallacciati, spessore 8/11 mm, coprifili ad incastro in multistrato, serratura a gancio con nottolino e maniglia ad incasso, dimensioni 210 Ã— 60 Ã· 90 cm:cieca liscia, anta singola:laccata bianca'), None, 1))

_TOLLERANZA = 1e-6


def _tabelle():
    """Definizioni locali delle tabelle toccate (mai i modelli ORM: una
    migrazione dati non deve dipendere da come saranno i modelli in futuro,
    stesso principio della 0021)."""
    sottocategoria = sa.table(
        "sottocategoria",
        sa.column("id"),
        sa.column("categoria_code"),
        sa.column("codice"),
        sa.column("nome"),
    )
    voce = sa.table(
        "voce",
        sa.column("id"),
        sa.column("sottocategoria_id"),
        sa.column("codice"),
        sa.column("descrizione"),
    )
    coefficiente = sa.table(
        "coefficiente_qta_voce",
        sa.column("id"),
        sa.column("voce_id"),
        sa.column("tipo_code"),
        sa.column("coefficiente_qta_per_mq"),
        sa.column("default_conteggio"),
        sa.column("updated_at"),
    )
    opzione = sa.table(
        "opzione_domanda",
        sa.column("id"),
        sa.column("domanda_code"),
        sa.column("code"),
    )
    effetto = sa.table(
        "effetto_opzione",
        sa.column("id"),
        sa.column("opzione_id"),
        sa.column("tipo_effetto"),
        sa.column("target_voce_id"),
        sa.column("tipo_code"),
        sa.column("valore"),
        sa.column("attivo"),
        sa.column("updated_at"),
    )
    return sottocategoria, voce, coefficiente, opzione, effetto


def _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key):
    """Chiave naturale -> voce.id (codice se esiste, altrimenti nome/descrizione
    esatta — stessa regola del seed/09-02). `None` se non risolta: la riga
    del diff viene saltata, mai un'eccezione (dato di curatela rotto non deve
    bloccare il boot)."""
    riga_sotto = bind.execute(
        sa.select(sottocategoria.c.id).where(
            sottocategoria.c.categoria_code == categoria_code,
            sottocategoria.c.codice == sottocategoria_key,
        )
    ).first()
    if riga_sotto is None:
        riga_sotto = bind.execute(
            sa.select(sottocategoria.c.id).where(
                sottocategoria.c.categoria_code == categoria_code,
                sottocategoria.c.codice.is_(None),
                sottocategoria.c.nome == sottocategoria_key,
            )
        ).first()
    if riga_sotto is None:
        return None
    sotto_id = riga_sotto[0]
    riga_voce = bind.execute(
        sa.select(voce.c.id).where(voce.c.sottocategoria_id == sotto_id, voce.c.codice == voce_key)
    ).first()
    if riga_voce is None:
        riga_voce = bind.execute(
            sa.select(voce.c.id).where(
                voce.c.sottocategoria_id == sotto_id,
                voce.c.codice.is_(None),
                voce.c.descrizione == voce_key,
            )
        ).first()
    return riga_voce[0] if riga_voce is not None else None


def _opzione_id(bind, opzione, domanda_code, opzione_code):
    riga = bind.execute(
        sa.select(opzione.c.id).where(opzione.c.domanda_code == domanda_code, opzione.c.code == opzione_code)
    ).first()
    return riga[0] if riga is not None else None


def _vicino(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= _TOLLERANZA


def upgrade() -> None:
    bind = op.get_bind()
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)
    sottocategoria, voce, coefficiente, opzione, effetto = _tabelle()

    for categoria_code, sottocategoria_key, voce_key, tipo_code, campo, vecchio, nuovo in _COEFFICIENTI:
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if voce_id is None:
            continue
        riga = bind.execute(
            sa.select(coefficiente.c.id, coefficiente.c[campo]).where(
                coefficiente.c.voce_id == voce_id, coefficiente.c.tipo_code == tipo_code
            )
        ).first()
        if riga is None or not _vicino(riga[1], vecchio):
            continue
        bind.execute(
            sa.update(coefficiente).where(coefficiente.c.id == riga[0]).values(**{campo: nuovo, "updated_at": adesso})
        )

    for domanda_code, opzione_code, tipo_effetto, chiave_voce, tipo_code, vecchio, nuovo in _VALORI_EFFETTO:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        cond_tipo_code = (
            effetto.c.tipo_code == tipo_code if tipo_code is not None else effetto.c.tipo_code.is_(None)
        )
        riga = bind.execute(
            sa.select(effetto.c.id, effetto.c.valore).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
                cond_tipo_code,
            )
        ).first()
        if riga is None or not _vicino(riga[1], vecchio):
            continue
        bind.execute(sa.update(effetto).where(effetto.c.id == riga[0]).values(valore=nuovo, updated_at=adesso))

    for domanda_code, chiave_voce, opzione_vecchia, opzione_nuova in _INCLUDI_SPOSTATI:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        opzione_nuova_id = _opzione_id(bind, opzione, domanda_code, opzione_nuova)
        opzione_vecchia_id = _opzione_id(bind, opzione, domanda_code, opzione_vecchia)
        if voce_id is None or opzione_nuova_id is None or opzione_vecchia_id is None:
            continue
        gia_su_nuova = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_nuova_id,
                effetto.c.tipo_effetto == "includi",
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        riga_vecchia = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_vecchia_id,
                effetto.c.tipo_effetto == "includi",
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        if gia_su_nuova is not None:
            if riga_vecchia is not None:
                bind.execute(sa.delete(effetto).where(effetto.c.id == riga_vecchia[0]))
            continue
        if riga_vecchia is None:
            continue
        bind.execute(
            sa.update(effetto).where(effetto.c.id == riga_vecchia[0]).values(opzione_id=opzione_nuova_id, updated_at=adesso)
        )

    for domanda_code, opzione_code, tipo_effetto, chiave_voce, tipo_code, valore in _EFFETTI_RIMOSSI:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        cond_tipo_code = (
            effetto.c.tipo_code == tipo_code if tipo_code is not None else effetto.c.tipo_code.is_(None)
        )
        riga = bind.execute(
            sa.select(effetto.c.id, effetto.c.valore).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
                cond_tipo_code,
            )
        ).first()
        if riga is None:
            continue
        if valore is not None and not _vicino(riga[1], valore):
            continue
        bind.execute(sa.delete(effetto).where(effetto.c.id == riga[0]))


def downgrade() -> None:
    bind = op.get_bind()
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)
    sottocategoria, voce, coefficiente, opzione, effetto = _tabelle()

    for categoria_code, sottocategoria_key, voce_key, tipo_code, campo, vecchio, nuovo in _COEFFICIENTI:
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if voce_id is None:
            continue
        riga = bind.execute(
            sa.select(coefficiente.c.id, coefficiente.c[campo]).where(
                coefficiente.c.voce_id == voce_id, coefficiente.c.tipo_code == tipo_code
            )
        ).first()
        if riga is None or not _vicino(riga[1], nuovo):
            continue
        bind.execute(
            sa.update(coefficiente).where(coefficiente.c.id == riga[0]).values(**{campo: vecchio, "updated_at": adesso})
        )

    for domanda_code, opzione_code, tipo_effetto, chiave_voce, tipo_code, vecchio, nuovo in _VALORI_EFFETTO:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        cond_tipo_code = (
            effetto.c.tipo_code == tipo_code if tipo_code is not None else effetto.c.tipo_code.is_(None)
        )
        riga = bind.execute(
            sa.select(effetto.c.id, effetto.c.valore).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
                cond_tipo_code,
            )
        ).first()
        if riga is None or not _vicino(riga[1], nuovo):
            continue
        bind.execute(sa.update(effetto).where(effetto.c.id == riga[0]).values(valore=vecchio, updated_at=adesso))

    for domanda_code, chiave_voce, opzione_vecchia, opzione_nuova in _INCLUDI_SPOSTATI:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        opzione_nuova_id = _opzione_id(bind, opzione, domanda_code, opzione_nuova)
        opzione_vecchia_id = _opzione_id(bind, opzione, domanda_code, opzione_vecchia)
        if voce_id is None or opzione_nuova_id is None or opzione_vecchia_id is None:
            continue
        gia_su_vecchia = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_vecchia_id,
                effetto.c.tipo_effetto == "includi",
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        riga_nuova = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_nuova_id,
                effetto.c.tipo_effetto == "includi",
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        if gia_su_vecchia is not None:
            if riga_nuova is not None:
                bind.execute(sa.delete(effetto).where(effetto.c.id == riga_nuova[0]))
            continue
        if riga_nuova is None:
            continue
        bind.execute(
            sa.update(effetto).where(effetto.c.id == riga_nuova[0]).values(opzione_id=opzione_vecchia_id, updated_at=adesso)
        )

    for domanda_code, opzione_code, tipo_effetto, chiave_voce, tipo_code, valore in _EFFETTI_RIMOSSI:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        gia_presente = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        if gia_presente is not None:
            continue
        bind.execute(
            sa.insert(effetto).values(
                opzione_id=opzione_id,
                tipo_effetto=tipo_effetto,
                target_voce_id=voce_id,
                tipo_code=tipo_code,
                valore=valore,
                attivo=True,
                updated_at=adesso,
            )
        )
