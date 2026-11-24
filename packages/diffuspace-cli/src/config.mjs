import { mkdir, readFile, writeFile, rename, chmod, lstat } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { randomBytes } from 'node:crypto';
import { MANAGED_MARKER, MODEL_ID, CONTEXT_WINDOW, modelCatalog, UPSTREAM_URL } from './constants.mjs';

export function paths(env = process.env) {
  const dataHome = env.DIFFUSPACE_HOME || join(env.XDG_CONFIG_HOME || join(homedir(), '.config'), 'diffuspace');
  const codexHome = env.CODEX_HOME || join(homedir(), '.codex');
  return { dataHome, codexHome, credentials: join(dataHome, 'credentials.json'), catalog: join(dataHome, 'clover.models.json'), profile: join(codexHome, 'clover.config.toml'), messages: join(dataHome, 'messages.json') };
}
export async function atomicPrivateWrite(path, content) {
  try { if ((await lstat(path)).isSymbolicLink()) throw new Error(`Refusing to replace a symlink: ${path}`); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const temp = `${path}.${randomBytes(8).toString('hex')}.tmp`;
  await writeFile(temp, content, { mode: 0o600, flag: 'wx' });
  await rename(temp, path);
}
export async function readSavedKey(p) {
  try {
    const data = JSON.parse(await readFile(p.credentials, 'utf8'));
    if (typeof data.apiKey !== 'string' || !data.apiKey.trim()) throw new Error('Saved API key is invalid. Use diffuspace clover --reset-key.');
    return data.apiKey;
  } catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}
export async function saveKey(p, apiKey) {
  await mkdir(p.dataHome, { recursive: true, mode: 0o700 });
  await chmod(p.dataHome, 0o700);
  await atomicPrivateWrite(p.credentials, `${JSON.stringify({ version: 1, apiKey })}\n`);
}
export async function verifyKey(apiKey, { upstreamURL = UPSTREAM_URL, fetchImpl = fetch } = {}) {
  const response = await fetchImpl(`${upstreamURL}/responses`, {
    method: 'POST', headers: { authorization: `Bearer ${apiKey}`, 'content-type': 'application/json' },
    body: JSON.stringify({ model: MODEL_ID, input: 'Reply with exactly OK.', reasoning: { effort: 'medium' }, stream: false, max_output_tokens: 128 }),
    signal: AbortSignal.timeout(45000),
  });
  if (!response.ok) throw new Error(`DiffuSpace key verification failed (HTTP ${response.status}).`);
  const data = await response.json();
  if (data.error || !Array.isArray(data.output) || data.status !== 'completed') throw new Error('DiffuSpace did not return a completed response during key verification.');
}
export function profileText(p) {
  return `${MANAGED_MARKER}
model = ${JSON.stringify(MODEL_ID)}
model_provider = "diffuspace"
model_context_window = ${CONTEXT_WINDOW}
model_reasoning_effort = "medium"
model_catalog_json = ${JSON.stringify(p.catalog)}
web_search = "disabled"
service_tier = "default"

[features]
# Keep inherited connector schemas from exhausting Clover context on startup.
apps = false
plugins = false
enable_request_compression = false

[model_providers.diffuspace]
name = "DiffuSpace Clover"
# The launcher supplies the live adapter port for this invocation.
base_url = "http://127.0.0.1:0/v1"
env_key = "DIFFUSPACE_ADAPTER_TOKEN"
wire_api = "responses"
supports_websockets = false
`;
}
export async function writeCodexConfig(p) {
  // Never silently replace an existing user-owned profile.
  try {
    const current = await readFile(p.profile, 'utf8');
    if (!current.startsWith(`${MANAGED_MARKER}\n`)) throw new Error(`${p.profile} already exists and is not managed by DiffuSpace. Rename it before setup.`);
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  await mkdir(p.dataHome, { recursive: true, mode: 0o700 });
  await mkdir(p.codexHome, { recursive: true, mode: 0o700 });
  await atomicPrivateWrite(p.catalog, `${JSON.stringify(modelCatalog(), null, 2)}\n`);
  await atomicPrivateWrite(p.profile, profileText(p));
}
export async function hiddenKey(input = process.stdin, output = process.stderr) {
  if (!input.isTTY || !input.setRawMode) throw new Error('Run in an interactive terminal to enter your API key, or set DIFFUSPACE_API_KEY.');
  output.write('Clover API key (hidden): ');
  const wasRaw = input.isRaw;
  input.setRawMode(true); input.resume();
  return new Promise((resolve, reject) => {
    let value = '';
    function done(error) {
      input.removeListener('data', onData); input.setRawMode(Boolean(wasRaw)); input.pause(); output.write('\n');
      if (error) reject(error); else if (value.trim()) resolve(value.trim()); else reject(new Error('API key cannot be empty.'));
    }
    function onData(chunk) {
      for (const char of chunk.toString('utf8')) {
        if (char === '\u0003' || char === '\u0004') return done(new Error('Key entry cancelled.'));
        if (char === '\r' || char === '\n') return done();
        if (char === '\u007f' || char === '\b') value = value.slice(0, -1);
        else if (char >= ' ' && char !== '\u001b') value += char;
      }
    }
    input.on('data', onData);
  });
}
