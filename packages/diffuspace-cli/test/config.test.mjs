import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, rm, stat, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { paths, writeCodexConfig, saveKey, readSavedKey } from '../src/config.mjs';
import { launchArguments, uninstall } from '../src/launch.mjs';

async function isolated(t) {
  const root = await mkdtemp(join(tmpdir(), 'diffuspace-test-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const env = { DIFFUSPACE_HOME: join(root, 'state'), CODEX_HOME: join(root, 'codex') };
  return { env, p: paths(env) };
}

test('setup preserves base config, writes 128k profile, and is idempotent', async t => {
  const { p } = await isolated(t); await mkdir(p.codexHome, { recursive: true });
  const base = join(p.codexHome, 'config.toml'); await writeFile(base, 'model = "original"\n');
  await writeCodexConfig(p); const profile = await readFile(p.profile, 'utf8');
  assert.match(profile, /model_context_window = 128000/); assert.match(profile, /model_reasoning_effort = "medium"/);
  assert.match(profile, /enable_request_compression = false/);
  assert.match(profile, /apps = false/); assert.match(profile, /plugins = false/);
  await writeCodexConfig(p); assert.equal(await readFile(p.profile, 'utf8'), profile);
  assert.equal(await readFile(base, 'utf8'), 'model = "original"\n');
});

test('setup refuses to overwrite a user-owned clover profile', async t => {
  const { p } = await isolated(t); await mkdir(p.codexHome, { recursive: true });
  await writeFile(p.profile, '# personal settings\n');
  await assert.rejects(writeCodexConfig(p), /not managed/);
  assert.equal(await readFile(p.profile, 'utf8'), '# personal settings\n');
});

test('saved key is private, never appears in profile, and uninstall removes only managed files', async t => {
  const { p, env } = await isolated(t);
  await saveKey(p, 'secret-test'); await writeCodexConfig(p);
  assert.equal(await readSavedKey(p), 'secret-test');
  if (process.platform !== 'win32') assert.equal((await stat(p.credentials)).mode & 0o777, 0o600);
  assert.ok(!(await readFile(p.profile, 'utf8')).includes('secret-test'));
  await writeFile(join(p.dataHome, 'keep.txt'), 'keep');
  await uninstall(env);
  assert.equal(await readFile(join(p.dataHome, 'keep.txt'), 'utf8'), 'keep');
  assert.equal(await readSavedKey(p), null);
});

test('exec receives correct profile and a per-invocation adapter URL', () => {
  assert.deepEqual(launchArguments(['exec', '--json', 'hello'], 'http://127.0.0.1:123/v1'), ['exec', '--profile', 'clover', '-c', 'model_providers.diffuspace.base_url="http://127.0.0.1:123/v1"', '--json', 'hello']);
});

test('API key prompt does not echo typed or pasted characters', async () => {
  const { PassThrough } = await import('node:stream');
  const { hiddenKey } = await import('../src/config.mjs');
  const input = new PassThrough(); input.isTTY = true;
  input.setRawMode = value => { input.isRaw = value; };
  let displayed = '';
  const promise = hiddenKey(input, { write: text => { displayed += text; } });
  input.write('secret-value\r');
  assert.equal(await promise, 'secret-value');
  assert.ok(!displayed.includes('secret-value')); assert.equal(input.isRaw, false);
});
