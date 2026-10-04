# Installing the `contexta-init` skill

The `contexta-init` skill produces the `KNOWLEDGE.md` file that contexta's indexer reads. Install it once per service repo.

## 1. Copy the skill into your service

From the root of your service repo:

```sh
mkdir -p .claude/skills
cp -r /path/to/contexta/skills/contexta-init .claude/skills/contexta-init
```

Or clone contexta somewhere and symlink if you'd rather pull updates automatically:

```sh
mkdir -p .claude/skills
ln -s /path/to/contexta/skills/contexta-init .claude/skills/contexta-init
```

Resulting layout inside your service:

```
<your-service>/
├── .claude/
│   └── skills/
│       └── contexta-init/
│           ├── SKILL.md
│           └── template.md
└── ... (your code)
```

## 2. Commit it

```sh
git add .claude/skills/contexta-init
git commit -m "Add contexta contexta-init skill"
```

Committing means every teammate (and every future Claude Code session on this repo) picks it up automatically.

## 3. Run it

Open the service in Claude Code and run:

```
/contexta-init
```

The skill will scrape your repo, ask a short set of questions, and write `KNOWLEDGE.md` at the repo root. First run takes ~5 minutes; later runs only ask about sections you flag as stale.

## 4. Commit the output

```sh
git add KNOWLEDGE.md
git commit -m "Add KNOWLEDGE.md for contexta"
```

contexta's indexer runs on a schedule and pulls `KNOWLEDGE.md` from each registered repo — no further action needed from you.

## 5. Push it to contexta now (optional)

If the k8s indexer isn't running yet, or you want your file in Qdrant immediately, index it from Claude Code via the `contexta` MCP server. See [connect-mcp.md](connect-mcp.md#indexing-a-repo-from-claude-code) for the full prompt and argument shape.

## Updating

Re-run `/contexta-init` whenever something material changes (new component, new dashboard, team handover, significant architecture decision). The skill is diff-aware and will only re-ask what you tell it is stale.