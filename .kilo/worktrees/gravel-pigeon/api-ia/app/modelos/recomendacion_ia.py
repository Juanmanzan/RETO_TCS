from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.infraestructura.postgres.base import Base


## modelo de la tabla recomendaciones_ia
class RecomendacionIa(Base):
    __tablename__ = "recomendaciones_ia"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    cliente_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("clientes.id"),
        nullable=False,
    )

    transaccion_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("transacciones.transaccion_id"),
        nullable=False,
    )

    capacidad_financiera: Mapped[str] = mapped_column(
        Enum(
            "FAVORABLE",
            "MODERADA",
            "REDUCIDA",
            name="capacidad_financiera_enum",
            create_type=False,
        ),
        nullable=False,
    )

    impacto_liquidez: Mapped[str] = mapped_column(
        Enum(
            "BAJO",
            "MODERADO",
            "ALTO",
            name="impacto_liquidez_enum",
            create_type=False,
        ),
        nullable=False,
    )

    recomendacion: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    version_modelo: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'reglas-v1'"),
    )

    generado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
