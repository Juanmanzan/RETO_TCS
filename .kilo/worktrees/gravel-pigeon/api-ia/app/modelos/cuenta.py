from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.infraestructura.postgres.base import Base


## modelo de la tabla cuentas
class Cuenta(Base):
    __tablename__ = "cuentas"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    cliente_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("clientes.id"),
        nullable=False,
        index=True,
    )

    tipo_cuenta: Mapped[str] = mapped_column(
        Enum(
            "AHORROS",
            "CORRIENTE",
            name="tipo_cuenta_enum",
            create_type=False,
        ),
        nullable=False,
    )

    saldo_centavos: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
