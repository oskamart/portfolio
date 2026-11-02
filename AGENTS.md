# Working notes for other agents on this kit

This tree is shared. Several agents are working on the same portfolio at once.
This file says who owns what, so nobody overwrites anybody.

## The one thing that matters

**`index.html`, `assets/css/site.css` and `assets/js/site.js` are shared.**
Everyone edits them. Before you change one:

```bash
git pull --rebase          # take the others' work first
```

After you change one:

```bash
git add -A && git commit
git push                    # never --force
```

If someone else pushed while you were working, `git pull --rebase` and
resolve. Both agents' commits stay in the history with their names attached —
do not squash.

## Namespaces

Each agent keeps its own scratch files, port, and output directory. Nothing
under one agent's namespace should ever be edited by another.

| Agent | Port | Screenshots | Logs | Scratch tools |
|---|---|---|---|---|
| GLM | 8742 | `shots/glm-*` | `/tmp/opencode/glm-*` | `build/glm-shoot.py` |
| opencode | 8743 | `shots/opencode/` | `/tmp/opencode/opencode-logs/` | `build/opencode-shoot.py`, `build/opencode-shoot_at.py` |
| qwen-agent (Qwen3.8) | 8123 | (own tree: `~/portfolio-qwen/shots/`) | `/tmp/portfolio-qwen-serve.log` | own tree entirely |

Add a row for yourself when you start.

## Running a copy

```bash
# your own port, so you never fight another agent for 8080
python3 deploy/serve.py --host 0.0.0.0 --port <your-port>
```

The shared `deploy/serve.py` is fine to use — it only reads the tree.

## Before you finish

```bash
python3 build/manifest.py     # re-measure; other agents' projects are in there
python3 build/verify.py       # links, anchors, assets, accessible names
```

`build/manifest.py` holds the list of measured projects. If you add a project
to the page, add it there too, or its numbers will render as "—".

## Two rules that have already bitten

1. **Do not write numbers by hand.** Every figure on the page comes from
   `assets/manifest.json`, which `build/manifest.py` generates from the real
   source trees. If a number is on the page and not in the manifest, it is
   unverified.
2. **Do not `git push --force`.** The main branch is shared and fast-forwarded.

## What is where

```
index.html                 the page — shared
assets/css/site.css        styles — shared
assets/js/site.js          behaviour — shared
assets/manifest.json       measured numbers — generated, commit it
build/manifest.py          measures the source trees → manifest.json
build/verify.py            links, anchors, assets, accessible names
build/shoot.py             shared capture tool
deploy/                    production server, publish, DNS, systemd unit
```

## Publishing

`deploy/publish.sh` measures, verifies, commits, pushes and checks the live
site. The site is served by GitHub Pages from `oskamart/portfolio` with
`CNAME` = `osys.one`.

**The DNS change at the registrar is still outstanding.** `osys.one` currently
points at an AWS Global Accelerator address that redirects to
`osys.duckdns.org`, whose origin does not answer from the public internet.
To finish, the registrar has to publish:

| Name | Type | Value |
|---|---|---|
| `osys.one` | A | `185.199.108.153` |
| `osys.one` | A | `185.199.109.153` |
| `osys.one` | A | `185.199.110.153` |
| `osys.one` | A | `185.199.111.153` |
| `www.osys.one` | CNAME | `oskamart.github.io` |

The Proton Mail MX and SPF records must not be touched.

`deploy/godaddy_dns.py` does exactly this through the GoDaddy API, and only
for the two names above. It needs `GODADDY_API_KEY` and
`GODADDY_API_SECRET`. `deploy/check_domain.py` reports where the domain
currently stands.

## qwen-agent namespace

`~/portfolio-qwen` is a fully separate tree (own git repo, port 8123, launched via its `serve-qwen.sh`). It was forked from this repo's `main` at 21:07. Do not edit it or bind its port; nothing of it needs merging here unless the user asks.
