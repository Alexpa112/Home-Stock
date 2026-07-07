"""Punto de entrada: arranca el servidor de desarrollo de Flask."""
from stockhogar import create_app

app = create_app()

if __name__ == "__main__":
    # host 0.0.0.0 para poder acceder desde otros dispositivos de la red local
    app.run(host="0.0.0.0", port=5000, debug=False)
