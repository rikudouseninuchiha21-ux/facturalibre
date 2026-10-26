"""Subpaquete DIAN: generación local de XML UBL 2.1 y PDF (Fase 38A).

Sin firma XAdES y sin envío a la DIAN: eso llega con la Fase 38B.
"""

from app.application.dian.cufe import compute_cufe
from app.application.dian.nit import compute_dv
from app.application.dian.pdf_builder import build_invoice_pdf
from app.application.dian.xml_builder import build_invoice_xml

__all__ = [
    "build_invoice_pdf",
    "build_invoice_xml",
    "compute_cufe",
    "compute_dv",
]
