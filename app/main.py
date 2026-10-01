from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import OrderRequest
from app.printer import printer_available, print_order as print_order_ticket, print_text


app = FastAPI(
    title="Sandubaria Print",
    description="Agente local de impressão do PDV",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pdv-sandubaria.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    # O PDV em HTTPS (Vercel) chama este agente em localhost.
    allow_private_network=True,
)


@app.get("/status")
def status():
    return {"agent": True, "printer": printer_available()}


@app.post("/print/order")
def print_order_route(order: OrderRequest):
    try:
        print_order_ticket(order)
    except OSError as e:
        raise HTTPException(status_code=503, detail=f"Impressora indisponível: {e}")
    return {"success": True, "message": "Pedido impresso"}


@app.post("/print/test")
def print_test():
    try:
        print_text("TESTE SANDUBARIA\nAcentos: ção ã é")
    except OSError as e:
        raise HTTPException(status_code=503, detail=f"Impressora indisponível: {e}")
    return {"success": True, "message": "Teste impresso"}
