# Docs Migration Product Notes

A handoff brief from the docs squad. Below is the shape and intent for whoever picks up the build.

## What this is for

We are sunsetting an aging CMS. The old page, a question spreadsheet, a term map, a slug-redirect table, and a small sheet of who-wins picks have been dropped into the kit. Sales and onboarding keep tripping over stale wording where the old page and the question rows disagree — the password-reset window says one thing in one spot and another somewhere else, and the seat-cap behavior is told two different ways. We want a tidy two-piece written surface plus the manifests around it, so the front-end can swap over cleanly.

## How writers and support actually use it

- Writers expect two real Markdown deliverables, broken out by subject. One covers the billing surface (subscription, invoices, seat usage, closing accounts); the other covers login, password reset, SSO setup, SCIM provisioning, and the audit log. A single giant page, or a flat catalog of questions, is unusable.
- Support pastes URLs into chat tickets, so every row in the link manifest needs to resolve to a true article path or in-page anchor inside the tree. Empty arrays are a smell.
- The sidebar manifest feeds the nav widget on the front-end. It has to obey the shape requirements we ship in `nav-schema.json` and may only name paths actually present on disk.
- The term widget reads the glossary at runtime. Words in the attached map (CMS, invoice, SSO, seat_limit, SCIM, audit_log) ought to either land as glossary rows or get normalized in-prose wherever they appear.
- The six rows in the attached question sheet are what support has been linking for months. Each one must keep its category tag during the move — that is how the support tool filters them.
- A small support-ticket sample is included because support will spot-check
  the migration through real ticket language, not only through source-file
  names. The generated pack should give those tickets a usable destination
  and preserve the source trail behind the answer.
- We also need slug rewrites so old inbound URLs still land. The slugs requiring a real destination are `reset-password`, `invoice-help`, `sso-setup`, `close-account`, and `scim-sync`.
- Where the old page and the question sheet disagree, the override file picks the winner. The two known disagreements are the reset-link lifetime (a fifteen-minute window from the question sheet beats the older body copy) and the seat-cap behavior (keep both the ninety-percent heads-up and the at-cap invite-block flow with the ship-out-or-upgrade affordances). A short conflict log is expected so the next writer can see what was kept and what was dropped.
- Stitching between the two pieces matters: invoice prose ought to nod at billing, SSO prose ought to nod at login, and the seat-cap section ought to be reachable from the account-management area.

## Where it has to live

- Build the surface under `/workspace/submission/help-center/`. That tree is what gets mounted for review; nothing outside it is read.
- The tree must hold at minimum:
  - `/workspace/submission/help-center/articles/account-billing.md`
  - `/workspace/submission/help-center/articles/account-security.md`
  - `/workspace/submission/help-center/nav.json`
  - `/workspace/submission/help-center/links.json`
  - `/workspace/submission/help-center/glossary.json`
  - `/workspace/submission/help-center/redirects.json`
  - `/workspace/submission/help-center/conflict-report.json`
- Pull body copy, question rows, term entries, slug rewrites, and override decisions out of the kit files at write time. Do not invent rows absent in the kit.

## Things to avoid

- Do not flatten everything into a single piece or a long question-and-answer dump. The two-piece break is load-bearing for the sidebar.
- Do not silently fold the question sheet in while shedding its category tag — the support tool filters on that tag staying visible next to each prompt.
- Do not leave the glossary as a bare word catalog with no backreference. Writers expect a pointer from each row to a true title row or jump anchor in one of the two pieces.
- Do not let the sidebar manifest, link manifest, or slug-rewrite manifest name paths absent in the tree. Anything absent surfaces as a broken destination.
- Do not fabricate policies, dates, APIs, SLA numbers, or onboarding flows absent in the kit. If the kit does not say it, leave it out.
- Do not lean on the public internet, real customer credentials, or live endpoints. Everything required is in the kit.

## Review notes

- A first sweep confirms the seven files above live under the tree and that the sidebar, link, and slug-rewrite manifests parse and resolve to true destinations inside the tree.
- A second sweep walks the two pieces for the old subject titles (billing surface, password reset, invoice handling, seat management, login security, SSO setup, SCIM sync, audit log, account closure) and confirms the six question rows have been folded in with their category tag preserved as an embedded note next to each prompt.
- A reviewer then reads the conflict log and confirms it names both the reset-window disagreement and the seat-cap disagreement, with the picked value, the dropped value, the chosen origin, and a sentence of reasoning per row.
- The body copy is checked against the override sheet: the reset window ought to read fifteen minutes, and the seat-cap narrative ought to keep both the early heads-up and the at-cap invite-block-with-shipout-or-upgrade behavior.
- Reviewers scan for fabricated copy — extra billing policies, made-up dates, uncited APIs, or invented onboarding flows absent in the kit should not appear.
- Quick self-check: open both pieces, count six category notes across three different category labels, and make sure each glossary row cites a true `articles/<file>.md#<anchor>` location. If the numbers do not line up, the surface is not done yet.
- Support spot-check: pick the sample tickets, follow their legacy slug and
  phrasing into the generated docs, and confirm the landing section gives a
  support agent the resolved answer without contradicting the source files.

## Migration Review Depth

Treat the output as something support will actually ship. Conflict choices need to appear consistently in the readable articles, the navigation/linking surface, the redirect map, and the conflict log; a value parked only in a JSON report is not useful to a customer.

The pack should let a reviewer walk from every source family in the kit to the generated surface: legacy article anchors, FAQ rows and categories, glossary terms, redirect slugs, schema-required nav nodes, and override decisions. Evidence that only restates the assignment without source ids and generated destinations does not help the migration review.

When a conflict has a losing claim, do not leave that losing claim behind in customer-facing prose as if it were still policy. FAQ rows should land once, near the section where support would use them, while keeping their category context and source trail instead of being dumped into a detached appendix.

Think of the manifests as a graph support will navigate. Nav entries, links, redirects, and glossary references should land on the right topic, not just any existing file. A reviewer should also be able to spot-audit a few important customer-facing claims back to concrete source rows or anchors.

Ticket-language coverage matters. A customer phrase such as an expired reset
link, a blocked invite at seat cap, an SSO-to-SCIM handoff, or invoice plus
closure preparation should land on the same resolved topic that the structured
source files imply. The ticket mapping can live in link manifests, redirect
notes, article prose, conflict notes, or another reviewable part of the
submitted help-center pack.
