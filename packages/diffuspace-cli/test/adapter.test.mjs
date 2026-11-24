import test from 'node:test';
import assert from 'node:assert/strict';
import { startAdapter } from '../src/adapter.mjs';
import { translateRequest, restoreResponse, toolAlias, parseSSE } from '../src/protocol.mjs';

const namespace = { type: 'namespace', name: 'tools', tools: [{ type: 'function', name: 'echo', strict: true, parameters: { type: 'object' } }] };
const event = value => `event: ${value.type}\ndata: ${JSON.stringify(value)}\n\n`;

test('namespaced tool round-trip keeps identity and call IDs across a follow-up', async t => {
  const alias = toolAlias('tools', 'echo'); let round = 0;
  const adapter = await startAdapter({ apiKey: 'unit-secret', fetchImpl: async (_url, options) => {
    const request = JSON.parse(options.body);
    assert.equal(options.headers.authorization, 'Bearer unit-secret');
    assert.equal(request.tools[0].name, alias); assert.equal(request.tools[0].strict, false);
    assert.equal(request.reasoning.effort, 'medium'); assert.equal(request.model, 'clover-10-23');
    if (++round === 2) {
      assert.equal(request.input[0].name, alias); assert.equal(request.input[0].namespace, undefined);
      assert.equal(request.input[1].call_id, 'call_1'); assert.equal(request.input[1].output, 'ok');
    }
    const item = { type: 'function_call', id: 'item_1', name: alias, call_id: 'call_1', arguments: '{"text":"ok"}' };
    return new Response(event({ type: 'response.output_item.added', item }) + event({ type: 'response.output_item.done', item }) + event({ type: 'response.completed', response: { status: 'completed', output: [item] } }), { headers: { 'content-type': 'text/event-stream' } });
  } });
  t.after(() => adapter.close());
  async function send(input = []) {
    const response = await fetch(`${adapter.baseURL}/responses`, { method: 'POST', headers: { authorization: `Bearer ${adapter.token}`, 'content-type': 'application/json' }, body: JSON.stringify({ stream: true, tools: [namespace], input }) });
    assert.equal(response.status, 200);
    const events = [];
    for await (const frame of parseSSE(response.body)) events.push(JSON.parse(frame.data));
    return events;
  }
  const events = await send();
  const restored = events[1].item;
  assert.equal(restored.name, 'echo'); assert.equal(restored.namespace, 'tools'); assert.equal(restored.call_id, 'call_1');
  assert.equal(events[2].response.output[0].namespace, 'tools');
  await send([restored, { type: 'function_call_output', call_id: 'call_1', output: [{ type: 'input_text', text: 'ok' }] }]);
});

test('aliases cannot collide with a top-level tool, and unsupported constraints are explicit', () => {
  const alias = toolAlias('tools', 'echo');
  assert.throws(() => translateRequest({ tools: [namespace, { type: 'function', name: alias }] }), /Duplicate/);
  assert.throws(() => translateRequest({ text: { format: { type: 'json_schema' } } }), /Unsupported output format/);
  assert.throws(() => translateRequest({ tool_choice: { type: 'function', name: 'echo' } }), /forced tool selection/);
  assert.throws(() => translateRequest({ tools: [{ type: 'custom', name: 'patch' }] }), /unsupported tool/);
});

test('SSE parser handles split CRLF, multi-byte UTF-8 and multiline data', async () => {
  const bytes = Buffer.from('event: demo\r\ndata: {"text":\r\ndata: "你好"}\r\n\r\n');
  async function* pieces() { for (const byte of bytes) yield Buffer.from([byte]); }
  const frames = [];
  for await (const frame of parseSSE(pieces())) frames.push(frame);
  assert.equal(frames.length, 1); assert.equal(JSON.parse(frames[0].data).text, '你好');
});

test('local adapter requires its per-session bearer token', async t => {
  let contacted = false;
  const adapter = await startAdapter({ apiKey: 'unit-secret', fetchImpl: async () => { contacted = true; } });
  t.after(() => adapter.close());
  const response = await fetch(`${adapter.baseURL}/models`);
  assert.equal(response.status, 401); assert.equal(contacted, false);
});

test('missing terminal event emits a visible error, not a successful empty stream', async t => {
  const adapter = await startAdapter({ apiKey: 'unit-secret', fetchImpl: async () => new Response(event({ type: 'response.created', response: {} }), { headers: { 'content-type': 'text/event-stream' } }) });
  t.after(() => adapter.close());
  const response = await fetch(`${adapter.baseURL}/responses`, { method: 'POST', headers: { authorization: `Bearer ${adapter.token}` }, body: JSON.stringify({ stream: true }) });
  const body = await response.text();
  assert.match(body, /event: error/); assert.match(body, /before a terminal/);
});

test('upstream errors redact credentials and preserve status', async t => {
  const adapter = await startAdapter({ apiKey: 'unit-secret', fetchImpl: async () => new Response('bad unit-secret', { status: 401 }) });
  t.after(() => adapter.close());
  const response = await fetch(`${adapter.baseURL}/responses`, { method: 'POST', headers: { authorization: `Bearer ${adapter.token}` }, body: '{}' });
  assert.equal(response.status, 401); const text = await response.text();
  assert.ok(!text.includes('unit-secret')); assert.match(text, /REDACTED/);
});

test('non-streaming tool call response is restored too', () => {
  const translated = translateRequest({ tools: [namespace] });
  const out = restoreResponse({ output: [{ type: 'function_call', name: translated.body.tools[0].name, call_id: 'abc' }] }, translated.aliases);
  assert.equal(out.output[0].namespace, 'tools'); assert.equal(out.output[0].name, 'echo');
});


test('response.failed exposes the upstream cause and redacts the API key', async t => {
  const adapter = await startAdapter({ apiKey: 'unit-secret', fetchImpl: async () => new Response(event({ type: 'response.created', response: {} }) + event({ type: 'response.failed', response: { error: { code: 'invalid_tool', message: 'bad unit-secret tool definition' } } }), { headers: { 'content-type': 'text/event-stream' } }) });
  t.after(() => adapter.close());
  const response = await fetch(`${adapter.baseURL}/responses`, { method: 'POST', headers: { authorization: `Bearer ${adapter.token}` }, body: JSON.stringify({ stream: true }) });
  const text = await response.text();
  assert.match(text, /event: error/); assert.match(text, /invalid_tool/); assert.match(text, /bad \[REDACTED\] tool definition/);
  assert.ok(!text.includes('unit-secret')); assert.ok(!text.includes('event: response.failed'));
});

test('JSON constraints remain explicit API failures without repeated terminal reminders', async t => {
  const { sessionReporter } = await import('../src/messages.mjs');
  let printed = ''; let contacted = false;
  const adapter = await startAdapter({ apiKey: 'unit-secret', onError: sessionReporter({ write: value => { printed += value; } }), fetchImpl: async () => { contacted = true; } });
  t.after(() => adapter.close());
  for (let i = 0; i < 2; i++) {
    const response = await fetch(`${adapter.baseURL}/responses`, { method: 'POST', headers: { authorization: `Bearer ${adapter.token}` }, body: JSON.stringify({ text: { format: { type: 'json_schema' } } }) });
    assert.equal(response.status, 400);
    const data = await response.json(); assert.equal(data.error.code, 'json_constraints_unavailable');
    assert.match(data.error.message, /Unsupported output format/);
  }
  assert.equal(contacted, false); assert.equal(printed, '');
});
