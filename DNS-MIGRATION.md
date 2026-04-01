# DNS Migration Reference: liberty-collective.com

Captured: 2026-04-01

## Current Setup
- **Registrar:** GoDaddy
- **Nameservers:** ns53.domaincontrol.com, ns54.domaincontrol.com
- **Current A Record:** 3.16.235.182 (SpotHopper)
- **Email Provider:** Microsoft 365 via Proofpoint (PPE-hosted)

## Records to Recreate in Cloudflare DNS

### MX Records (Email - CRITICAL)
| Priority | Value |
|----------|-------|
| 0 | mx1-usg1.ppe-hosted.com |
| 0 | mx2-usg1.ppe-hosted.com |
| 0 | mx3-usg1.ppe-hosted.com |

### TXT Records
| Value | Purpose |
|-------|---------|
| `v=spf1 include:_spf-usg1.ppe-hosted.com include:secureserver.net ~all` | SPF (email authentication) |
| `NETORGFT13790800.onmicrosoft.com` | Microsoft 365 domain verification |
| `apple-domain-verification=q31IY4uyGBpl6nOs` | Apple verification |

### CNAME Records
| Name | Value |
|------|-------|
| www | liberty-collective.com |

### No DMARC or DKIM records found
Consider adding DMARC after migration for better email security.

## Why Email Is Safe

Their email is hosted on **Microsoft 365**. That does not change. We are only changing where DNS points (from GoDaddy to Cloudflare), not where email lives. Microsoft 365 stays exactly where it is.

As long as the MX and TXT records are recreated in Cloudflare **BEFORE** switching nameservers, email never stops working. Both GoDaddy and Cloudflare will point to the same Microsoft 365 email servers during the transition.

**Do NOT touch Cloudflare's "Email Service" (Email Routing / Email Sending).** That is Cloudflare's own email product and is not relevant here. Liberty Collective's email runs entirely through Microsoft 365 via Proofpoint.

## Migration Steps (Zero-Downtime Procedure)

### Phase 1: Set Up Cloudflare (DO NOT switch nameservers yet)
1. Add liberty-collective.com domain to Cloudflare
2. Cloudflare will assign new nameservers (write them down, but don't use them yet)
3. Recreate ALL MX records above in Cloudflare DNS
4. Recreate ALL TXT records above in Cloudflare DNS (SPF, Microsoft 365 verification, Apple verification)
5. Recreate the www CNAME record
6. Add CNAME record pointing domain to Cloudflare Pages project (liberty-collective-7iw.pages.dev)

### Phase 2: Verify Before Switching
7. Double-check every DNS record in Cloudflare matches what GoDaddy currently has
8. Confirm MX records are identical — this is what keeps email working
9. Only proceed when everything matches

### Phase 3: Switch Nameservers
10. Go to GoDaddy and change nameservers from domaincontrol.com to the Cloudflare nameservers
11. **DO NOT delete anything on GoDaddy yet** — leave all records in place as a safety net
12. Wait for DNS propagation (usually minutes to a few hours, worst case 48 hours)

### Phase 4: Verify Everything Works
13. Verify site loads from Cloudflare Pages at liberty-collective.com
14. Send a test email TO an @liberty-collective.com address and confirm it arrives
15. Send a test email FROM an @liberty-collective.com address and confirm it sends
16. Wait a full 48 hours before considering anything on GoDaddy "safe to remove"

### Risk Window
During DNS propagation, some lookups may hit old nameservers (GoDaddy) and some hit new (Cloudflare). Since both have identical MX records pointing to the same Microsoft 365 servers, email works regardless of which nameserver responds. There is no gap where email could break if records match on both sides.

## Cloudflare Pages Project
- **Project:** liberty-collective
- **Production URL:** https://liberty-collective-7iw.pages.dev
- **GitHub Repo:** ChowdownMedia/liberty-collective
