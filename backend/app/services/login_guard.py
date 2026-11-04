"""Tetto ai tentativi di login falliti PER EMAIL.

Il limite per IP (`app.limiter`) non basta: un attacco distribuito su molti
IP (botnet, proxy) prova la stessa email da indirizzi sempre diversi. Qui si
conta per account: dopo `MAX_FALLITI` errori in `FINESTRA` l'email resta
bloccata per `BLOCCO`, poi riparte da zero.

Il blocco e' breve di proposito: un tetto per account permette anche di
chiudere fuori il proprietario sbagliando apposta la password, e 15 minuti
sono un fastidio, non un'interruzione del servizio.

In memoria: l'app gira su una sola istanza (vedi Dockerfile). Con piu'
istanze ognuna avrebbe il suo contatore, cioe' un tetto piu' largo ma
ancora presente.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

MAX_FALLITI = 10
FINESTRA = 15 * 60
BLOCCO = 15 * 60
#: Oltre questa soglia di email tracciate si fa pulizia delle scadute, cosi'
#: la memoria non cresce senza limite sotto attacco.
MAX_VOCI = 50_000


class LoginGuard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._falliti: dict[str, deque[float]] = defaultdict(deque)
        self._bloccati: dict[str, float] = {}

    def _pulisci(self, ora: float) -> None:
        for email in [e for e, fino in self._bloccati.items() if fino <= ora]:
            del self._bloccati[email]
        for email in list(self._falliti):
            tentativi = self._falliti[email]
            while tentativi and tentativi[0] <= ora - FINESTRA:
                tentativi.popleft()
            if not tentativi:
                del self._falliti[email]

    def bloccato(self, email: str) -> bool:
        with self._lock:
            fino = self._bloccati.get(email)
            if fino is None:
                return False
            if fino <= time.monotonic():
                del self._bloccati[email]
                return False
            return True

    def fallito(self, email: str) -> None:
        ora = time.monotonic()
        with self._lock:
            if len(self._falliti) > MAX_VOCI:
                self._pulisci(ora)
            tentativi = self._falliti[email]
            tentativi.append(ora)
            while tentativi and tentativi[0] <= ora - FINESTRA:
                tentativi.popleft()
            if len(tentativi) >= MAX_FALLITI:
                self._bloccati[email] = ora + BLOCCO
                tentativi.clear()

    def riuscito(self, email: str) -> None:
        with self._lock:
            self._falliti.pop(email, None)
            self._bloccati.pop(email, None)

    def reset(self) -> None:
        """Per i test."""
        with self._lock:
            self._falliti.clear()
            self._bloccati.clear()


login_guard = LoginGuard()
