#!/usr/bin/env bash
# Start an isolated X11 display on a real Linux kernel (WSL2 / VM / server).
# This does not install system packages or change the machine's desktop session.
set -euo pipefail

if [[ "$(uname -s)" != Linux ]]; then
    echo 'Run this script inside Ubuntu / Linux, not Windows or macOS.' >&2
    exit 1
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_dir=$(cd -- "$script_dir/.." && pwd)
cd -- "$project_dir"
if [[ $# -eq 0 ]]; then
    echo 'Usage: bash scripts/start-linux-x11.sh --server URL --token-file PATH [--name NAME]'
    exit 2
fi
for command_name in python3 xvfb-run xauth dbus-run-session; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Missing dependency: $command_name. See docs/multiplatform.md." >&2
        exit 1
    fi
done
/usr/bin/python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11 or newer is required; Ubuntu 24.04 is recommended.')
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Atspi', '2.0')
from gi.repository import Gtk, Atspi
PY

# Keep the Linux environment off Windows-mounted filesystems.
node_root=${PROOFLANE_LINUX_NODE_ROOT:-"$HOME/.local/share/prooflane-linux"}
mkdir -p -- "$node_root"
if [[ ! -x "$node_root/venv/bin/python" ]]; then
    /usr/bin/python3 -m venv --system-site-packages "$node_root/venv"
fi
source "$node_root/venv/bin/activate"
python -m pip install -r requirements-linux.txt
export NO_AT_BRIDGE=0
export GTK_MODULES=atk-bridge
export GDK_BACKEND=x11
unset WAYLAND_DISPLAY
echo 'Starting Linux X11 node. Stop with Ctrl+C. Output is real Linux GUI evidence.'
exec xvfb-run -a -s '-screen 0 1280x900x24 +extension Composite -nolisten tcp' \
    dbus-run-session -- python -m prooflane.agent --data "$node_root/agent-data" "$@"
