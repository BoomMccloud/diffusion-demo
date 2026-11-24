import { createHash } from 'node:crypto';
import { MODEL_ID } from './constants.mjs';

export class CompatibilityError extends Error {
  constructor(message, code = 'compatibility_error') { super(message); this.code = code; }
}

// Aliases are deterministic so resumed sessions do not depend on an in-memory table.
export function toolAlias(namespace, name) {
  return namespace ? `ds_${createHash('sha256').update(JSON.stringify([namespace, name])).digest('hex').slice(0, 32)}` : name;
}

export function translateRequest(source) {
  const body = structuredClone(source);
  const aliases = new Map();
  const used = new Set();
  const tools = [];
  function visit(tool, parent = '') {
    if (tool.type === 'namespace') {
      const namespace = parent ? `${parent}.${tool.name}` : tool.name;
      if (!tool.name || !Array.isArray(tool.tools)) throw new CompatibilityError('Malformed namespace tool.');
      tool.tools.forEach(child => visit(child, namespace));
      return;
    }
    if (tool.type !== 'function') throw new CompatibilityError(`Clover supports function tools; unsupported tool type: ${tool.type}.`);
    if (!tool.name) throw new CompatibilityError('Function tool is missing a name.');
    const name = toolAlias(parent, tool.name);
    if (used.has(name)) throw new CompatibilityError(`Duplicate tool name: ${name}.`);
    used.add(name);
    const converted = { ...tool, name, strict: false };
    delete converted.namespace;
    if (parent) {
      converted.description = `[${parent}.${tool.name}] ${tool.description || ''}`;
      aliases.set(name, { namespace: parent, name: tool.name });
    }
    tools.push(converted);
  }
  (body.tools || []).forEach(t => visit(t));
  if (body.tools) body.tools = tools;
  const format = body.text?.format;
  if (format && format.type !== 'text') throw new CompatibilityError(`Unsupported output format: ${format.type}. Use plain text output.`, 'json_constraints_unavailable');
  if (body.tool_choice && !['auto', 'none'].includes(body.tool_choice)) throw new CompatibilityError('Clover supports tool_choice auto or none; forced tool selection is unavailable.');
  body.model = MODEL_ID;
  body.reasoning = { effort: 'medium' };
  if (body.text) delete body.text.verbosity;
  delete body.service_tier;
  // Historical output items carry namespace separately in the Responses protocol.
  if (Array.isArray(body.input)) {
    for (const item of body.input) {
      if (item.type === 'function_call' && item.namespace) {
        item.name = toolAlias(item.namespace, item.name);
        delete item.namespace;
      }
      if (item.type === 'function_call_output' && Array.isArray(item.output)) {
        if (item.output.some(part => !['input_text', 'text'].includes(part.type))) {
          throw new CompatibilityError('Clover supports text tool results only; image or file tool results are unavailable.');
        }
        item.output = item.output.map(part => part.text).join('\n');
      }
      if (item.type === 'custom_tool_call' || item.type === 'custom_tool_call_output') {
        throw new CompatibilityError('Custom freeform tools are unavailable; use function tools or shell file editing.');
      }
    }
  }
  return { body, aliases };
}

export function restoreResponse(value, aliases) {
  if (!value || typeof value !== 'object') return value;
  if (Array.isArray(value)) return value.map(v => restoreResponse(v, aliases));
  const output = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, restoreResponse(v, aliases)]));
  if (output.type === 'function_call' && aliases.has(output.name)) Object.assign(output, aliases.get(output.name));
  return output;
}

// Parse SSE across arbitrary UTF-8 and HTTP chunk boundaries, without buffering a response.
export async function* parseSSE(stream) {
  const decoder = new TextDecoder();
  let buffer = '';
  function parse(frame) {
    const fields = { event: '', data: [] };
    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith(':')) continue;
      const index = line.indexOf(':');
      if (index < 0) continue;
      const key = line.slice(0, index);
      const value = line.slice(index + 1).replace(/^ /, '');
      if (key === 'data') fields.data.push(value);
      if (key === 'event') fields.event = value;
    }
    return fields.data.length ? { event: fields.event, data: fields.data.join('\n') } : null;
  }
  for await (const chunk of stream) {
    buffer += decoder.decode(chunk, { stream: true });
    let match;
    while ((match = /\r?\n\r?\n/.exec(buffer))) {
      const frame = buffer.slice(0, match.index);
      buffer = buffer.slice(match.index + match[0].length);
      const parsed = parse(frame);
      if (parsed) yield parsed;
    }
    if (buffer.length > 16 * 1024 * 1024) throw new Error('Upstream SSE frame exceeds 16 MiB.');
  }
  buffer += decoder.decode();
  if (buffer.trim()) {
    const parsed = parse(buffer);
    if (parsed) yield parsed;
  }
}
