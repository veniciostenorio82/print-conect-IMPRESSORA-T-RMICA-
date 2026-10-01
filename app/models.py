from datetime import datetime
from pydantic import BaseModel


class PrintRequest(BaseModel):
    text: str


class Product(BaseModel):
    name: str
    price: float


class OrderItem(BaseModel):
    product: Product
    quantity: int
    observations: str | None = None


class PaymentEntry(BaseModel):
    method: str
    amount: float
    cashReceived: float | None = None
    change: float | None = None


class OrderRequest(BaseModel):
    items: list[OrderItem]
    payments: list[PaymentEntry] = []
    createdAt: datetime | None = None
    orderNumber: str | None = None