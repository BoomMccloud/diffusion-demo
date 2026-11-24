// diffusion-demo: arm.mjs with Mercury replaced by our diffusion model and Jev
// reached through OpenRouter. Readiness, the decision agent and its settings
// are unchanged from the measured Jev + Mercury method.
import {runDecisionAgent} from '../frozen/arms/decision-agent.mjs';
import {createDecisionProviders} from '../frozen/arms/decision-providers.mjs';
import {createReadinessAdapter, VERSION} from './readiness.mjs';
import {diffusionProvider, MODEL} from './diffusion.mjs';
import {openRouterJevFetch, JEV_MODEL} from './openrouter-jev.mjs';
import {fetchWithDeadline} from './transport.mjs';
export const TOOL_VERSION = VERSION;
export async function runWebMCPDiffusion(args, {fetchCall = globalThis.fetch} = {}) {
  const readinessAudit = [];
  let decisionSignal;
  const readiness = {max_wait_ms:1000, poll_interval_ms:25, condition:'empty-only', attempt_budget:'actual-agent-AbortSignal', timeout:'preserve-empty-list', audit:'one-event-per-observation;outside-model-state'};
  const adapter = createReadinessAdapter(args, {getSignal:()=>decisionSignal, audit:e=>readinessAudit.push(e), timeoutMs:1000, pollMs:25});
  const jevFetch = openRouterJevFetch(fetchCall);
  const result = await runDecisionAgent({...args, model:undefined, jevTransport:'typesafe'}, {
    adapter,
    providerFactory:opts=>{
      decisionSignal = opts.signal;
      const providers = createDecisionProviders({...opts, fetchCall:(url,options)=>fetchWithDeadline(url,options,{fetchCall:jevFetch,timeoutMs:60000,provider:'Jev'})});
      providers.fillLuna = diffusionProvider({...opts,fetchCall,requestTimeoutMs:60000});
      return providers;
    },
  });
  result.transcript.push(...readinessAudit);
  for (const event of result.transcript) {
    if (event.provider === 'luna') event.provider = 'diffusion';
    if (event.requests) { event.requests.diffusion = event.requests.luna; delete event.requests.luna; }
  }
  if (result.provider_usage.luna) { result.provider_usage.diffusion = result.provider_usage.luna; delete result.provider_usage.luna; }
  Object.assign(result.decision_config, {
    version:VERSION, tool_readiness:readiness,
    tool_readiness_audit:{observations:readinessAudit.length,wait_count:readinessAudit.filter(e=>e.waited).length,total_wait_ms:readinessAudit.reduce((n,e)=>n+(e.wait_ms??0),0),outcomes:readinessAudit.map(e=>e.outcome)},
    argument_policy:'omit-unsupported-optional-fields;entity-specific-identifiers;non-finish-only',
    filler:MODEL, answer:'diffusion-written', optional_arguments:'diffusion-filled', answer_assembly:'diffusion-written',
    experiment:'diffusion-arguments-v1-readiness-v1',
    jev_model:JEV_MODEL, jev_route:'openrouter-systemone',
    filler_reasoning_effort:'none', filler_tool_choice:'auto', filler_max_completion_tokens:4096, filler_request_timeout_ms:60000, jev_request_timeout_ms:60000,
    filler_prices_per_million:'mercury-2.5 list (0.20 in, 0.02 cached, 0.75 out)',
    reproduction:'diffusion-demo variant of the portable launcher',
  });
  return result;
}
