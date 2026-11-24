// diffusion-demo: Mercury's argument-filler slot pointed at our hosted diffusion
// model. Prompts, schema handling and validation match mercury.mjs; the request
// differs only where our SGLang endpoint requires it.
import {fetchWithDeadline} from './transport.mjs';
import {validateArgumentSchema, assertArgs} from '../frozen/arms/decision-providers.mjs';
import {INSTRUCTIONS, ARGUMENT_GUIDANCE} from './mercury.mjs';

export const MODEL = process.env.DIFFUSION_MODEL ?? 'qwen36-iter22000-blk16-arverify-best';
// Priced at Mercury 2.5's list rates (per million tokens) so cost compares like
// for like; we self-host, so there is no real per-token bill.
export const PRICES = {input: .20, cached: .02, output: .75};

export function diffusionProvider({signal, record, fetchCall = fetch, requestTimeoutMs = 60000}) {
  const url = process.env.DIFFUSION_BASE_URL;
  if (!url) throw new Error('Missing DIFFUSION_BASE_URL');
  return async (state, action) => {
    validateArgumentSchema(action.inputSchema);
    // Offered tool name: the action id, minus edge underscores (the model
    // writes `__finish__` as `finish__`, which would miss the schema lookup).
    const toolName = action.id.replace(/^_+|_+$/g, '') || 'finish';
    const outboundSchema = structuredClone(action.inputSchema);
    if (action.id === '__finish__') { delete outboundSchema.properties.answer.minLength; delete outboundSchema.properties.answer.maxLength; }
    // 'none' disables thinking, the closest match to Mercury's 'instant'.
    // tool_choice is left on auto: the endpoint rejects forced tool calls
    // (no grammar constraints under its speculative decoding).
    // The one tool is offered under the selected action's name. Unforced, the
    // model names its call after the action; under any other name SGLang's
    // parser finds no matching schema and returns every value as a string
    // ("20" for an integer), which fails validation and loops the step.
    const body = {model: MODEL, reasoning_effort: 'none', max_completion_tokens: 4096,
      messages: [{role: 'system', content: INSTRUCTIONS.replaceAll('submit_arguments', toolName) + (action.id === '__finish__' ? '' : ARGUMENT_GUIDANCE)},
        {role: 'user', content: JSON.stringify({state, selected: {description: action.description, name: action.id}})}],
      tools: [{type: 'function', function: {name: toolName, description: action.description ?? 'Fill arguments', parameters: outboundSchema, strict: false}}]};
    record({provider: 'luna', model: MODEL, kind: 'request', request_body: body});
    const started = performance.now();
    const res = await fetchWithDeadline(url, {method: 'POST', signal, headers: {'content-type': 'application/json'}, body: JSON.stringify(body)},
      {fetchCall, timeoutMs: requestTimeoutMs, provider: 'Diffusion', onTimeout: () => record({provider: 'luna', model: MODEL, kind: 'transport_error', error_type: 'provider_request_timeout', timeout_ms: requestTimeoutMs, elapsed_ms: performance.now() - started})});
    const text = await res.text();
    if (!res.ok) { record({provider: 'luna', model: MODEL, kind: 'http_error', status: res.status, response_body: text}); throw new Error(`Diffusion provider HTTP ${res.status}: ${text}`); }
    let response; try { response = JSON.parse(text); } catch { throw new Error('Diffusion provider returned invalid JSON'); }
    const u = response.usage ?? {}, cached = u.prompt_tokens_details?.cached_tokens ?? 0;
    const known = [u.prompt_tokens, u.completion_tokens, cached].every(n => Number.isFinite(n) && n >= 0) && cached <= u.prompt_tokens;
    const usage = {input_tokens: known ? u.prompt_tokens - cached : 0, output_tokens: u.completion_tokens ?? 0, cached_input_tokens: cached, cache_creation_tokens: 0};
    const cost = known ? (usage.input_tokens * PRICES.input + cached * PRICES.cached + usage.output_tokens * PRICES.output) / 1e6 : null;
    record({provider: 'luna', model: MODEL, model_snapshot: response.model ?? '', snapshot_source: 'provider-response-alias', usage, cost, cost_estimated: true, cost_unknown: !known, elapsed_ms: performance.now() - started, response});
    if (!known) throw new Error('Diffusion provider missing or invalid usage; cost unknown');
    if (response.model !== MODEL) throw new Error(`Diffusion provider model mismatch: ${response.model ?? 'missing'}`);
    const choices = response.choices ?? [], calls = choices[0]?.message?.tool_calls ?? [];
    if (choices.length !== 1 || !['tool_calls', 'stop'].includes(choices[0].finish_reason) || calls.length !== 1 || calls[0].function?.name !== toolName) throw new Error('Diffusion provider must return exactly selected argument function without truncation');
    let args; try { args = JSON.parse(calls[0].function.arguments); } catch { throw new Error('invalid arguments: diffusion model returned malformed function JSON'); }
    assertArgs(action.inputSchema, args); return args;
  };
}
