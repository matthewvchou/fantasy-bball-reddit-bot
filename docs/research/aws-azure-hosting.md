# Small-server hosting on AWS or Azure (issue #33)

Researched 2026-11-11. Question: which small-server options fit one box running SQLite, a cron ingest, a website, and the Python bot, under $20/month? Compare price, disk, backup. Check whether cloud IPs are blocked by the NBA stats API.

All prices are USD, Linux, US East, list price, checked 2026-11-11. Monthly = hourly x 730 h (my arithmetic).

## Short answer

- Several options fit under $20/month on both clouds. Cheapest sensible: Lightsail $7 (1 GB, 40 GB SSD) or EC2 t4g.small ~$12 + disk + IPv4.
- Cost is not the problem. The NBA stats API is. Many reports say stats.nba.com times out from cloud IPs, including AWS and Azure. No official source confirms or denies it. Test from the real box before committing.

## AWS options

### Lightsail (flat bundle: compute, SSD, transfer, IPv4 included)
Source: https://aws.amazon.com/lightsail/pricing/ (fetched 2026-11-11)

| RAM | vCPU | SSD | Transfer | IPv4 | IPv6-only |
|---|---|---|---|---|---|
| 0.5 GB | 2 | 20 GB | 1 TB | $5 | $3.50 |
| 1 GB | 2 | 40 GB | 2 TB | $7 | $5 |
| 2 GB | 2 | 60 GB | 3 TB | $12 | $10 |
| 4 GB | 2 | 80 GB | 4 TB | $24 | $20 |

- Fits under $20: the 0.5, 1, and 2 GB plans (IPv4). 1 GB or 2 GB is the realistic pick for site + bot + cron.
- IPv6-only is cheaper but the box could not reach IPv4-only hosts directly. Not checked whether stats.nba.com has IPv6; avoid.
- Backups: snapshots cost $0.05 per GB-month (same page). Automatic snapshots: daily, latest 7 kept; they are deleted if the instance is deleted unless kept; manual snapshots are kept until deleted. Source: https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-snapshots-in-amazon-lightsail.html (fetched 2026-11-11). Automatic snapshots are billed at the same storage fee per that doc.
- Rough backup cost: a 40 GB instance snapshot is up to ~$2/month per stored snapshot (40 x $0.05). I did not verify whether Lightsail snapshots are incremental; 7 daily could be up to ~$14 worst case. Unverified.
- A free trial exists; the pricing page does not give its terms.

### EC2 (pay per piece)
Prices from the AWS public pricing JSON that feeds the pricing page (us-east-1, Linux, on-demand), fetched 2026-11-11:

| Type | Spec (not re-verified here) | $/hour | ~$/month |
|---|---|---|---|
| t4g.micro | 2 vCPU, 1 GB, ARM | 0.0084 | 6.13 |
| t4g.small | 2 vCPU, 2 GB, ARM | 0.0168 | 12.26 |
| t3.micro | 2 vCPU, 1 GB | 0.0104 | 7.59 |
| t3.small | 2 vCPU, 2 GB | 0.0208 | 15.18 |

Add-ons:
- Public IPv4: $0.005/hour = ~$3.65/month, charged even when idle. Source: https://aws.amazon.com/vpc/pricing/ (2026-11-11).
- EBS gp3: $0.08/GB-month, e.g. 30 GB = $2.40. Snapshots $0.05/GB-month (archive $0.0125, 90-day minimum). Source: https://aws.amazon.com/ebs/pricing/ (2026-11-11; the page gives an example region, rates vary by region).
- Example: t4g.small + 30 GB gp3 + IPv4 = 12.26 + 2.40 + 3.65 = ~$18.31, before snapshots and egress. The t4g.micro version is ~$12.18.
- T-series CPU credit "Unlimited" surcharge is $0.04/vCPU-hour (T4g), only if sustained CPU exceeds baseline. Source: https://aws.amazon.com/ec2/pricing/on-demand/ (2026-11-11).
- Backups: EBS snapshots, automatable with Data Lifecycle Manager (cost not stated on the EBS page; not verified). Lightsail is simpler for one box and cheaper in total.
- ARM (t4g) needs the Python deps to have arm64 wheels; not checked.

## Azure options

Prices from the Azure Retail Prices API (https://prices.azure.com/api/retail/prices), region eastus, Consumption, Linux, queried 2026-11-11. The Azure pricing web pages did not render prices to my fetcher, so the API is the source.

| Size | $/hour | ~$/month |
|---|---|---|
| B2pts_v2 (ARM) | 0.0084 | 6.13 |
| B2ats_v2 | 0.0094 | 6.86 |
| B1s | 0.0104 | 7.59 |
| B1ms | 0.0207 | 15.11 |
| B2s | 0.0416 | 30.37 (over budget) |

Add-ons (same API, eastus, 2026-11-11):
- Standard static public IPv4: $0.005/hour = ~$3.65/month. Basic static is $0.0036/hour (~$2.63).
- Managed disks: Standard SSD E4 (32 GB) $2.40/month; E6 (64 GB) $4.80/month. Premium SSD P4 (32 GB) $5.28/month; P6 (64 GB) $10.21/month. Standard SSD also adds $0.002 per 10K operations.
- Example: B1ms + 32 GB Standard SSD + static IP = ~15.11 + 2.40 + 3.65 = ~$21.16. Over $20. B1s or B2ats_v2 versions are ~$13.6 to $14.4.
- Not verified: RAM/vCPU of each size, VM disk snapshot pricing, Azure Backup pricing. The Azure pricing page confirms the OS disk is billed at the regular disk rate and a stopped VM is billed unless "Stopped (Deallocated)". Source: https://azure.microsoft.com/en-us/pricing/details/virtual-machines/ (2026-11-11). It also lists a 30-day $200 credit.
- Azure has no bundle like Lightsail; more pieces to configure.

## SQLite and disk notes
- All options use local block disks. SQLite on a single VM disk is fine. Back up with the SQLite `.backup` command or a copy to object storage (S3/Blob) rather than relying only on a disk snapshot taken mid-write. This is general SQLite practice, not checked against a source here.
- 20 to 40 GB is likely enough; I did not size the database.

## NBA stats API and cloud IPs

No official NBA document says cloud IPs are blocked. Evidence is community reports from the nba_api issue tracker (not NBA itself):

- "The NBA blocks all cloud hosting providers" and integration tests are not run from CI because of it. Comment by a contributor, 2021-02-02: https://github.com/swar/nba_api/issues/176#issuecomment-771991604. The same comment recommends a proxy and ~0.6 s sleeps between calls (throttling is a separate issue). The commenter had not tried the proxy, and the source of the claim is unknown.
- Timeouts reported from AWS EC2 and Lambda: https://github.com/swar/nba_api/issues/163 (2020), https://github.com/swar/nba_api/issues/498 (2025-01), https://github.com/swar/nba_api/issues/510 (2025-03). 498 and 510 were closed by pointing to #176.
- Other clouds: GCP https://github.com/swar/nba_api/issues/419, GitHub Codespaces https://github.com/swar/nba_api/issues/505.
- Azure: a user in #176 (2021-01-29) reports timeouts only after deployment. Not independently confirmed.
- Latest: https://github.com/swar/nba_api/issues/728 (opened 2026-10-22, open): timeouts from a Render cron job and also from a local Windows machine. A reply on 2026-10-23 says the same script works for them. So timeouts are not always cloud-specific.
- Counter-evidence: a Lambda user on a forum reported other sites work from Lambda, so general egress is fine. Missing headers can also cause timeouts.

Conclusion: treat as likely blocked or flaky from AWS and Azure datacenter IPs. I do not know the current state.

## Recommendation for the map (#28)
1. Before picking a host, run a test call to stats.nba.com (e.g. the box-score endpoint) from a Lightsail trial box and from an Azure VM for a day.
2. If blocked, options are: a residential proxy (extra cost, not researched), running only the ingest at home and pushing the SQLite file to the server, or using a data source other than stats.nba.com. None are researched here.
3. If not blocked, Lightsail $7 or $12 is the simplest fit with built-in daily snapshots.
