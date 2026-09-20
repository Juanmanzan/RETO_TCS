from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.infraestructura.postgres.base import Base

## modelo de la tabla transacciones de SQl
class Transaccion(Base):
    __tablename__ = "transacciones"

    transaccion_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    trace_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    clave_idempotencia: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    cuenta_origen_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    cuenta_destino_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    monto_centavos: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    moneda: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        Enum(
            "COMPLETADA",
            "RECHAZADA",
            name="estado_transaccion_enum",
            create_type=False,
        ),
        nullable=False,
    )

    motivo: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )