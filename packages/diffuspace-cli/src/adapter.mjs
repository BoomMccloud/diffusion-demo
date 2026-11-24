import http from 'node:http';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { once } from 'node:events';
import { UPSTREAM_URL, modelCatalog } from './constants.mjs';
import { CompatibilityError, parseSSE, restoreResponse, translateRequest } from './protocol.mjs';

function authorize(actual, expected) {
  const a = Buffer.from(actual || '');
  const b = Buffer.from(`Bearer ${expected}`);
  return a.length === b.length && timingSafeEqual(a, b);
}
export async function readJSON(request) {
  let size = 0; const chunks = [];
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 16 * 1024 * 1024) throw new CompatibilityError('Request exceeds 16 MiB.');
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new CompatibilityError('Invalid JSON request.'); }
}
function sendJSON(res, status, body) {
  res.writeHead(status, { 'content-type': 'application/json', 'cache-control': 'no-store' });
  res.end(JSON.stringify(body));
}
export async function startAdapter({ apiKey, upstreamURL = UPSTREAM_URL, fetchImpl = fetch, onError = () => {} }) {
  if (!apiKey) throw new Error('DiffuSpace API key is missing.');
  const token = randomBytes(32).toString('hex');
  const controllers = new Set();
  const server = http.createServer(async (req, res) => {
    const controller = new AbortController(); controllers.add(controller);
    res.on('close', () => { if (!res.writableEnded) controller.abort(); });
    let timer;
    const redact = value => String(value).split(apiKey).join('[REDACTED]');
    const fail = (status, message, code = 'diffuspace_adapter_error') => {
      const error = { type: 'diffuspace_adapter_error', code, message: redact(message) };
      onError(error.message, { code });
      if (res.destroyed || res.writableEnded) return;
      if (!res.headersSent) sendJSON(res, status, { error });
      else res.end(`event: error\ndata: ${JSON.stringify({ type: 'error', code: error.code, message: error.message })}\n\n`);
    };
    try {
      if (!authorize(req.headers.authorization, token)) return sendJSON(res, 401, { error: { message: 'Invalid local adapter token.' } });
      const path = new URL(req.url, 'http://127.0.0.1').pathname;
      if (req.method === 'GET' && path === '/health') return sendJSON(res, 200, { status: 'ok' });
      if (req.method === 'GET' && path === '/v1/models') return sendJSON(res, 200, modelCatalog());
      if (req.method !== 'POST' || path !== '/v1/responses') return sendJSON(res, 404, { error: { message: 'Route not supported. Codex uses local model-based compaction.' } });
      if (req.headers['content-encoding'] && req.headers['content-encoding'] !== 'identity') throw new CompatibilityError('Compressed requests are unsupported. Disable enable_request_compression for Clover.');
      const { body, aliases } = translateRequest(await readJSON(req));
      timer = setTimeout(() => controller.abort(new Error('Upstream request timed out after 180 seconds.')), 180000);
      const upstream = await fetchImpl(`${upstreamURL}/responses`, {
        method: 'POST', headers: { authorization: `Bearer ${apiKey}`, 'content-type': 'application/json', accept: body.stream ? 'text/event-stream' : 'application/json' },
        body: JSON.stringify(body), signal: controller.signal,
      });
      if (!upstream.ok) {
        const text = (await upstream.text()).slice(0, 4000);
        return fail(upstream.status, `DiffuSpace HTTP ${upstream.status}: ${text}`);
      }
      if (!body.stream) return sendJSON(res, 200, restoreResponse(await upstream.json(), aliases));
      if (!upstream.headers.get('content-type')?.includes('text/event-stream')) throw new Error('DiffuSpace returned a non-SSE response for a streaming request.');
      let terminal = false;
      for await (const frame of parseSSE(upstream.body)) {
        if (frame.data === '[DONE]') continue;
        let data;
        try { data = JSON.parse(frame.data); } catch { throw new Error('DiffuSpace returned invalid SSE JSON.'); }
        if (data.error || data.type === 'error') throw new Error(`DiffuSpace stream error: ${JSON.stringify(data.error || data)}`);
        if (!data.type) throw new Error('DiffuSpace SSE event has no type.');
        if (data.type === 'response.failed') {
          const failure = data.response?.error;
          throw new Error(`DiffuSpace response failed${failure?.code ? ` (${failure.code})` : ''}: ${failure?.message || 'No error details provided by the endpoint.'}`);
        }
        data = restoreResponse(data, aliases);
        if (!res.headersSent) res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-store', 'x-accel-buffering': 'no' });
        if (!res.write(`event: ${data.type}\ndata: ${JSON.stringify(data)}\n\n`)) await once(res, 'drain', { signal: controller.signal });
        if (['response.completed', 'response.failed', 'response.incomplete'].includes(data.type)) { terminal = true; break; }
      }
      if (!terminal) throw new Error('DiffuSpace stream ended before a terminal response event.');
      res.end();
    } catch (error) { fail(error instanceof CompatibilityError ? 400 : 502, error.message, error.code); }
    finally { clearTimeout(timer); controllers.delete(controller); }
  });
  server.requestTimeout = 190000;
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  return {
    baseURL: `http://127.0.0.1:${server.address().port}/v1`, token,
    async close() {
      controllers.forEach(c => c.abort());
      await new Promise(resolve => { server.close(resolve); server.closeAllConnections(); });
    },
  };
}
