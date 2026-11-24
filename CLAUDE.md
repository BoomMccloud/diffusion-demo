@AGENTS.md

## HackMD

- Edit HackMD notes through the API, not the browser. The browser panes aren't
  signed in to HackMD and return 403.
- The key is `HACKMD_API_KEY` in `.env.local`, which git ignores. Load it with
  `set -a; source .env.local; set +a` and never print it.
- Read a note with `GET https://api.hackmd.io/v1/notes/<id>` and update it with
  `PATCH` and a JSON body of `{"content": "..."}`. Send the bearer token in the
  `Authorization` header. A successful PATCH returns 202.
- DiffuSpace UI feedback goes in note `mVPQV64SS2yW5zBQ_O7uxA` (`ui_feedback`).
  It's a numbered list of one- or two-sentence items. Append new items to it.
