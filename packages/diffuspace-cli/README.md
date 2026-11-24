# DiffuSpace CLI

Run Codex with **Clover**, DiffuSpace's model with a 128,000-token context window.

```sh
diffuspace clover
```

The first launch asks for your API key without displaying it, verifies the key,
creates a `clover` Codex profile, and launches Codex through a local adapter.
Later launches reuse the saved key. The endpoint and model ID are built in.
No runtime npm dependencies are required.

## Install

Requires Node.js 22+ and Codex CLI. This preview is tested with Codex **0.164.0**.
Other versions may require catalog or protocol changes.

```sh
# If Codex is not already installed:
npm install -g @openai/codex

# Install directly from this GitHub repository:
npm install -g git+https://github.com/BoomMccloud/clover-cli.git
diffuspace clover
```

Or clone the source and install it locally:

```sh
git clone https://github.com/BoomMccloud/clover-cli.git
cd clover-cli
npm install -g .
diffuspace clover
```

From a downloaded release tarball, use
`npm install -g ./diffuspace-cli-0.1.8.tgz`.

For agent-assisted installation, share
[INSTALL.md](https://github.com/BoomMccloud/clover-cli/blob/main/INSTALL.md).
It explains setup without asking users to paste API keys into chat.

This package has not been published to npm. After publication the install command
would be `npm install -g @diffuspace/cli`, or `npx @diffuspace/cli clover`.

## Commands

```sh
diffuspace clover                  # First-run setup, adapter, then Codex
diffuspace clover --reset-key      # Replace the saved key after verification
diffuspace doctor                  # Verify Codex, authentication and streaming
diffuspace uninstall               # Remove this package's credentials and profile
diffuspace preview                 # Preview the banner and all five launch tips
diffuspace --version               # Print the installed CLI version
```

Pass Codex arguments after `--`:

```sh
diffuspace clover -- exec --skip-git-repo-check "Say hello"
diffuspace clover -- resume
```

The launcher preserves the current working directory and Codex's normal permission
checks. It does not add automatic approval or disable sandboxing. The adapter stops
when the child Codex process exits. Use the launcher rather than running
`codex --profile clover` directly: the launcher supplies the adapter's temporary
port and local authentication token.

## Clover messages

Interactive launch shows an ASCII clover, the CLI/Codex versions, first-release
status, and a feedback link: https://huggingface.co/Diffuspace. Setup explains key
storage, and doctor provides next steps and what to include in a bug report.

One of five developer tips rotates on each launch, wrapping back to the first.
The next tip index is saved separately from credentials in `messages.json` under
the DiffuSpace configuration directory. Nothing rotates on a timer or interrupts
a running turn. A corrupt or unwritable tip file does not block launch.

The JSON limitation is a fixed reminder before each launch, independent of the
rotating tip. Unsupported JSON constraints still return HTTP 400 with code
`json_constraints_unavailable`; the adapter does not silently remove them or
promise schema validation. The repeated long terminal reminder is suppressed.
Other identical adapter errors print at most once per launched session; errors
still propagate to Codex for each failed request.

Non-interactive/`exec` launches use a compact banner on stderr, leaving Codex's
stdout intact for JSON output. Set `NO_COLOR=1` to disable banner color.
`diffuspace preview` shows every launch variant without credentials or a network
request. See `src/messages.mjs` to edit the copy or add another tip.

## Local configuration

- Key: `~/.config/diffuspace/credentials.json`, stored as plaintext with owner-only
  file permissions (`0600` on Unix), inside a private directory (`0700`). This
  preview does not use an operating-system keychain. Windows users should protect
  the directory with their account's access controls.
- Model catalog: `~/.config/diffuspace/clover.models.json`.
- Profile: `~/.codex/clover.config.toml`. An existing profile not owned by this
  package is preserved; setup reports a conflict instead.
- Your base Codex configuration, default model, sessions, and other profiles are
  preserved. The launcher does not uninstall the Codex CLI.

`CODEX_HOME`, `XDG_CONFIG_HOME`, and `DIFFUSPACE_HOME` can select other storage
locations. `DIFFUSPACE_API_KEY` supplies a key for the current invocation without
saving it, useful for automation. A key in this environment variable is verified
on each invocation and takes precedence over the saved key.

Do not commit credentials or paste keys into chat. The local adapter binds only to
`127.0.0.1`, uses a random bearer token per launch, and forwards the real key only
to `https://api.diffuspace.ai:30090/v1`. It does not log prompts or credentials.
Your prompts and tool outputs are sent to DiffuSpace for inference.

## Compatibility

The adapter translates namespaced function definitions and returned calls, keeps
call IDs for subsequent tool results, and converts Codex text-part tool outputs
into strings. Function schemas use `strict: false`. It normalizes reasoning to
`medium` to avoid the endpoint's reasoning-disabled streaming failure. Text is
streamed through; malformed or prematurely closed streams produce explicit errors.

The profile sets 128,000 context tokens, a 95% effective-context allowance,
function tools, and plain text input. Native Codex automatic compaction uses Clover
itself; no artificial compaction threshold is configured. A prior isolated native
CLI test compacted a conversation near 120k tokens and retained its test fact.
That result is one synthetic test, not a guarantee of long-session quality.

Current limitations:

- Enforced JSON mode / JSON Schema and forced tool selection return clear errors.
  Prompt-requested JSON should be parsed and validated by the consuming application.
- Image/file tool outputs, image input, and custom freeform tools are unsupported.
  Clover can edit text files through shell commands; there is no freeform patch tool.
- Inherited apps and plugins are disabled for this profile. Large connector catalogs
  caused upstream failure before any answer in the initial preview. Your base
  configuration and other profiles are unchanged. Standalone configured MCP
  servers remain enabled, subject to their normal approval settings.
- Built-in hosted web search is disabled for this profile. Function-based MCP tools
  can still be used when their inputs and outputs are text compatible.
- This is a Codex CLI integration. Desktop model-picker integration is not tested.
- Resumed sessions must use `diffuspace clover` so the local adapter is available.

## Development

```sh
cd clover-cli
npm run check
npm test
npm pack
```

Tests cover actual local HTTP exchanges with mocked upstream responses, streaming
chunk boundaries, namespaced tool round trips, private key storage, and preservation
of user configuration. No API key is needed for these tests.

Official protocol references:
[Codex configuration](https://learn.chatgpt.com/docs/config-file/config-advanced),
[model catalogs](https://learn.chatgpt.com/docs/model-catalogs),
[Responses streaming events](https://developers.openai.com/api/reference/resources/responses/streaming-events).

Compare the two alternate Clover designs: `diffuspace preview --designs`.
The startup banner uses variant 2 artwork with only Clover/by DiffuSpace beside it; release metadata stays below.

## Sync changes

In your standalone checkout:

```sh
git pull --ff-only
# Edit the source, then verify:
npm run check
npm test
git add .
git commit -m "Describe the change"
git push origin main
```

Reinstall the local checkout with `npm install -g .` to use source changes.
Pushing to GitHub does not publish the package to npm. Never commit `.env`, API
keys, local Codex settings, or session logs.
