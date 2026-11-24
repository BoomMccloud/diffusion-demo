"""Use Harbor's Pi adapter with the Clover Chat Completions relay."""

import json
from pathlib import Path
import shlex

from harbor.agents.installed.pi import Pi

from .pi_relay import BASE_URL, MODEL, SETTINGS


class CloverPi(Pi):
    upstream = ("43.107.54.53", 31002)

    async def _write_custom_models_json(self, environment, models_json):
        provider, = models_json["providers"].values()
        if provider["baseUrl"] != BASE_URL:
            raise ValueError("CloverPi must be configured with its loopback relay URL")
        for model in provider["models"]:
            model.update(MODEL)
        await super()._write_custom_models_json(environment, models_json)
        await self._upload_config_text(
            environment, content=json.dumps(SETTINGS),
            remote_path="/tmp/harbor-pi-agent/settings.json", filename="settings.json",
        )
        await environment.upload_file(
            Path(__file__).with_name("pi_relay.py"), "/tmp/clover_pi_relay.py"
        )
        session = shlex.quote(str(self.session_id))
        endpoint = shlex.join(map(str, self.upstream))
        log_path = shlex.quote(str(self.environment_logs_dir / "clover-api.jsonl"))
        await self.exec_as_agent(environment, command=f"""
set -eu
mkdir -p {shlex.quote(str(self.environment_logs_dir))}
nohup python3 /tmp/clover_pi_relay.py {session} {endpoint} > {log_path} 2>&1 </dev/null &
python3 - <<'PY'
import time
import urllib.error
import urllib.request

for _ in range(30):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8741/health", timeout=1):
            break
    except urllib.error.URLError:
        time.sleep(0.2)
else:
    raise SystemExit("Clover relay failed to start")
PY
""")


class MiniCPMPi(CloverPi):
    upstream = ("/gateway/minicpm.sock",)
