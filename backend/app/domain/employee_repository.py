"""Acceso a datos de empleados."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.payroll import Employee


class EmployeeRepository:
    """CRUD básico de empleados con baja lógica."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> Employee:
        """Crea un empleado y confirma la transacción."""
        employee = Employee(**values)
        self.db.add(employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def get_by_id(self, employee_id: UUID) -> Employee | None:
        """Obtiene un empleado por id, activo o inactivo."""
        return self.db.get(Employee, employee_id)

    def list_employees(
        self,
        *,
        limit: int,
        offset: int,
        is_active: bool | None = None,
    ) -> list[Employee]:
        """Lista empleados con filtro opcional por estado."""
        statement = select(Employee)
        if is_active is not None:
            statement = statement.where(Employee.is_active.is_(is_active))
        statement = (
            statement.order_by(Employee.last_name, Employee.first_name, Employee.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def list_active(self) -> list[Employee]:
        """Empleados que participan en la liquidación de nómina."""
        statement = (
            select(Employee)
            .where(Employee.is_active.is_(True))
            .order_by(Employee.last_name, Employee.first_name, Employee.id)
        )
        return list(self.db.scalars(statement).all())

    def update(self, employee_id: UUID, values: dict[str, Any]) -> Employee:
        """Actualiza campos editables y confirma la transacción."""
        employee = self.get_by_id(employee_id)
        if employee is None:
            raise ResourceNotFoundError("Empleado no encontrado")
        for field, value in values.items():
            setattr(employee, field, value)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def deactivate(self, employee_id: UUID) -> None:
        """Baja lógica: conserva al empleado y su historial de nómina."""
        employee = self.get_by_id(employee_id)
        if employee is None:
            raise ResourceNotFoundError("Empleado no encontrado")
        if employee.is_active:
            employee.is_active = False
            self.db.commit()

    def rollback(self) -> None:
        """Revierte la transacción en curso tras un error de integridad."""
        self.db.rollback()
