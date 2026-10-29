"""Punto de entrada: `python main.py` o `uvicorn main:app`."""
import uvicorn

from nutripae.config import cargar
from nutripae.web.app import crear_app

app = crear_app(cargar())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
