"""Tests del dígito de verificación del NIT (módulo 11 DIAN)."""

from __future__ import annotations

import pytest

from app.application.dian.nit import NitValidationError, compute_dv


def test_dv_of_dian_nit() -> None:
    # NIT de la DIAN, verificado contra el algoritmo oficial.
    assert compute_dv("800197268") == "4"


def test_dv_of_nine_digit_nit() -> None:
    assert compute_dv("900123456") == "8"


def test_dv_of_short_nit() -> None:
    assert compute_dv("830020470") == "5"


def test_leading_zeros_do_not_change_dv() -> None:
    # Peso x 0 = 0: los ceros a la izquierda no alteran el DV.
    assert compute_dv("001234567") == "2"
    assert compute_dv("001234567") == compute_dv("1234567")


def test_invalid_nit_raises() -> None:
    with pytest.raises(NitValidationError):
        compute_dv("90012345A")
    with pytest.raises(NitValidationError):
        compute_dv("")
