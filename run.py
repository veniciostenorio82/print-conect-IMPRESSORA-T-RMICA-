import socket
import sys
import threading
import tkinter as tk
from tkinter import messagebox

import uvicorn

from app.main import app
from app.printer import printer_available, print_text

HOST, PORT = "127.0.0.1", 8000


def port_in_use() -> bool:
    with socket.socket() as s:
        return s.connect_ex((HOST, PORT)) == 0


def start_server() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


class Window(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Sandubaria Print")
        self.geometry("320x230")
        self.resizable(False, False)

        tk.Label(self, text="Sandubaria Print", font=("Sans", 16, "bold")).pack(pady=(15, 5))
        self.agent_lbl = tk.Label(self, font=("Sans", 11))
        self.agent_lbl.pack(pady=3)
        self.printer_lbl = tk.Label(self, font=("Sans", 11))
        self.printer_lbl.pack(pady=3)

        tk.Button(self, text="Imprimir teste", command=self.test_print).pack(pady=(12, 4))
        tk.Button(self, text="Sair (parar impressão)", command=self.quit_app).pack()

        # Fechar no X apenas minimiza; o agente continua rodando
        self.protocol("WM_DELETE_WINDOW", self.iconify)
        self.refresh()

    def refresh(self) -> None:
        self.agent_lbl.config(text="● Agente: rodando", fg="green")
        ok = printer_available()
        self.printer_lbl.config(
            text="● Impressora: conectada" if ok else "● Impressora: não encontrada",
            fg="green" if ok else "red",
        )
        self.after(3000, self.refresh)

    def test_print(self) -> None:
        try:
            print_text("TESTE SANDUBARIA\nAcentos: ção ã é")
        except OSError as e:
            messagebox.showerror("Erro", f"Não foi possível imprimir:\n{e}")

    def quit_app(self) -> None:
        if messagebox.askyesno("Sair", "Sem o agente, o PWA não consegue imprimir. Sair mesmo?"):
            self.destroy()
            sys.exit(0)


if __name__ == "__main__":
    if port_in_use():
        # Já existe uma instância rodando; evita duplicar
        tk.Tk().withdraw()
        messagebox.showinfo("Sandubaria Print", "O agente já está em execução.")
        sys.exit(0)

    threading.Thread(target=start_server, daemon=True).start()

    win = Window()
    if "--minimized" in sys.argv:  # usado na inicialização automática
        win.iconify()
    win.mainloop()