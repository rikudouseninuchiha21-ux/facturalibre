"""Errores de dominio compartidos por los repositorios."""


class ResourceNotFoundError(Exception):
    """El recurso no existe o está eliminado lógicamente."""


class VersionConflictError(Exception):
    """La versión enviada no coincide con la versión actual del recurso."""
