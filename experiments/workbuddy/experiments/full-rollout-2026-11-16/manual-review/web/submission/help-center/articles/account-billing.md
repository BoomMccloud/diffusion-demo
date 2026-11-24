# Account and Billing

This article covers subscription management, invoices, team seat usage, and account closure prerequisites. It was migrated from the legacy CMS (`legacy-help.html`, section `data-slug="account-billing"`) and enriched with FAQ rows from `faq.csv` (category tags preserved).

## Migration Context

The content below replaces pages served by the legacy CMS. Legacy slugs are redirected via `redirects.json`; see [Redirects](../redirects.json) for the full mapping.

---

## Reset Password

Users can reset their password via email. The reset link is valid for **15 minutes**.

> **FAQ — Category: Account**
> Q: How to reset password?
> A: Reset via the email link; the link is valid for 15 minutes.
> Source: `faq.csv` row 1 (`question=How to reset password`).

### Conflict Resolution

Legacy HTML stated a 30-minute window; the FAQ row specified 15 minutes. Per `conflict-overrides.csv` (`password_reset_link_ttl`), the FAQ value wins. This decision is also recorded in `conflict-report.json`. Support ticket SUP-219 referenced the discrepancy ("expired after half an hour").

---

## Invoices

Admins can download invoices from the Billing Center and filter by month using the invoice field.

> **FAQ — Category: Billing**
> Q: How to download invoices?
> A: Go to the Billing Center and download by month.
> Source: `faq.csv` row 2 (`question=How to download invoices`).

Cross-reference: See [Close Account](./account-security.md#close-account) for billing settlement prerequisites before closing an account.

---

## Team Seats

Once the team reaches `seat_limit`, new members require an admin to release a seat or upgrade the plan. When usage hits 90%, admins receive a warning notification. If the cap is reached, invitations are blocked until an admin releases a seat or upgrades the plan.

> **FAQ — Category: Account**
> Q: Can I still invite members once the seat limit is reached?
> A: Once the seat limit is reached invitations are blocked; admins are notified when usage hits 90%.
> Source: `faq.csv` row 5 (`question=Can I still invite members once the seat limit is reached`).

### Conflict Resolution

Legacy HTML described only "release a seat or upgrade plan"; the FAQ added "invitations blocked when cap is reached; 90% triggers warning." Per `conflict-overrides.csv` (`seat_limit_invite_behavior`), both behaviors are retained in this body copy. Support ticket SUP-244 confirmed the real-world impact of this dual-path flow.

---

*Article anchors: #reset-password, #invoices, #team-seats*
