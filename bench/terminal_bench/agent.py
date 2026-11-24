"""Harbor installer for the Clover compacting mini-swe-agent."""

from pathlib import Path

from harbor.agents.installed.mini_swe_agent import MiniSweAgent


class CloverMiniSweAgent(MiniSweAgent):
    async def install(self, environment):
        await super().install(environment)
        await environment.upload_file(
            Path(__file__).with_name("compaction.py"), "/tmp/clover_compaction.py"
        )
        await self.exec_as_agent(environment, command=r"""
set -eu
. "$HOME/.local/bin/env"
python="$(uv tool dir)/mini-swe-agent/bin/python"
"$python" - <<'PY'
from pathlib import Path
import minisweagent.models.litellm_model as model

path = Path(model.__file__)
path.with_name("clover_compaction.py").write_bytes(Path("/tmp/clover_compaction.py").read_bytes())
hook = '''
from minisweagent.models.clover_compaction import compact_messages

class CloverCompactingModel(LitellmModel):
    def _prepare_messages_for_api(self, messages):
        return compact_messages(super()._prepare_messages_for_api(messages))

LitellmModel = CloverCompactingModel
'''
if "class CloverCompactingModel" not in path.read_text():
    with path.open("a") as source:
        source.write(hook)
PY
"$python" -c 'from minisweagent.models.litellm_model import LitellmModel; assert LitellmModel.__name__ == "CloverCompactingModel"'
""")
