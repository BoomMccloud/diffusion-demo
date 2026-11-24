set -euo pipefail
export HOME=/tmp/cbc-home PATH=/opt/codebuddy-code/bin:$PATH CODEBUDDY_AUTO_COMPACT_WINDOW=110000 CODEBUDDY_COMPUTER_USE_ENABLED=0 CODEBUDDY_WAIT_FOR_MCP_SERVERS_ENABLED=0 CODEBUDDY_CODE_DISABLE_SESSION_TITLE_REFRESH=1
mkdir -p "$HOME/.codebuddy" /workspace/output
python3 /run-pilot/socket-forward.py >/run-pilot/forward.log 2>&1 &
python3 - <<'PY'
import json,os,pathlib,time,urllib.request,urllib.error
home=pathlib.Path(os.environ['HOME'])/'.codebuddy'
model={'id':'clover-pilot','name':'clover-pilot','vendor':'OpenAI','url':'http://127.0.0.1:18767/v1/chat/completions','apiKey':'local-pilot','supportsToolCall':True,'supportsImages':False,'supportsReasoning':True,'temperature':0}
(home/'models.json').write_text(json.dumps({'models':[model],'availableModels':['clover-pilot']}))
settings={'alwaysThinkingEnabled':True,'autoUpdates':False,'autoCompactEnabled':True,'includeCoAuthoredBy':False,'promptSuggestionEnabled':False,'enableAllProjectMcpServers':False,'cleanupPeriodDays':3650,'permissions':{'defaultMode':'bypassPermissions','deny':['WebSearch','AskUserQuestion','Workflow','ComputerUse','WaitForMcpServers','EnterPlanMode']}}
(home/'settings.json').write_text(json.dumps(settings))
pathlib.Path('/workspace/pilot-mcp.json').write_text(json.dumps({'mcpServers':{'pilot-wps':{'type':'http','url':'http://127.0.0.1:18768/mcp','defer_loading':False}}}))
for port in (18767,18768):
 for attempt in range(30):
  try: urllib.request.urlopen('http://127.0.0.1:%d/'%port,timeout=1)
  except urllib.error.HTTPError: break
  except Exception: time.sleep(.2)
 else: raise RuntimeError('forward unavailable')
PY
cbc -p --output-format stream-json -y --model clover-pilot --max-turns 48 --mcp-config /workspace/pilot-mcp.json -- '看一下这份客服工单处理记录，把每天的计划处理量和实际解决量按周汇总（每周从周一算起），我想看每周计划多少、实际完成多少、完成率是多少。输出一个新的xlsx文件。结果保存为 output/result.xlsx。请使用 pilot-wps 的 write_output 工具创建并保存最终工作簿，使用 read_output 验证。该工具保存的文件随后会被复制到 output/result.xlsx。' > /run-pilot/trajectory.jsonl 2>/run-pilot/stderr.log
