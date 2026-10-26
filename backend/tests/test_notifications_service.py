"""Tests unitarios del servicio de notificaciones in-app."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.application.notification_service import NotificationService
from app.domain.models.auth import User, UserRole
from app.domain.models.notification import NotificationSeverity


def _make_user(db_session: Session, *, role: UserRole, active: bool = True) -> User:
    user = User(
        email=f"{role.value.lower()}-{uuid4()}@example.com",
        hashed_password="dummy-hash",
        full_name=f"Usuario {role.value}",
        role=role,
        is_active=active,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_create_persists_and_returns(db_session: Session) -> None:
    user = _make_user(db_session, role=UserRole.ADMIN)
    service = NotificationService(db_session)

    notification = service.create(
        user_id=user.id,
        category="BUDGET_APPROVED",
        severity=NotificationSeverity.INFO,
        title="Presupuesto aprobado",
        body="El presupuesto de Administración fue aprobado.",
        link="/budgets/123",
    )

    assert notification.id is not None
    assert notification.user_id == user.id
    assert notification.category == "BUDGET_APPROVED"
    assert notification.severity == NotificationSeverity.INFO
    assert notification.read_at is None

    fetched = service.list_for_user(user_id=user.id)
    assert [item.id for item in fetched] == [notification.id]


def test_create_for_roles_creates_one_per_active_user(
    db_session: Session,
) -> None:
    active_admin = _make_user(db_session, role=UserRole.ADMIN)
    active_accountant = _make_user(db_session, role=UserRole.ACCOUNTANT)
    inactive_accountant = _make_user(db_session, role=UserRole.ACCOUNTANT, active=False)
    cashier = _make_user(db_session, role=UserRole.CASHIER)
    service = NotificationService(db_session)

    created = service.create_for_roles(
        roles=[UserRole.ADMIN, UserRole.ACCOUNTANT],
        category="BUDGET_ALERT",
        severity=NotificationSeverity.WARNING,
        title="Presupuesto en nivel WARNING",
    )

    # Una por usuario ACTIVO de los roles objetivo; el cajero no recibe.
    assert created == 2
    for user in (active_admin, active_accountant):
        notifications = service.list_for_user(user_id=user.id)
        assert len(notifications) == 1
        assert notifications[0].title == "Presupuesto en nivel WARNING"
    assert service.list_for_user(user_id=inactive_accountant.id) == []
    assert service.list_for_user(user_id=cashier.id) == []


def test_mark_read_requires_owner(db_session: Session) -> None:
    owner = _make_user(db_session, role=UserRole.ADMIN)
    other = _make_user(db_session, role=UserRole.ACCOUNTANT)
    service = NotificationService(db_session)
    notification = service.create(
        user_id=owner.id,
        category="BUDGET_ALERT",
        severity=NotificationSeverity.CRITICAL,
        title="Sobregiro",
    )

    # Otro usuario no puede marcar la notificación ajena.
    assert service.mark_read(notification_id=notification.id, user_id=other.id) is False
    assert notification.read_at is None

    # El dueño sí.
    assert service.mark_read(notification_id=notification.id, user_id=owner.id) is True
    assert notification.read_at is not None

    # Re-marcar la misma no cuenta de nuevo.
    assert service.mark_read(notification_id=notification.id, user_id=owner.id) is False


def test_mark_all_read_returns_count(db_session: Session) -> None:
    user = _make_user(db_session, role=UserRole.ACCOUNTANT)
    other = _make_user(db_session, role=UserRole.ADMIN)
    service = NotificationService(db_session)
    for _ in range(3):
        service.create(
            user_id=user.id,
            category="BUDGET_CLOSED",
            severity=NotificationSeverity.INFO,
            title="Cerrado",
        )
    service.create(
        user_id=other.id,
        category="BUDGET_CLOSED",
        severity=NotificationSeverity.INFO,
        title="Cerrado del otro usuario",
    )

    marked = service.mark_all_read(user_id=user.id)
    assert marked == 3
    assert service.unread_count(user_id=user.id) == 0
    # Las notificaciones del otro usuario quedan intactas.
    assert service.unread_count(user_id=other.id) == 1


def test_unread_count_and_filters(db_session: Session) -> None:
    user = _make_user(db_session, role=UserRole.ADMIN)
    service = NotificationService(db_session)
    first = service.create(
        user_id=user.id,
        category="A",
        severity=NotificationSeverity.INFO,
        title="Uno",
    )
    service.create(
        user_id=user.id,
        category="B",
        severity=NotificationSeverity.WARNING,
        title="Dos",
    )

    assert service.unread_count(user_id=user.id) == 2
    service.mark_read(notification_id=first.id, user_id=user.id)

    assert service.unread_count(user_id=user.id) == 1
    unread = service.list_for_user(user_id=user.id, unread_only=True)
    assert [item.title for item in unread] == ["Dos"]
    assert len(service.list_for_user(user_id=user.id)) == 2


def test_list_for_user_pagination(db_session: Session) -> None:
    user = _make_user(db_session, role=UserRole.ADMIN)
    service = NotificationService(db_session)
    for index in range(5):
        service.create(
            user_id=user.id,
            category="X",
            severity=NotificationSeverity.INFO,
            title=f"Notificación {index}",
        )

    page_one = service.list_for_user(user_id=user.id, limit=2, offset=0)
    page_two = service.list_for_user(user_id=user.id, limit=2, offset=2)
    rest = service.list_for_user(user_id=user.id, limit=2, offset=4)

    assert len(page_one) == 2
    assert len(page_two) == 2
    assert len(rest) == 1
    ids = [item.id for item in page_one + page_two + rest]
    assert len(set(ids)) == 5
