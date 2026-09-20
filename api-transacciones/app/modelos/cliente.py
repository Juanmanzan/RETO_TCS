from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.infraestructura.postgres.base import Base


## modelo de la tabla clientes
class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    apellido: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
    )

    ingresos_mensuales: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    gastos_mensuales: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
