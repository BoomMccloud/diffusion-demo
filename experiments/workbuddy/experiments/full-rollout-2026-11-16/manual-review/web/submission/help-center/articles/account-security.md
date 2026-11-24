# Login Security

This article covers SSO configuration, SCIM sync, audit logging, and account closure. It was migrated from the legacy CMS (`legacy-help.html`, section `data-slug="account-security"`) and enriched with FAQ rows from `faq.csv` (category tags preserved).

## Migration Context

The content below replaces pages served by the legacy CMS. Legacy slugs are redirected via `redirects.json`; see [Redirects](../redirects.json) for the full mapping.

---

## SSO Configuration

Enterprise admins can enable SSO and require members to sign in with their corporate identity.

> **FAQ — Category: Security**
> Q: How to enable SSO?
> A: Enterprise admins configure SSO under Login Security.
> Source: `faq.csv` row 3 (`question=How to enable SSO`).

Cross-reference: See [SCIM Sync](#scim-sync) for automatic member provisioning alongside SSO.

---

## SCIM Sync

Enterprises can use SCIM to automatically sync member accounts; when sync fails, check the audit_log.

> **FAQ — Category: Security**
> Q: How to troubleshoot SCIM sync failures?
> A: First check the identity provider mapping, then review sync errors in the audit_log.
> Source: `faq.csv` row 6 (`question=How to troubleshoot SCIM sync failures`).

Cross-reference: See [Audit Log](#audit-log) for exporting logs used in troubleshooting.

---

## Audit Log

Admins can export the audit_log from Login Security to troubleshoot SSO and SCIM related login issues.

---

## Close Account

Before closing an account, confirm that billing is settled and export any necessary historical records.

> **FAQ — Category: Account**
> Q: How to close an account?
> A: First confirm billing is settled and export historical records.
> Source: `faq.csv` row 4 (`question=How to close an account`).

Cross-reference: See [Invoices](./account-billing.md#invoices) for downloading invoices before closure.

---

*Article anchors: #sso-configuration, #scim-sync, #audit-log, #close-account*
