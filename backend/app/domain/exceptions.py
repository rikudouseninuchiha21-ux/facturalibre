"""Errores de dominio compartidos por los repositorios."""


class ResourceNotFoundError(Exception):
    """El recurso no existe o está eliminado lógicamente."""


class VersionConflictError(Exception):
    """La versión enviada no coincide con la versión actual del recurso."""


class InvoiceStateError(Exception):
    """La operación no está permitida para el estado actual de la factura."""


class InventoryError(Exception):
    """Operación de inventario inválida o imposible de completar."""


class InsufficientStockError(InventoryError):
    """La bodega no tiene cantidad suficiente para una salida de stock."""


class PayrollError(Exception):
    """Operación de nómina inválida o periodo no liquidable."""
