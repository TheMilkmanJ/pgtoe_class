#!/usr/bin/env bash
# =============================================================================
#  CosmicDashboard — Robust Launcher
#  • Auto-starts the FastAPI backend (cosmo_dashboard_backend.py)
#  • Auto-starts a localtunnel for phone/remote access
#  • Injects the tunnel URL directly into the backend via /api/set_tunnel_url
#  • Restarts either service automatically if it crashes
#  • Opens the dashboard in the browser on launch
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_SCRIPT="$SCRIPT_DIR/scripts/cosmo_dashboard_backend.py"
BACKEND_URL="http://localhost:8000"
BACKEND_LOG="$SCRIPT_DIR/chains/dashboard_backend.log"
TUNNEL_LOG="$SCRIPT_DIR/chains/dashboard_tunnel.log"
PORT=8000
RESTART_DELAY=5   # seconds to wait before restarting a crashed service

# Set Python path to pgtoe_gold conda environment directly to avoid shell function activation crashes
if [ -f "/home/themilkmanj/miniconda3/envs/pgtoe_gold/bin/python3" ]; then
    PYTHON="/home/themilkmanj/miniconda3/envs/pgtoe_gold/bin/python3"
else
    PYTHON=$(command -v python3 || command -v python)
fi
NPX=$(command -v npx || true)

mkdir -p "$SCRIPT_DIR/chains"

# ---------------------------------------------------------------------------
# Dashboard HTTP Basic Auth credentials (prevents repeated login prompts)
# ---------------------------------------------------------------------------
# If the user has not exported DASHBOARD_PASS, generate ONE stable password
# for the lifetime of this launcher session and export it. The backend child
# process (and any watcher restarts) will inherit it and skip its own random
# generation. The same value is used by the health-check curls below.
if [ -z "${DASHBOARD_PASS:-}" ]; then
    DASHBOARD_PASS=$(python3 -c "
import secrets, string
# Use a shorter, user-friendly random password (alphanum + safe symbols)
alphabet = string.ascii_letters + string.digits + '-_'
print(''.join(secrets.choice(alphabet) for _ in range(12)))
")
    echo "==========================================================================="
    echo " COSMICDASHBOARD LOGIN CREDENTIALS (stable for this launcher run)"
    echo ""
    echo "   Username : ${DASHBOARD_USER:-admin}"
    echo "   Password : $DASHBOARD_PASS"
    echo ""
    echo "   (Enter these when your browser prompts for login.)"
    echo "   To use your own fixed password every time, run before the launcher:"
    echo "     export DASHBOARD_USER=yourname"
    echo "     export DASHBOARD_PASS=your-memorable-password"
    echo ""
    echo "   Credentials also written to chains/dashboard_credentials.txt"
    echo "==========================================================================="
    echo "$DASHBOARD_PASS" > "$SCRIPT_DIR/chains/dashboard_credentials.txt"
    chmod 600 "$SCRIPT_DIR/chains/dashboard_credentials.txt" 2>/dev/null || true
fi

export DASHBOARD_USER="${DASHBOARD_USER:-admin}"
export DASHBOARD_PASS
export DASHBOARD_WORKSPACE_ROOT="${DASHBOARD_WORKSPACE_ROOT:-$(pwd)}"

# ---------------------------------------------------------------------------
# Cleanup: kill background workers on exit
# ---------------------------------------------------------------------------
BACKEND_PID=""
TUNNEL_PID=""
BACKEND_WATCHER_PID=""
TUNNEL_WATCHER_PID=""

cleanup() {
    echo ""
    echo "[CosmicDashboard] Shutting down..."
    [ -n "$BACKEND_WATCHER_PID" ] && kill "$BACKEND_WATCHER_PID" 2>/dev/null || true
    [ -n "$TUNNEL_WATCHER_PID"  ] && kill "$TUNNEL_WATCHER_PID"  2>/dev/null || true
    [ -n "$BACKEND_PID" ]         && kill "$BACKEND_PID"         2>/dev/null || true
    [ -n "$TUNNEL_PID"  ]         && kill "$TUNNEL_PID"          2>/dev/null || true
    echo "[CosmicDashboard] Goodbye."
    exit 0
}
trap cleanup SIGINT SIGTERM

# ---------------------------------------------------------------------------
# Wait for the backend to respond (with timeout)
# ---------------------------------------------------------------------------
wait_for_backend() {
    local deadline=$((SECONDS + 30))
    while [ $SECONDS -lt $deadline ]; do
        if curl -s --max-time 2 -u "${DASHBOARD_USER:-}:${DASHBOARD_PASS:-}" \
               "$BACKEND_URL/api/status" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

# ---------------------------------------------------------------------------
# Start / restart the backend in a loop (watchdog)
# ---------------------------------------------------------------------------
run_backend_watcher() {
    while true; do
        echo "[Backend] Starting cosmo_dashboard_backend.py..."
        "$PYTHON" "$BACKEND_SCRIPT" \
            >> "$BACKEND_LOG" 2>&1 &
        BACKEND_PID=$!
        echo "[Backend] PID=$BACKEND_PID  (log: $BACKEND_LOG)"
        wait "$BACKEND_PID" 2>/dev/null || true
        echo "[Backend] Process exited. Restarting in ${RESTART_DELAY}s..."
        sleep "$RESTART_DELAY"
    done
}

# ---------------------------------------------------------------------------
# Parse the localtunnel URL from its stdout and push it to the backend
# ---------------------------------------------------------------------------
push_tunnel_url() {
    local url="$1"
    # Retry a few times in case the backend isn't quite ready yet
    for _ in 1 2 3 4 5; do
        local result
        result=$(curl -s --max-time 5 \
            -u "${DASHBOARD_USER:-}:${DASHBOARD_PASS:-}" \
            -X POST "$BACKEND_URL/api/set_tunnel_url" \
            -H "Content-Type: application/json" \
            -d "{\"url\": \"$url\"}" 2>&1)
        if echo "$result" | grep -q '"status":"success"'; then
            echo "[Tunnel] URL pushed to backend: $url"
            return 0
        fi
        sleep 2
    done
    echo "[Tunnel] Warning: could not push URL to backend (backend may still be starting)"
}

# ---------------------------------------------------------------------------
# Start / restart localtunnel in a loop (watchdog)
# ---------------------------------------------------------------------------
run_tunnel_watcher() {
    if [ -z "$NPX" ]; then
        echo "[Tunnel] npx not found — phone link unavailable. Install Node.js to enable."
        return
    fi

    while true; do
        echo "[Tunnel] Starting localtunnel on port $PORT..."
        # Run localtunnel and capture its output while also logging it
        local tmpfifo
        tmpfifo=$(mktemp -u)
        mkfifo "$tmpfifo"

        npx localtunnel --port "$PORT" >"$tmpfifo" 2>>"$TUNNEL_LOG" &
        TUNNEL_PID=$!

        # Read localtunnel's output to grab the URL
        while IFS= read -r line; do
            echo "[Tunnel] $line" | tee -a "$TUNNEL_LOG"
            # localtunnel prints: "your url is: https://xxxx.loca.lt"
            if [[ "$line" =~ (https?://[a-zA-Z0-9\-]+\.loca\.lt) ]]; then
                local tunnel_url="${BASH_REMATCH[1]}"
                push_tunnel_url "$tunnel_url"
            fi
        done <"$tmpfifo" &

        rm -f "$tmpfifo"
        wait "$TUNNEL_PID" 2>/dev/null || true
        TUNNEL_PID=""
        echo "[Tunnel] localtunnel exited. Restarting in ${RESTART_DELAY}s..."
        # Clear stale URL from backend
        curl -s --max-time 5 \
            -u "${DASHBOARD_USER:-}:${DASHBOARD_PASS:-}" \
            -X POST "$BACKEND_URL/api/set_tunnel_url" \
            -H "Content-Type: application/json" \
            -d '{"url": ""}' >/dev/null 2>&1 || true
        sleep "$RESTART_DELAY"
    done
}

# ---------------------------------------------------------------------------
# Open browser
# ---------------------------------------------------------------------------
open_browser() {
    if wait_for_backend; then
        echo "[Browser] Dashboard is up — opening $BACKEND_URL"
        if command -v xdg-open &>/dev/null; then
            xdg-open "$BACKEND_URL" &
        elif command -v open &>/dev/null; then
            open "$BACKEND_URL" &
        else
            echo "[Browser] Could not detect a browser opener. Navigate to $BACKEND_URL manually."
        fi
    else
        echo "[Browser] Backend did not start in time — skipping auto-open. Navigate to $BACKEND_URL manually."
    fi
}

# ---------------------------------------------------------------------------
# Check if backend is already running; if so, just open the browser
# ---------------------------------------------------------------------------
echo "==================================================="
echo "       CosmicDashboard — Robust Launcher"
echo "==================================================="
echo ""

if wait_for_backend 2>/dev/null; then
    echo "[Backend] Already running at $BACKEND_URL"
    open_browser
else
    # Kill any stale backend on our port first
    fuser -k "${PORT}/tcp" 2>/dev/null || true
    sleep 1

    # Start the backend watchdog in background
    run_backend_watcher &
    BACKEND_WATCHER_PID=$!

    # Open the browser once the backend is ready
    open_browser
fi

# Start the tunnel watchdog in background
run_tunnel_watcher &
TUNNEL_WATCHER_PID=$!

echo ""
echo "[CosmicDashboard] All services running. Press Ctrl+C to stop."
echo "  Dashboard:  $BACKEND_URL"
echo "  Backend log: $BACKEND_LOG"
echo "  Tunnel log:  $TUNNEL_LOG"
echo ""

# Wait forever (until Ctrl+C)
while true; do
    sleep 60
done
