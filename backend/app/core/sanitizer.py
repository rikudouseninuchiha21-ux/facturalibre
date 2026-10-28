"""Sanitización de entradas de texto (OWASP LLM01, prompt injection).

Reservado para cuando se integren modelos de IA (39B+): todo texto externo
que llegue a un prompt pasa por ``sanitize_for_prompt``. Hoy se usa para
validar que las entradas de usuario que viajan a XML/logs no contengan
marcado peligroso.
"""

from __future__ import annotations

import re
import unicodedata

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_PROMPT_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts)", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"<\|.*?\|>"),
    re.compile(r"</?(script|iframe|object|embed)\b", re.IGNORECASE),
)

MAX_TEXT_LENGTH = 5000


def sanitize_for_prompt(value: str, *, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Normaliza y neutraliza texto externo antes de un prompt o documento.

    - Elimina caracteres de control y marca etiquetas peligrosas.
    - Reduce a un límite de longitud.
    - NO elimina contenido legítimo: solo neutraliza inyección.
    """
    normalized = unicodedata.normalize("NFKC", value)
    normalized = _CONTROL_CHARS.sub("", normalized)
    for pattern in _PROMPT_PATTERNS:
        normalized = pattern.sub("[sanitizado]", normalized)
    return normalized[:max_length]


def contains_prompt_injection(value: str) -> bool:
    """Detecta patrones típicos de prompt injection en texto externo."""
    return any(pattern.search(value) for pattern in _PROMPT_PATTERNS)


__all__ = ["contains_prompt_injection", "sanitize_for_prompt"]
