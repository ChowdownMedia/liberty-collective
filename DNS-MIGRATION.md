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

## Migration Steps
1. Add liberty-collective.com domain to Cloudflare
2. Cloudflare will assign new nameservers
3. Recreate ALL MX and TXT records above in Cloudflare DNS FIRST
4. Add CNAME record pointing domain to Cloudflare Pages project (liberty-collective.pages.dev)
5. Switch nameservers at GoDaddy from domaincontrol.com to Cloudflare nameservers
6. Wait for DNS propagation (up to 48 hours, usually faster)
7. Verify email still works
8. Verify site loads from Cloudflare Pages

## Cloudflare Pages Project
- **Project:** liberty-collective
- **Production URL:** https://liberty-collective-7iw.pages.dev
- **GitHub Repo:** ChowdownMedia/liberty-collective
