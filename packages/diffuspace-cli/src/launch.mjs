import { spawn, spawnSync } from 'node:child_process';
import { rm, readFile } from 'node:fs/promises';
import { constants } from 'node:os';
import { paths, readSavedKey, saveKey, verifyKey, writeCodexConfig, hiddenKey } from './config.mjs';
import { startAdapter } from './adapter.mjs';
import { launchMessage, setupMessage, nextTip, sessionReporter, doctorIntro, doctorSuccess } from './messages.mjs';
import { MANAGED_MARKER, MODEL_ID, TESTED_CODEX_VERSION } from './constants.mjs';

export function codexVersion(env = process.env) {
  const result = spawnSync('codex', ['--version'], { encoding: 'utf8', env });
  if (result.error || result.status !== 0) throw new Error('Codex CLI is required. Install it first: npm install -g @openai/codex');
  return result.stdout.trim();
}
async function obtainKey(p, { reset = false, env = process.env } = {}) {
  const environmentKey = env.DIFFUSPACE_API_KEY?.trim();
  if (environmentKey) { await verifyKey(environmentKey); return environmentKey; }
  const saved = reset ? null : await readSavedKey(p);
  if (saved) return saved;
  process.stderr.write(setupMessage());
  const apiKey = await hiddenKey();
  process.stderr.write('Checking your key with Clover...\n');
  await verifyKey(apiKey);
  await saveKey(p, apiKey);
  process.stderr.write(`Key accepted. Saved to ${p.credentials} with owner-only permissions.\nYou will not need to enter it next time.\n`);
  return apiKey;
}
export function launchArguments(forwarded, baseURL) {
  const settings = ['--profile', 'clover', '-c', `model_providers.diffuspace.base_url=${JSON.stringify(baseURL)}`];
  // exec accepts profile flags itself; interactive mode uses the root flags.
  return forwarded[0] === 'exec' ? ['exec', ...settings, ...forwarded.slice(1)] : [...settings, ...forwarded];
}
export async function launch(forwarded, { reset = false, env = process.env } = {}) {
  const version = codexVersion(env);
  const p = paths(env);
  const apiKey = await obtainKey(p, { reset, env });
  await writeCodexConfig(p);
  const adapter = await startAdapter({ apiKey, onError: sessionReporter() });
  const childEnv = { ...env, DIFFUSPACE_ADAPTER_TOKEN: adapter.token };
  delete childEnv.DIFFUSPACE_API_KEY;
  const signals = new Map();
  let child;
  try {
    process.stderr.write(launchMessage({ codexVersion: version, tip: await nextTip(p), compact: !process.stderr.isTTY || forwarded[0] === 'exec', color: Boolean(process.stderr.isTTY && !env.NO_COLOR) }));
    child = spawn('codex', launchArguments(forwarded, adapter.baseURL), { stdio: 'inherit', env: childEnv });
    for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
      const handler = () => { if (child.exitCode === null && child.signalCode === null) child.kill(signal); };
      signals.set(signal, handler); process.on(signal, handler);
    }
    return await new Promise((resolve, reject) => {
      child.once('error', reject);
      child.once('exit', (code, signal) => resolve(code ?? 128 + (constants.signals[signal] || 1)));
    });
  } finally {
    signals.forEach((handler, signal) => process.removeListener(signal, handler));
    await adapter.close();
  }
}
export async function doctor(env = process.env) {
  const p = paths(env);
  console.log(doctorIntro(`${codexVersion(env)} (tested ${TESTED_CODEX_VERSION})`));
  const apiKey = env.DIFFUSPACE_API_KEY?.trim() || await readSavedKey(p);
  if (!apiKey) throw new Error('No API key saved. Run diffuspace clover first.');
  const adapter = await startAdapter({ apiKey, onError: sessionReporter() });
  try {
    const response = await fetch(`${adapter.baseURL}/responses`, {
      method: 'POST', headers: { authorization: `Bearer ${adapter.token}`, 'content-type': 'application/json' },
      body: JSON.stringify({ model: MODEL_ID, stream: true, input: 'Reply with exactly OK.', max_output_tokens: 128 }),
    });
    const text = await response.text();
    if (!response.ok || !text.includes('event: response.completed\n')) throw new Error('The streaming check did not complete. Check your connection, then try again. To replace your key, run diffuspace clover --reset-key.');
    console.log(doctorSuccess(p.profile));
  } finally { await adapter.close(); }
}
export async function uninstall(env = process.env) {
  const p = paths(env);
  try {
    const text = await readFile(p.profile, 'utf8');
    if (!text.startsWith(`${MANAGED_MARKER}\n`)) throw new Error('Refusing to remove a user-owned Clover profile.');
    await rm(p.profile);
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  // Remove only the three named files owned by this package, not the directory.
  for (const file of [p.credentials, p.catalog, p.messages]) await rm(file, { force: true });
  console.log('Clover settings, saved key, and tip history removed. Your other Codex profiles are untouched.\nThanks for trying the first release. Feedback and collaboration: https://huggingface.co/Diffuspace');
}
