import os
import shutil
import socket
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox

import uvicorn

from app.main import app
from app.printer import print_text, printer_status

HOST, PORT = "127.0.0.1", 8000
INSTALL_BIN = "/opt/sandubaria-print/sandubaria-print"

UDEV_SCRIPT = r"""
set -eu
cat > /etc/udev/rules.d/99-sandubaria-print.rules <<'EOF'
SUBSYSTEM=="usbmisc", KERNEL=="lp[0-9]*", TAG+="uaccess"
EOF
udevadm control --reload-rules
udevadm trigger --subsystem-match=usbmisc
"""

INSTALL_SCRIPT = r"""
set -eu
SRC="$1"
install -d -m 755 /opt/sandubaria-print
install -m 755 "$SRC" /opt/sandubaria-print/sandubaria-print
cat > /etc/udev/rules.d/99-sandubaria-print.rules <<'EOF'
SUBSYSTEM=="usbmisc", KERNEL=="lp[0-9]*", TAG+="uaccess"
EOF
udevadm control --reload-rules
udevadm trigger --subsystem-match=usbmisc
cat > /usr/share/applications/sandubaria-print.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Sandubaria Print
Comment=Agente de impressão do PDV
Exec=/opt/sandubaria-print/sandubaria-print
Icon=printer
Terminal=false
Categories=Utility;
EOF
cat > /etc/xdg/autostart/sandubaria-print.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Sandubaria Print
Exec=/opt/sandubaria-print/sandubaria-print --minimized
Icon=printer
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
"""

PRINTER_LABELS = {
    "ok": ("● Impressora: conectada", "green"),
    "missing": ("● Impressora: não encontrada", "red"),
    "denied": ("● Impressora: sem permissão", "red"),
    "error": ("● Impressora: indisponível", "red"),
}


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_installed() -> bool:
    if not is_frozen():
        return False
    return os.path.realpath(sys.executable) == os.path.realpath(INSTALL_BIN)


def port_in_use() -> bool:
    with socket.socket() as s:
        return s.connect_ex((HOST, PORT)) == 0


def start_server() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def run_as_admin(script: str, *args: str) -> str | None:
    pkexec = shutil.which("pkexec")
    if pkexec is None:
        return "Este computador não mostrou o pedido de senha. Instale o PolicyKit (pkexec)."
    result = subprocess.run(
        [pkexec, "/bin/sh", "-c", script, "sh", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return None
    if result.returncode in (126, 127) and not (result.stderr or "").strip():
        return "Operação cancelada."
    detail = (result.stderr or result.stdout or "").strip()
    return detail or "A operação não foi concluída."


class Window(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Sandubaria Print")
        self.resizable(False, False)
        self.did_install = is_installed()
        self._setup_mode: str | None = None

        tk.Label(self, text="Sandubaria Print", font=("Sans", 16, "bold")).pack(pady=(15, 5))
        self.agent_lbl = tk.Label(self, font=("Sans", 11))
        self.agent_lbl.pack(pady=3)
        self.printer_lbl = tk.Label(self, font=("Sans", 11))
        self.printer_lbl.pack(pady=3)
        tk.Label(
            self,
            text="Abra o PDV no navegador deste computador.\nA impressão passa por este programa.",
            justify="center",
        ).pack(pady=(8, 4))
        self.hint_lbl = tk.Label(self, text="", justify="center", wraplength=360)
        self.hint_lbl.pack(pady=(0, 4))

        tk.Button(self, text="Imprimir teste", command=self.test_print).pack(pady=(8, 4))
        self.setup_btn = tk.Button(self)
        self.quit_btn = tk.Button(self, text="Sair (parar impressão)", command=self.quit_app)
        self.quit_btn.pack(pady=(4, 12))

        self.protocol("WM_DELETE_WINDOW", self.iconify)
        self._apply_status()
        self.after(3000, self.refresh)

    def _set_setup(self, mode: str | None) -> None:
        if mode == self._setup_mode:
            return
        self._setup_mode = mode
        if mode is None:
            self.setup_btn.pack_forget()
        else:
            if mode == "install":
                self.setup_btn.config(text="Instalar neste computador", command=self.install_here)
            else:
                self.setup_btn.config(text="Permitir impressora", command=self.allow_printer)
            if not self.setup_btn.winfo_ismapped():
                self.setup_btn.pack(pady=(4, 4), before=self.quit_btn)
        self.geometry("400x340" if mode else "400x280")

    def refresh(self) -> None:
        self._apply_status()
        self.after(3000, self.refresh)

    def _apply_status(self) -> None:
        self.agent_lbl.config(text="● Agente: rodando", fg="green")
        state = printer_status()
        text, color = PRINTER_LABELS.get(state, PRINTER_LABELS["error"])
        self.printer_lbl.config(text=text, fg=color)

        if is_frozen() and not self.did_install:
            self._set_setup("install")
            self.hint_lbl.config(
                text="Clique em instalar e informe a senha. O programa entra no menu e abre sozinho no próximo login."
            )
        elif state == "denied":
            self._set_setup("allow")
            self.hint_lbl.config(text="A impressora está conectada, mas este usuário ainda não pode usá-la.")
        else:
            self._set_setup(None)
            if state == "missing":
                self.hint_lbl.config(text="Conecte a impressora USB e ligue-a.")
            elif self.did_install:
                self.hint_lbl.config(text="Este computador já está preparado.")
            else:
                self.hint_lbl.config(text="")

    def install_here(self) -> None:
        self.setup_btn.config(state="disabled")
        self.update_idletasks()
        error = run_as_admin(INSTALL_SCRIPT, sys.executable)
        self.setup_btn.config(state="normal")
        if error:
            messagebox.showerror("Instalação", error)
            return
        self.did_install = True
        self._apply_status()
        messagebox.showinfo(
            "Sandubaria Print",
            "Instalado.\n\nProcure Sandubaria Print no menu de aplicativos. "
            "Ele também abrirá sozinho no próximo login.\n\n"
            "Pode continuar usando esta janela agora.",
        )

    def allow_printer(self) -> None:
        self.setup_btn.config(state="disabled")
        self.update_idletasks()
        error = run_as_admin(UDEV_SCRIPT)
        self.setup_btn.config(state="normal")
        if error:
            messagebox.showerror("Impressora", error)
            return
        self._apply_status()
        messagebox.showinfo(
            "Sandubaria Print",
            "Permissão concedida.\n\nSe a impressora continuar sem acesso, desconecte e conecte o cabo USB.",
        )

    def test_print(self) -> None:
        try:
            print_text("TESTE SANDUBARIA\nAcentos: ção ã é")
        except OSError as e:
            messagebox.showerror("Erro", f"Não foi possível imprimir:\n{e}")

    def quit_app(self) -> None:
        if messagebox.askyesno("Sair", "Sem o agente, o PDV não consegue imprimir. Sair mesmo?"):
            self.destroy()
            sys.exit(0)


def main() -> None:
    if port_in_use():
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Sandubaria Print", "O agente já está em execução.")
        sys.exit(0)

    threading.Thread(target=start_server, daemon=True).start()
    win = Window()
    if "--minimized" in sys.argv:
        win.iconify()
    win.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Sandubaria Print", str(exc))
        raise
