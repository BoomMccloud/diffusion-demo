#!/usr/bin/env node
import { launch, doctor, uninstall } from '../src/launch.mjs';
import { CLI_VERSION, FEEDBACK_URL } from '../src/constants.mjs';
import { launchMessage, TIPS, designPreview } from '../src/messages.mjs';

const HELP = `Clover by DiffuSpace · first-release preview · CLI ${CLI_VERSION}

Usage:
  diffuspace clover [--reset-key] [-- <codex arguments>]
  diffuspace doctor
  diffuspace uninstall
  diffuspace preview [--designs]

Run diffuspace clover from your project folder. First launch asks only for your key.
Early release: feedback, bug reports, and contributions welcome.
${FEEDBACK_URL}
Requires Node.js 22+ and an installed Codex CLI (tested 0.164.0).
Example: diffuspace clover -- exec --skip-git-repo-check "Say hello"
`;
const [command, ...rest] = process.argv.slice(2);
try {
  if (!command || ['--help', '-h', 'help'].includes(command)) console.log(HELP);
  else if (['--version', '-v'].includes(command)) console.log(`diffuspace ${CLI_VERSION}`);
  else if (command === 'preview') {
    if (rest.includes('--designs')) {
      console.log(`Variant 1: artwork\n\n${designPreview('art')}\n\nVariant 2: side panel\n\n${designPreview('side')}\n`);
    } else {
      for (let i = 0; i < TIPS.length; i++) console.log(launchMessage({ codexVersion: 'Codex CLI', tip: TIPS[i] }));
    }
  }
  else if (command === 'clover') {
    const separator = rest.indexOf('--');
    const options = separator < 0 ? rest : rest.slice(0, separator);
    const reset = options.includes('--reset-key');
    const forwarded = separator < 0 ? options.filter(x => x !== '--reset-key') : rest.slice(separator + 1);
    process.exitCode = await launch(forwarded, { reset });
  } else if (command === 'doctor') await doctor();
  else if (command === 'uninstall') await uninstall();
  else throw new Error(`Unknown command: ${command}. Run diffuspace --help.`);
} catch (error) {
  console.error(`[Clover] ${error.message}`);
  process.exitCode = 1;
}
