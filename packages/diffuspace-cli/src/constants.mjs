import { readFileSync } from 'node:fs';

export const CLI_VERSION = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version;
export const FEEDBACK_URL = 'https://huggingface.co/Diffuspace';
export const UPSTREAM_URL = 'https://api.diffuspace.ai:30090/v1';
export const MODEL_ID = 'clover-10-23';
export const CONTEXT_WINDOW = 128000;
export const TESTED_CODEX_VERSION = '0.164.0';
export const MANAGED_MARKER = '# Managed by @diffuspace/cli';
export const BASE_INSTRUCTIONS = 'You are Clover, a coding assistant. Follow user instructions, inspect relevant files, make focused changes, and verify your work. Use available function tools when needed. Preserve unrelated user changes. If a tool is denied approval, stop and report the blocker; do not seek an alternate route. Use shell commands to edit files when no patch tool is available.';
export function modelCatalog() {
  return { models: [{
    slug: MODEL_ID, display_name: 'Clover', description: 'Clover by DiffuSpace. First-release coding preview, 128k context. Feedback and contributions welcome.',
    base_instructions: BASE_INSTRUCTIONS, default_reasoning_level: 'medium',
    supported_reasoning_levels: [{ effort: 'medium', description: 'Compatible default reasoning setting' }],
    shell_type: 'unified_exec', visibility: 'list', supported_in_api: true, priority: 1,
    additional_speed_tiers: [], service_tiers: [], available_access_programs: { cyber: [] },
    availability_nux: null, upgrade: null, model_messages: null,
    include_skills_usage_instructions: false, include_plugin_usage_instructions: false,
    include_apps_usage_instructions: false, default_reasoning_summary: 'none',
    support_verbosity: false, default_verbosity: null, apply_patch_tool_type: null,
    web_search_tool_type: 'text', truncation_policy: { mode: 'tokens', limit: 10000 },
    supports_image_detail_original: false, context_window: CONTEXT_WINDOW,
    max_context_window: CONTEXT_WINDOW, effective_context_window_percent: 95,
    experimental_supported_tools: [], input_modalities: ['text'], supports_search_tool: false,
    supports_experimental_context: false, use_responses_lite: false,
    supports_reasoning_effort_updates: false, tool_mode: 'direct',
    multi_agent_version: null, multi_agent_reasoning_effort: null,
  }] };
}
