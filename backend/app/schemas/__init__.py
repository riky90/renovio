"""Pydantic response/request schemas — the anti-leak serialization gate.

Every model here declares an explicit, closed field set. None of these
models may ever reference `base_eur_mq`, `moltiplicatore`, or
`coefficiente_impresa` (see 01-RESEARCH.md Pattern 1 / threat T-03-01).
"""
