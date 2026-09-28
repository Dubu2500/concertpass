from fastapi import FastAPI

app = FastAPI(title="ticket-checkout")


@app.post("/checkout")
def checkout():
    # Endpoint de prueba: siempre responde 200
    return {"status": "success"}
