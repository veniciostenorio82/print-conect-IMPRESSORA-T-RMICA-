#!/usr/bin/env bash
set -e

# Pede sudo automaticamente
if [ "$EUID" -ne 0 ]; then
  exec sudo "$0" "$@"
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_SRC="$DIR/sandubaria-print"
INSTALL_DIR="/opt/sandubaria-print"

if [ ! -f "$BIN_SRC" ]; then
  echo "Executável 'sandubaria-print' não encontrado ao lado do install.sh."
  exit 1
fi

# 1. Programa
mkdir -p "$INSTALL_DIR"
install -m 755 "$BIN_SRC" "$INSTALL_DIR/sandubaria-print"

ICON="printer"
if [ -f "$DIR/sandubaria-print.png" ]; then
  install -m 644 "$DIR/sandubaria-print.png" "$INSTALL_DIR/icon.png"
  ICON="$INSTALL_DIR/icon.png"
fi

# 2. Permissão da impressora (qualquer usuário logado na sessão gráfica)
cat > /etc/udev/rules.d/99-sandubaria-print.rules <<'EOF'
SUBSYSTEM=="usbmisc", KERNEL=="lp[0-9]*", TAG+="uaccess"
EOF
udevadm control --reload-rules
udevadm trigger --subsystem-match=usbmisc

# 3. Ícone no menu de aplicativos
cat > /usr/share/applications/sandubaria-print.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Sandubaria Print
Comment=Agente de impressão do PDV
Exec=$INSTALL_DIR/sandubaria-print
Icon=$ICON
Terminal=false
Categories=Utility;
EOF

# 4. Início automático com o sistema (todos os usuários), já minimizado
cat > /etc/xdg/autostart/sandubaria-print.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Sandubaria Print
Exec=$INSTALL_DIR/sandubaria-print --minimized
Icon=$ICON
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Instalado. Procure 'Sandubaria Print' no menu de aplicativos."
echo "Ele também iniciará sozinho no próximo login."