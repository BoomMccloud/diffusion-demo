import { readFile, mkdir } from 'node:fs/promises';
import { atomicPrivateWrite } from './config.mjs';
import { CLI_VERSION, FEEDBACK_URL } from './constants.mjs';

export const CLOVER_ART = String.raw`        .-.-.
       (  |  )
   .-.-.\ | /.-.-.
  ( -----\|/----- )   Clover
   '-.-. /|\ .-.-'    by DiffuSpace
       (  |  )
        '-+-'
         /
       .'
    .-'`;
export const CLOVER_ALT_ART = String.raw`        .-.-.
       (  |  )
   .-.-.\ | /.-.-.
  ( -----\|/----- )
   '-.-. /|\ .-.-'
       (  |  )
        '-+-'
         /
       .'
    .-'`;

export function designPreview(layout = 'art') {
  if (layout === 'art') return CLOVER_ALT_ART;
  if (layout !== 'side') throw new Error(`Unknown preview layout: ${layout}`);
  const labels = {
    3: 'Clover', 4: 'by DiffuSpace',
    6: `First-release preview · CLI ${CLI_VERSION} · 128k context`,
    7: `Feedback: ${FEEDBACK_URL}`,
  };
  return CLOVER_ALT_ART.split('\n').map((line, index) => labels[index]
    ? `${line.padEnd(22)}${labels[index]}` : line).join('\n');
}

export const JSON_REMINDER = 'JSON reminder: ask for plain JSON and validate it in your code. Enforced JSON mode and JSON Schema are not available yet.';
export const TIPS = [
  'Start small: describe the change, point Clover to the files, and ask it to verify the result.',
  'Good bug reports include what you expected, what happened, and your CLI and Codex versions. Leave out keys and private code.',
  'Working on something useful? Feedback, experiments, and contributions are welcome.',
  'Connection trouble? Run diffuspace doctor in another terminal for a quick check.',
  'Review the diff and run your tests. Clover is an early release and can make mistakes.',
];

export function launchMessage({ codexVersion, tip = TIPS[0], compact = false, color = false }) {
  const art = color ? `\u001b[32m${CLOVER_ART}\u001b[0m` : CLOVER_ART;
  return [
    compact ? 'Clover by DiffuSpace' : art,
    `First-release preview · CLI ${CLI_VERSION} · 128k context · ${codexVersion}`,
    'Expect rough edges. Help us make Clover better.',
    `Feedback & collaboration: ${FEEDBACK_URL}`,
    '', JSON_REMINDER,
    'This profile uses core tools and standalone MCP servers; inherited apps/plugins are off.',
    '', `Tip: ${tip}`, '',
  ].join('\n');
}

export function setupMessage() {
  return [
    'Welcome to Clover. One API key, then you are ready to code.',
    'Your key is saved locally in an owner-only file. It is not encrypted by a keychain.',
    'Prompts and tool results are sent to DiffuSpace for inference.',
    '',
  ].join('\n');
}

// Rotation is local, deterministic, and independent of credentials. Corrupt or unwritable
// cosmetic state must never prevent a coding session from starting.
export async function nextTip(p) {
  let index = 0;
  try {
    const saved = JSON.parse(await readFile(p.messages, 'utf8'));
    if (Number.isSafeInteger(saved.nextTip) && saved.nextTip >= 0) index = saved.nextTip % TIPS.length;
  } catch { /* First launch or cosmetic state is unavailable. */ }
  try {
    await mkdir(p.dataHome, { recursive: true, mode: 0o700 });
    await atomicPrivateWrite(p.messages, `${JSON.stringify({ nextTip: (index + 1) % TIPS.length })}\n`);
  } catch { /* Tip rotation is optional. */ }
  return TIPS[index];
}

export function sessionReporter(output = process.stderr) {
  const seen = new Set();
  return (message, { code } = {}) => {
    // The complete reminder is printed before launch. The API still returns a
    // concise, actionable failure for a request whose constraints cannot be met.
    if (code === 'json_constraints_unavailable') return;
    const key = `${code || ''}:${message}`;
    if (seen.has(key)) return;
    seen.add(key);
    output.write(`[Clover] ${message}\n`);
  };
}

export function doctorIntro(version) {
  return `Clover doctor · CLI ${CLI_VERSION}\nChecking your local setup and the connection to DiffuSpace.\nCodex: ${version}\n`;
}
export function doctorSuccess(profile) {
  return [
    'Ready: your key was accepted and a streamed response completed.',
    'Context: 128k tokens, with a 95% effective-context allowance.',
    `Profile: ${profile}`,
    JSON_REMINDER,
    'Next: run diffuspace clover from the folder you want to work in.',
    `Still hitting a bug? Share your versions and a minimal reproduction: ${FEEDBACK_URL}`,
    'Never include your API key, credentials file, or private code in a report.',
    '',
  ].join('\n');
}
