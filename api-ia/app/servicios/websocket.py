from fastapi import WebSocket


class GestorWebSocket:

    def __init__(self) -> None:
        self._conexiones: list[WebSocket] = []

    async def conectar(
        self,
        websocket: WebSocket,
    ) -> None:

        await websocket.accept()

        self._conexiones.append(
            websocket
        )

    def desconectar(
        self,
        websocket: WebSocket,
    ) -> None:

        if websocket in self._conexiones:
            self._conexiones.remove(
                websocket
            )

    async def publicar(
        self,
        mensaje: dict,
    ) -> None:

        conexiones_caidas: list[WebSocket] = []

        for websocket in self._conexiones:

            try:

                await websocket.send_json(
                    mensaje
                )

            except RuntimeError:

                conexiones_caidas.append(
                    websocket
                )

        for websocket in conexiones_caidas:

            self.desconectar(
                websocket
            )


gestor_websocket = GestorWebSocket()
