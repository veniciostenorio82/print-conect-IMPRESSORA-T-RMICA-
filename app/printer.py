import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

DEVICE = "/dev/usb/lp0"
WIDTH = 32
TZ = ZoneInfo("America/Sao_Paulo")  # mesmo fuso de Maceió

ESC_INIT = b"\x1b@"
ESC_CP860 = b"\x1bt\x03"
ALIGN_LEFT = b"\x1ba\x00"
ALIGN_CENTER = b"\x1ba\x01"
BOLD_ON = b"\x1bE\x01"
BOLD_OFF = b"\x1bE\x00"
DOUBLE_ON = b"\x1d!\x11"
DOUBLE_OFF = b"\x1d!\x00"
CUT = b"\x1dV\x42\x00"

DOUBLE_LINE = "=" * WIDTH
SINGLE_LINE = "-" * WIDTH

PAYMENT_NAMES = {
    "dinheiro": "DINHEIRO",
    "cartao-credito": "CARTÃO CRÉDITO",
    "cartao-debito": "CARTÃO DÉBITO",
    "pix": "PIX",
}


def _enc(text: str) -> bytes:
    return text.encode("cp860", errors="replace")


def _money(value: float) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


def _row(left: str, right: str) -> str:
    space = WIDTH - len(right) - 1
    return left[:space].ljust(space + 1) + right


def _local_date(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(TZ)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)  # o JS envia em UTC (Z); converte para o horário local


def printer_status() -> str:
    try:
        with open(DEVICE, "wb"):
            return "ok"
    except FileNotFoundError:
        return "missing"
    except PermissionError:
        return "denied"
    except OSError:
        return "error"


def printer_available() -> bool:
    return printer_status() == "ok"


def _send(data: bytes) -> None:
    with open(DEVICE, "wb") as printer:
        printer.write(data)


def print_text(text: str) -> None:
    _send(ESC_INIT + ESC_CP860 + _enc(text) + b"\n\n\n\n")


def print_order(order) -> None:
    out = ESC_INIT + ESC_CP860

    def line(text: str = "") -> None:
        nonlocal out
        out += _enc(text + "\n")

    subtotal = sum(i.product.price * i.quantity for i in order.items)
    discount = 0.0
    total = subtotal - discount

    # Cabeçalho
    out += ALIGN_CENTER
    line(DOUBLE_LINE)
    out += BOLD_ON + DOUBLE_ON
    line("SANDUBARIA")
    out += DOUBLE_OFF + BOLD_OFF
    line(DOUBLE_LINE)
    line()
    out += BOLD_ON
    line(f"PEDIDO Nº {order.orderNumber or '-'}")
    out += BOLD_OFF
    line(_local_date(order.createdAt).strftime("%d/%m/%Y %H:%M"))
    out += ALIGN_LEFT
    line()

    # Itens
    for item in order.items:
        label = f"{item.quantity}x {item.product.name}"
        price = _money(item.product.price * item.quantity)
        parts = textwrap.wrap(label, WIDTH - len(price) - 1) or [label]
        line(_row(parts[0], price))
        for extra in parts[1:]:
            line("   " + extra)
        if item.observations and item.observations.strip():
            for l in textwrap.wrap(f"Obs: {item.observations.strip()}", WIDTH - 3):
                line("   " + l)
    line()

    # Totais
    line(SINGLE_LINE)
    line(_row("SUBTOTAL", _money(subtotal)))
    line(_row("DESCONTO", _money(discount)))
    out += BOLD_ON
    line(_row("TOTAL", _money(total)))
    out += BOLD_OFF
    line(SINGLE_LINE)
    line()

    # Pagamentos
    for p in order.payments:
        line(f"PAGAMENTO: {PAYMENT_NAMES.get(p.method, p.method.upper())}")
        line(f"VALOR: {_money(p.amount)}")
        if p.cashReceived:
            line(f"RECEBIDO: {_money(p.cashReceived)}")
        if p.change:
            line(f"TROCO: {_money(p.change)}")
        line()

    out += ALIGN_CENTER
    line(DOUBLE_LINE)
    out += b"\n\n\n\n" + CUT
    _send(out)