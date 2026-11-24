import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { paths } from '../src/config.mjs';
import { CLOVER_ART, JSON_REMINDER, TIPS, launchMessage, nextTip, sessionReporter, setupMessage, doctorSuccess } from '../src/messages.mjs';
import { FEEDBACK_URL } from '../src/constants.mjs';

async function state(t) {
  const root = await mkdtemp(join(tmpdir(), 'clover-messages-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  return paths({ DIFFUSPACE_HOME: root, CODEX_HOME: join(root, 'codex') });
}

test('tips rotate across launches, wrap, and keep the fixed JSON reminder', async t => {
  const p = await state(t);
  for (let i = 0; i <= TIPS.length; i++) {
    const tip = await nextTip(p);
    assert.equal(tip, TIPS[i % TIPS.length]);
    const text = launchMessage({ codexVersion: 'test', tip });
    assert.equal(text.split(JSON_REMINDER).length - 1, 1);
    assert.ok(text.includes(FEEDBACK_URL));
  }
});

test('corrupt and unavailable cosmetic state never blocks startup', async t => {
  const p = await state(t);
  await writeFile(p.messages, '{invalid');
  assert.equal(await nextTip(p), TIPS[0]);
  // A directory in place of the state file fails both read and atomic replacement.
  await rm(p.messages); await mkdir(p.messages);
  assert.equal(await nextTip(p), TIPS[0]);
});

test('terminal notices suppress upfront JSON reminders and deduplicate real errors', () => {
  let text = '';
  const report = sessionReporter({ write: part => { text += part; } });
  for (let i = 0; i < 3; i++) report('Unsupported output format: json_schema.', { code: 'json_constraints_unavailable' });
  for (let i = 0; i < 3; i++) report('Connection timed out.', { code: 'network_error' });
  report('Key verification failed.', { code: 'auth_error' });
  assert.equal(text, '[Clover] Connection timed out.\n[Clover] Key verification failed.\n');
});

test('compact launch output is plain, and setup gives accurate credential guidance', () => {
  const text = launchMessage({ codexVersion: 'test', compact: true });
  assert.ok(!text.includes(CLOVER_ART)); assert.ok(!text.includes('\u001b['));
  assert.match(text, /First-release preview/); assert.ok(text.includes(JSON_REMINDER));
  assert.match(setupMessage(), /not encrypted/); assert.match(setupMessage(), /sent to DiffuSpace/);
  assert.ok(doctorSuccess('/test/profile').includes(FEEDBACK_URL));
});

test('launcher shows one reminder on stderr while stdout stays machine-readable', async t => {
  const { saveKey } = await import('../src/config.mjs');
  const { chmod } = await import('node:fs/promises');
  const { spawn } = await import('node:child_process');
  const { fileURLToPath } = await import('node:url');
  const p = await state(t); await saveKey(p, 'saved-unit-key');
  const bin = join(p.dataHome, 'bin'); await mkdir(bin);
  await writeFile(join(bin, 'package.json'), '{"type":"module"}');
  const executable = join(bin, 'codex');
  await writeFile(executable, `#!${process.execPath}
if (process.argv.includes('--version')) console.log('codex-cli 0.164.0');
else {
  const option = process.argv.find(arg => arg.startsWith('model_providers.diffuspace.base_url='));
  const url = JSON.parse(option.slice(option.indexOf('=') + 1));
  for (let i = 0; i < 2; i++) {
    const response = await fetch(url + '/responses', { method: 'POST', headers: { authorization: 'Bearer ' + process.env.DIFFUSPACE_ADAPTER_TOKEN }, body: JSON.stringify({ text: { format: { type: 'json_schema' } } }) });
    if (response.status !== 400) process.exit(2);
  }
  console.log(JSON.stringify({ ok: true, adapter: url }));
}
`);
  await chmod(executable, 0o755);
  const env = { ...process.env, CODEX_HOME: p.codexHome, DIFFUSPACE_HOME: p.dataHome, PATH: `${bin}:${process.env.PATH}` };
  delete env.DIFFUSPACE_API_KEY;
  const command = fileURLToPath(new URL('../bin/diffuspace.mjs', import.meta.url));
  const child = spawn(process.execPath, [command, 'clover', '--', 'exec', '--json', 'hello'], { env, stdio: ['ignore', 'pipe', 'pipe'] });
  let stdout = ''; let stderr = '';
  child.stdout.on('data', chunk => { stdout += chunk; }); child.stderr.on('data', chunk => { stderr += chunk; });
  const exit = await new Promise((resolve, reject) => { child.once('error', reject); child.once('exit', resolve); });
  assert.equal(exit, 0, stderr);
  const result = JSON.parse(stdout); assert.equal(result.ok, true);
  assert.equal(stderr.split(JSON_REMINDER).length - 1, 1);
  assert.ok(!stderr.includes('Unsupported output format'));
  assert.ok(!stderr.includes('saved-unit-key'));
  await assert.rejects(fetch(result.adapter + '/health'), /fetch failed/);
});
