# Identity / Active Directory / Entra ID attack-path tooling

The BloodHound stack (BloodHound CE, AzureHound, SharpHound) has been the canonical identity attack-path platform since ~2016. In the 2025-2026 window, the core stack itself saw **one rewrite** (MSSQLHound → Go, April 2026) and **zero new competitors** — the graph-based AD/Entra attack-path problem is effectively solved at the OSS layer. What *did* ship is a ring of **adjacent tools** that extend identity attack-path analysis into new surfaces: federated authentication abuse (SAMLSmith, maSSO, OAuthSeeker), SaaS permission graphs (ForceHound → Salesforce), training environments (EntraGoat), and cloud enumeration primitives (ATEAM, AzDevRecon, Azure AppHunter, SquarePhish 2.0).

The strategic read: BloodHound is no longer just "the AD tool." SpecterOps is positioning it — and the underlying graph model — as the **universal identity attack-path engine**, with community and third-party ingestors feeding data from every identity-adjacent surface. The 2025-2026 releases documented here are the first wave of that expansion.

Conference context: [DEF CON 33](../conferences/defcon-33.md) Demo Labs and Cloud Village produced EntraGoat, SAMLSmith, OAuthSeeker, ATEAM, AzDevRecon, Azure AppHunter, and SquarePhish 2.0 in a single event. [Troopers 25](../conferences/troopers-25.md) (Heidelberg, June 2025) runs the only dedicated "Active Directory & Entra ID Security" conference track and remains the forward-looking venue for technique disclosures in this category.

---

## Comparison matrix

| Tool | Side | Target surface | Author | Release | Language | BloodHound integration |
|---|---|---|---|---|---|---|
| BloodHound CE | Dual | AD / Entra ID attack paths | SpecterOps | Established | Go + TypeScript | **Is** BloodHound |
| AzureHound | Offensive | Azure / Entra ID enumeration | SpecterOps | Established | Go | Native ingestor |
| MSSQLHound | Offensive | MSSQL → AD lateral movement | SpecterOps | Go rewrite Apr 2026 | Go | Native ingestor |
| EntraGoat | Training | Deliberately-vulnerable Entra ID | Semperis | New 2025 | Terraform + Bicep | Target environment |
| SAMLSmith | Offensive | AD FS / SAML / SaaS federation | Semperis | New 2025 | Go | None (standalone) |
| OAuthSeeker | Offensive | Azure / M365 OAuth phishing | Praetorian | New 2025 | Python | None (standalone) |
| maSSO | Offensive | OIDC / SAML SP testing | Doyensec | New 2026 | Python | None (standalone) |
| ForceHound | Offensive | Salesforce permission graphs | NetSPI | New 2026 | Python | CE ingestor (first SaaS graph) |
| ATEAM | Offensive | Azure tenant enumeration | NetSPI (Fosaaen, Elling) | New 2025 | PowerShell | None |
| AzDevRecon | Offensive | Azure DevOps enumeration | Raunak Parmar | New 2025 | Web UI | None |
| Azure AppHunter | Offensive | Service-principal permissions | Gyftos, Vourdas | New 2025 | PowerShell | None |
| SquarePhish 2.0 | Offensive | QR-code → Entra ID token theft | Romsdahl, Talebzadeh | New 2025 | Python | None |

---

## The SpecterOps core stack

### BloodHound Community Edition

**Repo:** `SpecterOps/BloodHound` -- License: Apache-2.0 -- Go + TypeScript + PostgreSQL + Neo4j.

BloodHound CE is the open-source graph-based attack-path analysis platform for Active Directory and Entra ID. It models principals, groups, GPOs, OUs, computers, sessions, ACLs, and trust relationships as a directed graph, then runs shortest-path and reachability queries to find attack chains that an adversary could exploit to reach high-value targets (Domain Admins, Tier Zero assets, cloud admin roles).

In 2026, BloodHound CE remains uncontested in its category. No OSS alternative has attempted to replicate the graph + ingestor + query-engine architecture. The commercial tier, BloodHound Enterprise, has expanded beyond AD and Entra ID into **Okta, GitHub, and Jamf** — attack paths now chain across identity systems. The CE edition tracks behind the Enterprise feature set, but the graph model and API are shared.

The most notable 2026 development on the practitioner side: **"Enhancing BloodHound with AI: Active Directory Attack Path Analysis via MCP and Claude AI"** (FMI Cybersecurity, March 2026) is the first published write-up of wrapping BloodHound's API via MCP for LLM-driven attack-path interpretation. The pattern — Claude queries the BloodHound graph, interprets shortest paths, and generates remediation recommendations in natural language — is the same MCP-wrapping pattern documented for Trivy and cloud-audit in [`cloud-posture.md`](./cloud-posture.md). Expect BloodHound MCP servers to appear as community projects in H2 2026.

### AzureHound

**Repo:** `SpecterOps/AzureHound` -- License: Apache-2.0 -- Go.

The Azure / Entra ID data collector for BloodHound. Enumerates Azure RM resources, Entra ID objects, role assignments, app registrations, service principals, and managed identities, then outputs JSON ingestible by BloodHound CE. AzureHound is to Azure what SharpHound is to on-prem AD — the data exfiltration layer that feeds the graph.

No significant changes in the 2025-2026 window beyond maintenance releases. The tool is stable and operationally complete for its scope.

### MSSQLHound — Go rewrite (April 2026)

**Repo:** `SpecterOps/MSSQLHound` -- License: Apache-2.0 -- **Go** (formerly C#/.NET).

MSSQLHound discovers MSSQL servers on a network, enumerates database links, linked-server chains, `xp_cmdshell` configurations, impersonation paths, and SQL agent jobs, then outputs BloodHound-ingestible JSON. The attack surface is the classic "SQL Server as a lateral-movement pivot" — a single misconfigured linked server can chain through 3-4 SQL instances into domain admin.

The April 2026 rewrite from C#/.NET to Go is the headline change:

- **Cross-platform.** The original required Windows + .NET; the Go binary runs on Linux, macOS, Windows. This is operationally significant — most red-team operators run from Linux.
- **SOCKS proxy support.** Native SOCKS5 support means MSSQLHound can run through a C2 tunnel (Sliver, Ligolo-ng, Chisel) without extra tooling. The .NET version required proxychains or similar.
- **Single binary, zero runtime deps.** Same deployment model as the rest of the Go-based SpecterOps stack.

SpecterOps blog post: *"MSSQLHound Now Available in Go"* (April 2026).

---

## New 2025-2026 tools

### EntraGoat (Semperis) — vulnerable Entra ID training lab

**Repo:** `Semperis/EntraGoat` -- Terraform + Bicep. DEF CON 33 Demo Labs.

EntraGoat is a deliberately-vulnerable Entra ID environment — the identity equivalent of DVWA, CloudGoat, or Whooli. It deploys a misconfigured Azure AD tenant with:

- Overprivileged app registrations and service principals
- Misconfigured Conditional Access policies
- Dangerous role assignments (Global Admin paths via nested groups)
- Consent grant attack surfaces
- Federation misconfigurations exploitable with tools like SAMLSmith

The value is training, not tooling. EntraGoat gives identity security teams a safe target to run BloodHound + AzureHound against, practice attack-path remediation, and validate detection rules — without touching production Entra ID. For teams building an identity security program, EntraGoat is the first place to start: deploy it, point AzureHound at it, import into BloodHound CE, and learn to read the graph.

### SAMLSmith (Semperis) — SAML response forging

**Repo:** `semperis/samlsmith` -- License: MIT -- Go. DEF CON 33 Demo Labs. Authors: Eric Woodruff, Tomer Nahum.

SAMLSmith forges SAML responses for red-team operations against AD FS and SAML-federated SaaS applications. Given a signing certificate (extracted from a compromised AD FS server, or a misconfigured federation trust), SAMLSmith generates arbitrary SAML assertions — impersonate any user, inject any claim, target any relying party.

The tool operationalizes the **Golden SAML** attack class (MITRE ATT&CK T1606.002) that was central to the SolarWinds/SUNBURST incident. Prior to SAMLSmith, executing Golden SAML required manual XML crafting or the ADFSDump + shimit chain. SAMLSmith collapses this to a single CLI invocation.

Operational scope: AD FS as IdP, any SAML 2.0 SP as target. This includes M365, AWS SSO, Salesforce, ServiceNow, Workday — anything that consumes a SAML assertion from a federated AD FS instance.

### OAuthSeeker (Praetorian) — OAuth phishing simulation

**Repo:** `praetorian-inc/oauthseeker` -- License: Apache-2.0 -- Python. DEF CON 33 Demo Labs.

OAuthSeeker automates OAuth device-code phishing attacks against Azure / M365 targets. The device-code flow (RFC 8628) is the same mechanism exploited in the Storm-1811 / Midnight Blizzard campaigns of 2024-2025 — the user visits `microsoft.com/devicelogin`, enters a code, and unknowingly grants an attacker's application access to their tokens.

OAuthSeeker packages the full phishing lifecycle:

- Generates device-code authorization requests against Entra ID
- Serves phishing pages (or integrates with existing phishing infrastructure)
- Polls for token completion
- Extracts access and refresh tokens on successful auth
- Supports custom application registrations for scope control

This is the phishing-simulation counterpart to SquarePhish 2.0 (which focuses on QR-code delivery). Both target the same Entra ID token-issuance surface, but OAuthSeeker is purely device-code-flow, while SquarePhish 2.0 uses QR codes as the social-engineering vector.

### maSSO (Doyensec) — malicious IdP for SP testing

**Repo:** `doyensec/cloudsec-tidbits/tree/main/lab-masso` -- Python. New 2026.

maSSO is a malicious Identity Provider for testing OIDC and SAML Service Provider implementations. It is the **identity-protocol analog of Burp Collaborator** — a controlled evil server that lets you probe how a target SP handles adversarial federation responses.

Three attack classes implemented:

1. **JIT ghost identity injection.** Exploits Just-In-Time provisioning: maSSO sends a SAML/OIDC assertion for a user that does not exist in the SP's directory. If the SP auto-provisions on first login (common in SaaS), the attacker creates an arbitrary account in the target tenant.
2. **IdP identifier hijacking.** Registers a malicious IdP with an identifier that collides with or shadows a legitimate IdP in the SP's federation configuration. Exploits weak IdP validation in multi-tenant SaaS.
3. **Federated username parsing attacks.** Sends assertions with ambiguous or malformed username claims (email-like identifiers with special characters, domain confusion, case sensitivity mismatches) to trigger account linking to existing legitimate users.

maSSO is the first purpose-built offensive tool for testing the SP side of federation. Prior approaches required manually configuring Keycloak or Okta as a "malicious" IdP — maSSO is designed adversarial from the ground up.

### ForceHound (NetSPI) — Salesforce attack paths in BloodHound

**Repo:** `NetSPI/ForceHound` -- Python. New 2026.

ForceHound is the first tool to apply graph-based attack-path analysis to **Salesforce**. It enumerates Salesforce org permissions — profiles, permission sets, sharing rules, field-level security, record access — and exports the data as BloodHound CE-ingestible JSON.

This is architecturally significant: it extends the BloodHound graph model beyond Microsoft identity (AD, Entra ID, Azure RM) into SaaS. A single BloodHound CE instance can now visualize attack paths that start in on-prem AD, traverse Entra ID via federation, and terminate at sensitive Salesforce records — if both AzureHound and ForceHound data are imported.

ForceHound models:
- User → Profile → Permission Set assignment chains
- Object-level and field-level CRUD permissions
- Sharing rules and record-level access grants
- Admin-equivalent permission combinations (Modify All Data, View All Data, Manage Users)

The Salesforce permission model is notoriously opaque — nested profiles, permission set groups, and org-wide defaults interact in ways that even experienced Salesforce admins struggle to audit. ForceHound makes the effective-permission graph queryable in Cypher, using the same BloodHound query patterns AD teams already know.

---

## Cloud enumeration tools (DEF CON 33 Cloud Village)

Four tools released at the [DEF CON 33 Cloud Village](../conferences/defcon-33.md) that serve as **reconnaissance feeders** for identity attack-path work:

**ATEAM** (Azure Tenant Enumeration and Attribution Module) — Karl Fosaaen and Thomas Elling, NetSPI. Enumerates Azure tenants, maps tenant-to-domain relationships, and attributes infrastructure to organizations. The recon layer that answers "what Azure tenants does this target operate?" before AzureHound collection begins.

**AzDevRecon** — Raunak Parmar. Web-based Azure DevOps enumeration tool. Discovers organizations, projects, repositories, pipelines, and service connections in Azure DevOps. The identity-adjacent value: Azure DevOps service connections often hold service-principal credentials or managed-identity assignments that feed back into Entra ID attack paths.

**Azure AppHunter** — Marios Gyftos, Nikos Vourdas. Scans Entra ID for overprivileged service principals and app registrations. Identifies dangerous API permission grants (Mail.ReadWrite, RoleManagement.ReadWrite.Directory, Application.ReadWrite.All) that enable privilege escalation or data exfiltration without user interaction. This is the automated version of the manual "audit app registrations" checklist most Entra ID hardening guides recommend.

**SquarePhish 2.0** — Nevada Romsdahl, Kam Talebzadeh. QR-code-based phishing toolkit targeting Entra ID token acquisition. Generates QR codes that resolve to device-code or authorization-code flows, delivered via email or physical media. The 2.0 release adds token-refresh persistence and multi-tenant support. Complements OAuthSeeker — same token-theft objective, different social-engineering vector.

---

## Attack-path evolution: from AD graphs to cross-identity chains

The 2025-2026 tools reveal three structural shifts in how identity attack paths are modeled and exploited:

**1. The graph model is absorbing non-Microsoft surfaces.**

BloodHound started as an AD-only tool. AzureHound added Entra ID. ForceHound adds Salesforce. BloodHound Enterprise (commercial) now ingests Okta, GitHub, and Jamf. The trajectory is clear: every system that issues identities or grants permissions will eventually have an ingestor that feeds the BloodHound graph. The OSS community is following the Enterprise roadmap with a 6-12 month lag.

The SpecterOps blog post *"Identity APM Has Gone Mainstream"* (April 2026) — based on a survey of 500+ security decision-makers — explicitly frames this as the "Identity Attack Path Management" category. The thesis: every identity system is an attack surface, and the paths between them are where breaches happen. The Vercel breach analysis (*"The Vercel Breach Explains Why Identity Attack Path Management Can't Wait"*, April 2026) demonstrates the pattern with non-human identities (NHI) — service accounts, API keys, OAuth apps — as the pivot points.

**2. Federation protocols are now a first-class attack surface.**

SAMLSmith, maSSO, and OAuthSeeker together cover the three major federation attack classes:

| Attack class | Protocol | Tool | Prior art |
|---|---|---|---|
| Golden SAML (forged assertions) | SAML 2.0 | SAMLSmith | ADFSDump + shimit (manual) |
| Malicious IdP (SP-side testing) | OIDC + SAML | maSSO | Manual Keycloak config |
| Device-code phishing | OAuth 2.0 | OAuthSeeker | Custom scripts per engagement |

Before 2025, executing these attacks required significant manual setup. The tooling gap meant federation misconfigurations were under-tested relative to their risk. These three tools lower the barrier enough that federation testing should now be standard in any identity-focused red-team engagement.

**3. Non-human identities (NHI) are the new Tier Zero.**

The common thread across AzureHound (service principals, managed identities), Azure AppHunter (overprivileged app registrations), ForceHound (connected apps, API users), and the SpecterOps NHI research is that **machine identities now outnumber human identities in most enterprises, and their attack paths are less monitored**. BloodHound CE already models service principals; the 2026 direction is deeper NHI coverage — OAuth apps, API keys, workload identity federation, and machine-to-machine trust chains.

---

## Strategic recommendations

**For teams with an existing BloodHound deployment:**

1. **Add MSSQLHound (Go) to your collection pipeline.** The Go rewrite removes the Windows/.NET dependency. If you have SQL Server infrastructure, MSSQL lateral-movement paths are likely present and unmonitored.
2. **Evaluate ForceHound if you run Salesforce.** Import ForceHound data alongside AzureHound data into the same BloodHound CE instance. The cross-surface graph queries ("shortest path from compromised AD user to Salesforce Modify All Data") are the payoff.
3. **Deploy EntraGoat as a training lab.** Run AzureHound against it, import into BloodHound CE, and use it to train junior analysts on attack-path interpretation before pointing them at production data.

**For teams building an identity red-team capability:**

4. **Add SAMLSmith to your AD FS engagement toolkit.** If the client uses AD FS for SaaS federation, Golden SAML should be in-scope. SAMLSmith operationalizes the attack in a single CLI invocation.
5. **Use maSSO to test SP-side federation handling.** JIT provisioning, IdP identifier collisions, and username-parsing attacks are common in SaaS implementations and rarely tested. maSSO is the first tool that makes this systematic.
6. **Run OAuthSeeker or SquarePhish 2.0 for Entra ID phishing simulations.** Device-code and QR-code phishing are the dominant initial-access vectors for Azure/M365 compromise in 2025-2026. Both tools provide the controlled simulation that compliance teams require.

**For teams doing cloud recon:**

7. **Chain ATEAM → AzureHound → BloodHound CE.** ATEAM identifies the tenant; AzureHound collects the graph; BloodHound CE visualizes the paths. Azure AppHunter and AzDevRecon fill gaps in service-principal and DevOps reconnaissance respectively.

**For the BloodHound + AI pattern:**

8. **The MCP-wrapping pattern from FMI Cybersecurity is worth replicating.** BloodHound's Cypher API is a natural fit for LLM-driven query generation and path interpretation. If your team already uses Claude or another LLM operationally, wrapping BloodHound via MCP is a low-effort, high-leverage integration.

---

## Where the category is going

1. **More BloodHound ingestors for SaaS platforms.** ForceHound proves the pattern; expect community ingestors for ServiceNow, Workday, AWS IAM Identity Center, and Google Workspace within 12 months. The graph model is extensible; the only bottleneck is someone writing the enumerator and the node/edge type definitions.

2. **Federation testing will become standard red-team scope.** SAMLSmith, maSSO, and OAuthSeeker collectively make federation attacks accessible enough that "test our SAML/OIDC federation" will become a standard line item in identity-focused engagements, not a specialist add-on.

3. **NHI attack paths will drive the next BloodHound CE feature cycle.** The SpecterOps NHI research (Vercel breach analysis, "Identity APM" report) signals that service principals, OAuth apps, managed identities, and workload-identity federation are the priority attack surface for 2026-2027. Expect BloodHound CE to add deeper NHI modeling — currently it captures service principals but does not fully model OAuth consent grants, API permission chains, or cross-cloud workload-identity trust.

4. **The Troopers 25 AD & Entra ID track will produce technique disclosures.** Troopers' dedicated Track 3 is the leading indicator for identity attack techniques 6-12 months before tooling catches up. Monitor the track program for signals on what the next wave of tools will automate.

5. **Identity attack-path analysis will subsume CIEM.** Cloud Infrastructure Entitlement Management (CIEM) tools like Ermetic (acquired by Tenable), ZEST (Zscaler), and CloudKnox (acquired by Microsoft) model cloud permissions. BloodHound's graph approach models the same permissions *plus* the attack paths between them. As BloodHound ingests more cloud identity sources, the boundary between "attack-path tool" and "entitlement management tool" will blur. The OSS version of this convergence is already visible in ForceHound and the BloodHound Enterprise Okta/GitHub/Jamf integrations.
