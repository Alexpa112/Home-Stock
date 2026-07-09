"""Punto de entrada: arranca el servidor de desarrollo de Flask."""
import os

from stockhogar import create_app

app = create_app()

if __name__ == "__main__":
    # host 0.0.0.0 para poder acceder desde otros dispositivos de la red local
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
