// diffusion-demo: route the frozen scaffold's Typesafe Jev call through
// OpenRouter's System One endpoint, pinned to the Jev 1.13 snapshot used on
// the September 18 board. Only the transport changes; request and response
// bodies keep the Typesafe shape.
export const JEV_MODEL = process.env.JEV_MODEL ?? 'typesafe/jev-1.13';
const TYPESAFE_URL = 'https://api.typesafe.ai/v1/systemone';
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/systemone';

export function openRouterJevFetch(fetchCall = globalThis.fetch) {
  return async (url, options) => {
    if (url !== TYPESAFE_URL) return fetchCall(url, options);
    if (!process.env.OPENROUTER_API_KEY) throw new Error('Missing OPENROUTER_API_KEY');
    const body = JSON.parse(options.body);
    body.model = JEV_MODEL;
    const response = await fetchCall(OPENROUTER_URL, {...options,
      headers: {...options.headers, authorization: `Bearer ${process.env.OPENROUTER_API_KEY}`},
      body: JSON.stringify(body)});
    const text = await response.text();
    if (!response.ok) return new Response(text, {status: response.status, statusText: response.statusText, headers: response.headers});
    // The scaffold requires a bare `jev-` snapshot name; OpenRouter prefixes
    // the vendor ("typesafe/jev-1.13-20260917").
    const result = JSON.parse(text);
    if (typeof result.model === 'string') result.model = result.model.replace(/^typesafe\//, '');
    return new Response(JSON.stringify(result), {status: response.status, statusText: response.statusText, headers: response.headers});
  };
}
