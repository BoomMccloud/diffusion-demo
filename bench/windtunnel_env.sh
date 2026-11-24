# Source before running WindTunnel on macOS with podman.
# Uses the Docker CLI (brew install docker) against podman's Docker-compatible socket,
# because podman's own CLI omits the sha256: prefix the capsule image checks expect.
export PATH="/opt/homebrew/opt/gnu-tar/libexec/gnubin:/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"
# A clean CLI config avoids the leftover Docker Desktop credsStore in ~/.docker.
export DOCKER_CONFIG="$HOME/.cache/windtunnel/docker-config"
export DOCKER_HOST="unix://$(podman machine inspect --format '{{.ConnectionInfo.PodmanSocket.Path}}')"
# Point the wm-claude arm at the hosted diffusion model (SGLang serves /v1/messages).
if [ -n "${DIFFUSION_BASE_URL:-}" ]; then
  _base="${DIFFUSION_BASE_URL%/chat/completions}"
  export ANTHROPIC_BASE_URL="${_base%/v1}" ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-dummy}"
  unset _base
fi
