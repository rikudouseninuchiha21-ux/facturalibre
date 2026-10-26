"""Conversión de importes monetarios a palabras en español (Colombia).

Formato de factura: ``UN MILLÓN DOSCIENTOS TREINTA Y CUATRO PESOS CON 56/100``.
No se usan librerías externas: los centavos van como ``NN/100`` y el
singular/plural de ``PESOS`` sigue el entero.
"""

from __future__ import annotations

from decimal import Decimal

_UNITS = (
    "",
    "UN",
    "DOS",
    "TRES",
    "CUATRO",
    "CINCO",
    "SEIS",
    "SIETE",
    "OCHO",
    "NUEVE",
    "DIEZ",
    "ONCE",
    "DOCE",
    "TRECE",
    "CATORCE",
    "QUINCE",
)
_TENS = (
    "",
    "",
    "VEINTI",
    "TREINTA",
    "CUARENTA",
    "CINCUENTA",
    "SESENTA",
    "SETENTA",
    "OCHENTA",
    "NOVENTA",
)
_HUNDREDS = (
    "",
    "CIENTO",
    "DOSCIENTOS",
    "TRESCIENTOS",
    "CUATROCIENTOS",
    "QUINIENTOS",
    "SEISCIENTOS",
    "SETECIENTOS",
    "OCHOCIENTOS",
    "NOVECIENTOS",
)

_MAX_SUPPORTED = Decimal("999999999999.99")


def _words_below_hundred(value: int) -> str:
    if value <= 15:
        return _UNITS[value]
    if value < 30:
        return f"VEINTI{_UNITS[value % 10]}"
    tens, units = divmod(value, 10)
    if units:
        return f"{_TENS[tens]} Y {_UNITS[units]}"
    return _TENS[tens]


def _words_below_thousand(value: int) -> str:
    hundreds, rest = divmod(value, 100)
    if value == 100:
        return "CIEN"
    parts = []
    if hundreds:
        parts.append(_HUNDREDS[hundreds])
    if rest:
        parts.append(_words_below_hundred(rest))
    return " ".join(parts)


def _apocope(words: str) -> str:
    """Apócopes ante ``MIL``/``MILLONES``: UNO→UN, VEINTIUNO→VEINTIÚN."""
    if words == "UNO":
        return "UN"
    if words.endswith("UNO"):
        return words[:-3] + "ÚN"
    return words


def _integer_to_words(value: int) -> str:
    if value == 0:
        return "CERO"

    groups: list[int] = []
    remaining = value
    while remaining > 0:
        groups.append(remaining % 1000)
        remaining //= 1000

    parts: list[str] = []
    for position in reversed(range(len(groups))):
        group = groups[position]
        if group == 0:
            continue
        if position == 1:
            if group == 1:
                parts.append("MIL")
                continue
            parts.append(f"{_apocope(_words_below_thousand(group))} MIL")
        elif position == 2:
            if group == 1:
                parts.append("UN MILLÓN")
                continue
            parts.append(f"{_words_below_thousand(group)} MILLONES")
        elif position == 3:
            if group == 1:
                parts.append("MIL MILLONES")
                continue
            parts.append(f"{_apocope(_words_below_thousand(group))} MIL MILLONES")
        else:
            parts.append(_words_below_thousand(group))
    return " ".join(parts)


def number_to_words_es_co(amount: Decimal) -> str:
    """Importe en palabras al estilo de factura colombiana.

    Ejemplos:
    - ``0``        → ``CERO PESOS CON 00/100``
    - ``100``      → ``CIEN PESOS CON 00/100``
    - ``1234.56``  → ``MIL DOSCIENTOS TREINTA Y CUATRO PESOS CON 56/100``
    - ``1000000``  → ``UN MILLÓN PESOS CON 00/100``
    """
    if amount < 0:
        raise ValueError("El importe no puede ser negativo")
    if amount > _MAX_SUPPORTED:
        raise ValueError("Importe fuera de rango soportado")

    cents = int((abs(amount) * 100) % 100)
    units = int(amount)
    words = _integer_to_words(units)
    noun = "PESO" if units == 1 else "PESOS"
    return f"{words} {noun} CON {cents:02d}/100"


__all__ = ["number_to_words_es_co"]
