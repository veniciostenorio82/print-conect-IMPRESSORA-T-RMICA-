#!/usr/bin/env bash
set -e
if [ "$EUID" -ne 0 ]; then exec sudo "$0" "$@"; fi

pkill -f /opt/sandubaria-print/sandubaria-print || true
rm -rf /opt/sandubaria-print
rm -f /etc/udev/rules.d/99-sandubaria-print.rules
rm -f /usr/share/applications/sandubaria-print.desktop
rm -f /etc/xdg/autostart/sandubaria-print.desktop
udevadm control --reload-rules
echo "Removido."