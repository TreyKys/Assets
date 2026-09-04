# Alibaba Cloud ECS setup — Exodus desktop hunt

Two tiers, don't pay for the bigger one until Step A finds something worth
filming (see `DESKTOP-HUNT-PLAYBOOK.md`).

- **Tier A (now):** extract + push `app.asar` JS. Tiny/cheap, no GUI.
- **Tier C (later):** run the real GUI + record the video PoC. Only spin this up
  once I've picked a candidate bug from the static read.

---

## 1. Account & verification

1. Sign up at `alibabacloud.com` (or `www.aliyun.com` for the China site — use
   the international `.com` site).
2. You'll need **real-name / ID verification** before you can launch ECS
   instances (passport or govt ID + a card for billing). This can take a few
   minutes to a day. Do this first — it's the only step that can stall you.
3. Add a payment method. Use **Pay-As-You-Go**, not a subscription — for a few
   days of testing this is pennies, and you can stop/release the instance the
   moment you're done recording.

## 2. Launch the Tier A instance (extraction only)

Console → **ECS (Elastic Compute Service)** → **Create Instance** → *Custom
launch* (skip the wizard defaults).

| Setting | Value | Why |
|---|---|---|
| **Billing** | Pay-As-You-Go | control cost, easy to release |
| **Region** | Whichever is cheapest/closest to you (e.g. Singapore) | doesn't matter for this step, no GUI/streaming yet |
| **Instance type** | `ecs.t6` or `ecs.e` burstable family, **1 vCPU / 1–2 GB** (smallest available) | we're only unzipping + running `npx asar extract`, no app execution |
| **Image** | **Ubuntu 22.04 64-bit** | matches the playbook's commands |
| **System disk** | 20–40 GB, standard/cloud SSD | the extracted app.asar contents are a few hundred MB |
| **Network** | Default VPC, assign a **public IP** (or bind an EIP after) | you need SSH in |
| **Security group** | create new — see §3 | lock it down |
| **Key pair** | create/upload an **SSH key pair**, not password auth | more secure, no brute-force surface |

Confirm and launch. Note the public IP once it's running.

## 3. Security group (lock it to you)

In the security group rules, **only allow inbound port 22 (SSH) from your own
current IP** (`https://checkip.amazonaws.com` or similar to find it), not
`0.0.0.0/0`. Nothing else needs to be open for Tier A. When you move to Tier C
later, you'll add port 5900 (VNC) or similar — same rule, restrict to your IP.

## 4. Connect

```bash
chmod 600 your-key.pem
ssh -i your-key.pem root@<public-ip>          # Alibaba Ubuntu images default to root, or 'ubuntu'
```

First commands on the box:

```bash
apt update && apt -y upgrade
apt -y install unzip curl nodejs npm
node -v   # sanity check
```

## 5. Do the extraction (from the playbook)

```bash
# 1) Download the Linux build from https://www.exodus.com/download
curl -A "h1-<your-username> exodus-research" -L -o exodus.zip "<linux-zip-url>"

# 2) Unzip and find the asar
unzip -q exodus.zip -d exodus_app
find exodus_app -name "app.asar"

# 3) Extract bundled JS
npx --yes @electron/asar extract exodus_app/**/resources/app.asar app_src

# 4) Push it to the repo for me to audit (skip node_modules, keep it lean)
git clone https://github.com/TreyKys/Assets.git
cd Assets
git checkout claude/jsonrpc-relay-resilience-yhzj9q
mkdir -p exodus_h1/desktop_app_src
cp -r ../app_src/* exodus_h1/desktop_app_src/
rm -rf exodus_h1/desktop_app_src/node_modules
git add exodus_h1/desktop_app_src
git commit -m "Add extracted Exodus desktop app.asar JS for static audit"
git push
```

(You'll need a GitHub credential on the box — either a personal access token
when it prompts for a password, or push from your own machine instead if
that's easier: `scp -r -i your-key.pem root@<ip>:~/app_src ./` then push
locally.)

## 6. When you're done with Tier A

**Stop or release the instance** (Console → Instance → Stop, or Release if
you're fully done) so you're not paying for idle compute while I do the
reading on my end. Spin Tier C up fresh once we have a target — I'll give you
the exact bigger spec (2 vCPU/4GB+) and the GUI/ffmpeg recording steps from
`DESKTOP-HUNT-PLAYBOOK.md` §Step C at that point.

---

**Next:** once `exodus_h1/desktop_app_src` lands in the repo, tell me and I'll
start the static audit immediately.
