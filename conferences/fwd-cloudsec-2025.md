# fwd:cloudsec NA 2025

**June 2025**

Smaller, focused, technical cloud-security conference. fwd:cloudsec runs a **Technical Oversight Committee** that adopts community OSS cloud-security projects — its sponsorship of long-term tools (CloudFox, IAMVulnerable, BadPods, Prowler) is one reason much of cloud OSS still survives commoditization.

Primary pages:
- Speakers + abstracts: https://fwdcloudsec.org/conference/north-america/speakers.html
- Projects page: https://fwdcloudsec.org/projects/ , https://next.fwdcloudsec.org/projects/
- Pretalx: https://pretalx.com/fwd-cloudsec-2025/
- Talk summaries (community): https://github.com/Cybr-Inc/fwdcloudsec-2025-summaries — also at https://cybr.com/announcements/fwdcloudsec-2025-conference-talks-summarized/

---

## Talks that released open-source code

- **Taming LLMs to Detect Anomalies in Cloud Audit Logs** (Yigael Berger) — Released: CloudTrail-log parsing code, LLM training code, web app for anomaly visualization.
- **What would you ask a crystal ball for AWS IAM?** (Nick Siow) — Released: new open-source building blocks for IAM policy analysis and access modeling.
- **Trust Issues: What Do All these JSON files actually mean?** (David Kerber) — Released: open-source IAM-permission simulator across policy layers.
- **Prowler ↔ AWS Security Hub** — automation pattern session; serverless architecture for routing Prowler findings into Security Hub.

## Notable research talks (no public tool release)

- **Breaking AI Agents: Exploiting Managed Prompt Templates to Take Over Amazon Bedrock Agents** (Jay Chen, Royce Lu) — high-impact agent-takeover technique on Bedrock managed templates.
- **Double Agents: Exposing Hidden Threats in AI Agent Platforms** — broader survey of attack patterns on agent platforms.
- **Bypassing AI Security Controls with Prompt Formatting** (Nathan Kirk).
- **Challenges around AI as a Service logging** — what cloud-AI services log vs. need to log for IR.
- **Farewell False Positives — Trustworthy AI for IaC Analysis** (Emily Choi-Greene).
- **Inside Microsoft's Battle Against Cloud-Enabled Deepfake Threats.**
- **ECS-cape — Hijacking IAM Privileges in Amazon ECS** (Naor Haziz).
- **whoAMI — Discovering and Exploiting AMI Name Confusion** (Seth Art) — cross-listed with DEF CON 33 Cloud Village.
- **Beyond the Big Three — Mastering Oracle Cloud Security** (Dani Kaganovitch).
- **Data Perimeter Implementation Strategies** (Agnel Amodia, Ben Joyce).

## Foundational tools repeatedly featured

Seth Art is a recurring speaker; the open-source toolkit anchored on his work is essentially the "reference stack" for AWS pentesting:

- **CloudFox** — situational awareness in AWS (find privesc paths quickly).
- **CloudFoxable** — vulnerable AWS environment companion for training.
- **IAMVulnerable** — Terraform-deployed deliberately-vuln AWS IAM lab.
- **BadPods** — collection of malicious Kubernetes pod manifests for privilege-escalation training.
- **Prowler** — most heavily used OSS AWS/GCP/Azure security scanner.

---

## Strategic read

The community-OSS picture in cloud security is **fragmenting in 2025**. Press recaps (Cybr, Red Canary) note many cloud-OSS projects that emerged 2019–2021 have either been commercialized or abandoned; fwd:cloudsec's Technical Oversight Committee is one of the few governance bodies trying to keep that ecosystem alive. fwd:cloudsec discussions in 2025 also raised whether GenAI-assisted coding + MCP servers will *revive* OSS cloud tooling production — too early to tell.

---

## Sources
- fwd:cloudsec speakers: https://fwdcloudsec.org/conference/north-america/speakers.html
- Red Canary recap: https://redcanary.com/blog/news-events/fwdcloudsec-2025/
- Cybr summaries: https://cybr.com/announcements/fwdcloudsec-2025-conference-talks-summarized/
- Cybr-Inc summary repo: https://github.com/Cybr-Inc/fwdcloudsec-2025-summaries
