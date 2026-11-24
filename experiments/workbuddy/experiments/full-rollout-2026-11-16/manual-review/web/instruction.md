# Web-Bench Task T50

The attachments are help docs and an FAQ table exported from the old CMS. Please reorganize them into a new help-center docs pack — Markdown content, navigation structure, and link list.


## Migration Review Evidence

Make the help-center pack reviewable from the submitted files. A writer or support reviewer should be able to trace FAQ merges, glossary replacements, navigation nodes, redirects, conflict choices, orphan-link cleanup, and source-priority decisions back to concrete rows or anchors in the bundled assets. That evidence can live in article notes, manifest fields, the conflict report, a migration notes file, or another clear part of the pack; do not rely on prose-only claims that cannot be followed to a generated destination.

## Output

Create the required artifact inside `/workspace`. The required output path is:

- `/workspace/submission/help-center` (declared as `environment/submission/help-center/`)

The help-center pack must include these files at minimum:

- `/workspace/submission/help-center/articles/account-billing.md`
- `/workspace/submission/help-center/articles/account-security.md`
- `/workspace/submission/help-center/nav.json`
- `/workspace/submission/help-center/links.json`
- `/workspace/submission/help-center/glossary.json`
- `/workspace/submission/help-center/redirects.json`
- `/workspace/submission/help-center/conflict-report.json`

Do not collapse everything into one article. Split account/billing content and security/SSO/password content into the two required Markdown articles, then make `nav.json` and `links.json` point to actual files or anchors.

Do not place the final answer only in chat; write the runnable artifact files.

## Public Assets

- `legacy_html`: `/workspace/public-assets/source_docs/legacy-help.html` text/html
- `faq_csv`: `/workspace/public-assets/source_docs/faq.csv` text/csv
- `nav_schema`: `/workspace/public-assets/spec/nav-schema.json` application/json
- `term_map`: `/workspace/public-assets/source_docs/terms.json` application/json
- `redirects_csv`: `/workspace/public-assets/source_docs/redirects.csv` text/csv
- `conflict_overrides`: `/workspace/public-assets/source_docs/conflict-overrides.csv` text/csv
- `support_ticket_samples`: `/workspace/public-assets/source_docs/support-ticket-samples.csv` text/csv
- `docs_migration_notes`: `/workspace/public-assets/spec/docs-migration-product-notes.md` text/markdown
