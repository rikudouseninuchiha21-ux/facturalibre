"""Tests del número a palabras en español (Colombia)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.application.dian.words import number_to_words_es_co


def test_zero() -> None:
    assert number_to_words_es_co(Decimal("0.00")) == "CERO PESOS CON 00/100"


def test_one_hundred() -> None:
    assert number_to_words_es_co(Decimal("100.00")) == "CIEN PESOS CON 00/100"


def test_thousands_with_cents() -> None:
    assert (
        number_to_words_es_co(Decimal("1234.56"))
        == "MIL DOSCIENTOS TREINTA Y CUATRO PESOS CON 56/100"
    )


def test_one_million() -> None:
    assert number_to_words_es_co(Decimal("1000000.00")) == "UN MILLÓN PESOS CON 00/100"


def test_negative_rejected() -> None:
    with pytest.raises(ValueError):
        number_to_words_es_co(Decimal("-1.00"))
