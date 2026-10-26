"""Errores de dominio compartidos por los repositorios."""


class ResourceNotFoundError(Exception):
    """El recurso no existe o está eliminado lógicamente."""


class VersionConflictError(Exception):
    """La versión enviada no coincide con la versión actual del recurso."""


class InvoiceStateError(Exception):
    """La operación no está permitida para el estado actual de la factura."""


class InvoiceValidationError(Exception):
    """Los datos de entrada de una factura no son válidos."""


class QuoteStateError(Exception):
    """La operación no está permitida para el estado actual de la cotización."""


class InventoryError(Exception):
    """Operación de inventario inválida o imposible de completar."""


class InsufficientStockError(InventoryError):
    """La bodega no tiene cantidad suficiente para una salida de stock."""


class PayrollError(Exception):
    """Operación de nómina inválida o periodo no liquidable."""


class TreasuryError(Exception):
    """Operación de tesorería inválida para el estado actual."""


class TreasuryValidationError(TreasuryError):
    """Datos de tesorería inconsistentes con el catálogo o las cuentas."""


class FixedAssetError(Exception):
    """Operación inválida sobre un activo fijo o su depreciación."""


class FixedAssetValidationError(FixedAssetError):
    """Datos del activo incompatibles con su política de depreciación."""


class CostCenterError(Exception):
    """Operación inválida sobre un centro de costo (código duplicado, etc.)."""


class BudgetError(Exception):
    """Operación inválida sobre un presupuesto."""


class BudgetStateError(BudgetError):
    """La operación no está permitida para el estado actual del presupuesto."""


class BudgetValidationError(BudgetError):
    """Datos de presupuesto inconsistentes con el catálogo o el periodo."""


class ReceivablesError(Exception):
    """Operación inválida sobre cartera, recordatorios o acuerdos."""


class ReceivablesValidationError(ReceivablesError):
    """Datos de cartera inconsistentes con facturas, pagos o contacto."""


class ReminderError(ReceivablesError):
    """Recordatorio de cobranza no permitido para el estado actual."""


class AgreementError(ReceivablesError):
    """Acuerdo de pago no permitido en su estado actual."""


class AgreementValidationError(AgreementError):
    """Datos del acuerdo incompatibles con las cuotas o el saldo de la factura."""


class AuthError(Exception):
    """Error de autenticación o registro."""


class EmailAlreadyRegisteredError(AuthError):
    """El email ya pertenece a un usuario."""


class RegistrationClosedError(AuthError):
    """El registro público ya fue cerrado tras el primer usuario."""


class InvalidCredentialsError(AuthError):
    """Email, contraseña o usuario inactivo."""
