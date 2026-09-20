from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.esquemas.recomendaciones import RespuestaRecomendacion
from app.modelos.recomendacion_ia import RecomendacionIa


@dataclass(frozen=True)
class ResultadoPersistenciaRecomendacion:
    recomendacion_id: int | None
    insertada: bool


## guarda la recomendacion generada por la ia
async def insertar_recomendacion(
    sesion: AsyncSession,
    recomendacion: RespuestaRecomendacion,
) -> ResultadoPersistenciaRecomendacion:

    recomendacion_ia = RecomendacionIa(
        cliente_id=recomendacion.id_usuario,
        transaccion_id=recomendacion.transaccion_id,
        capacidad_financiera=(
            recomendacion.capacidad_financiera
        ),
        impacto_liquidez=recomendacion.impacto_liquidez,
        recomendacion=recomendacion.recomendacion,
        version_modelo=recomendacion.version_modelo,
    )

    sesion.add(
        recomendacion_ia
    )

    await sesion.commit()

    await sesion.refresh(
        recomendacion_ia
    )

    return ResultadoPersistenciaRecomendacion(
        recomendacion_id=recomendacion_ia.id,
        insertada=True,
    )
