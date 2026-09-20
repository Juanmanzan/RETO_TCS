from fastapi import FastAPI

from app.rutas.listar_cuentas import (router as router_cuentas,)
from app.rutas.transacciones import (router as router_transacciones,)

## registra las rutas disponibles en la aplicacion
def registrar_rutas(app: FastAPI) -> None:
    app.include_router(
        router_cuentas
    )

    app.include_router(
        router_transacciones
    )
