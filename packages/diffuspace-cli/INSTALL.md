# Install Clover for Codex

Follow these instructions when a user asks you to install this local preview.
The supported user-facing command is `diffuspace clover`.

1. Check `node --version` (22 or newer) and `codex --version`. This package was
   tested with Codex 0.164.0. If Codex is missing, install it with
   `npm install -g @openai/codex` using the environment's normal permissions.
2. Install directly from GitHub:

   ```sh
   npm install -g git+https://github.com/BoomMccloud/clover-cli.git
   ```

   Or, from a cloned `clover-cli` repository root, run `npm install -g .`.

   For a downloaded release tarball instead, run:

   ```sh
   npm install -g ./diffuspace-cli-0.1.8.tgz
   ```

3. Ask the user to run `diffuspace clover` in their own terminal. It prompts for
   the API key with hidden input. Never ask them to paste the key into chat.
   The endpoint and model are already fixed; do not ask for those values.
4. The launcher creates the `clover` profile and local model catalog, starts an
   authenticated loopback adapter, and opens Codex in the current directory.
   A saved key is reused on later launches. Normal Codex permissions still apply.
5. Run `diffuspace doctor` to verify authentication and streaming if needed.

Do not replace the user's default model, change approval policies, or overwrite
an existing user-owned `clover` profile. The launcher handles these checks.

The saved key is plaintext protected by owner-only filesystem permissions on
Unix. See README.md for storage paths, environment-variable alternatives, current
limitations, and the upstream service that receives prompts and tool outputs.

To replace a key: `diffuspace clover --reset-key`.
To remove generated settings and credentials: `diffuspace uninstall`.
To remove the npm CLI too: `npm uninstall -g @diffuspace/cli`.

The package is not yet published on npm. Do not tell users that
`npx @diffuspace/cli clover` works until a release has actually been published.

Preview the release messaging without a key or network access: `diffuspace preview`.
Feedback and collaboration: https://huggingface.co/Diffuspace.

Compare the two alternate Clover designs: `diffuspace preview --designs`.
The startup banner uses variant 2 artwork with only Clover/by DiffuSpace beside it; release metadata stays below.
