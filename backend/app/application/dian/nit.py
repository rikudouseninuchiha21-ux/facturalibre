"""Algoritmos de identificación tributaria DIAN (NIT y dígito de verificación)."""

from __future__ import annotations

NIT_WEIGHTS: tuple[int, ...] = (3, 7, 13, 17, 19, 23, 29, 37, 41, 11, 13)


class NitValidationError(ValueError):
    """El NIT contiene caracteres que no son dígitos."""


def compute_dv(nit: str) -> str:
    """Calcula el dígito de verificación de un NIT con el algoritmo módulo 11.

    Regla DIAN: cada dígito se multiplica, de derecha a izquierda, por los
    pesos 3, 7, 13, 17, 19, 23, 29, 37, 41, 11, 13... y se suman los
    productos. Con ``residuo = suma % 11``:

    - residuo > 1  →  DV = 11 - residuo
    - residuo <= 1 →  DV = residuo

    Los ceros a la izquierda no alteran el DV (peso × 0 = 0).

    Ejemplos verificados:
    - ``800197268`` (NIT de la DIAN) → DV ``4``
    - ``900123456`` → DV ``8``
    - ``001234567`` → DV ``2`` (igual que ``1234567``)
    """
    digits = nit.strip()
    if not digits or not digits.isdigit():
        raise NitValidationError(f"NIT inválido: {nit!r}")

    total = 0
    for position, digit in enumerate(reversed(digits)):
        total += int(digit) * NIT_WEIGHTS[position % len(NIT_WEIGHTS)]

    residue = total % 11
    return str(11 - residue) if residue > 1 else str(residue)


__all__ = ["NitValidationError", "compute_dv"]
