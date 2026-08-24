"""Server-side business logic services (estimation engine, city resolution).

These modules are where the pricing secret (`coefficiente_impresa`) may be
read from the DB but must NEVER be placed in any client-facing result.
"""
