# Development moves onto the Proxmox box

Code, agent sessions and preview stacks all move into LXC 102 on the
Proxmox node. A walkthrough needs a live site, and one shared bench could
only hold one branch - deploying T6 destroyed T7's job data, because
`bench migrate` deletes doctypes whose files vanish between branches. The
fix is **one throwaway Docker Compose stack per ticket**, each on a
deterministic port derived from the ticket name, created and destroyed by
`scripts/preview.sh`, with each branch seeding its own data at boot.

Putting the sessions on the same box is what makes that cheap. Nearly all
of today's deploy cost is transport: archive the worktree, `scp` it to the
node, `pct push` it into the container, delete every tracked file, extract,
commit, fetch, checkout, rebuild, migrate. When the code already lives
where Docker runs, that becomes `docker compose up` against a git worktree
- and every agent tool call stops paying an ssh → `pct exec` → `docker exec`
triple hop.

Automated tests do not run on a preview stack. CI builds a fresh site per
branch and is the authority on whether the suite passes; a stack is for a
human to click through.

> **Briefly superseded by ADR-0004 (2026-08-25), then restored the same
> day.** The `CI` workflow was disabled over billing and the suites ran on
> this box by hand; making the repository public made Actions free and the
> workflow came back. Both sentences above hold again. ADR-0004 is kept for
> the by-hand commands and for the `bench migrate` trap it found.

## Considered options

- **The founder's Windows PC with WSL2 + Docker Desktop.** More free RAM
  (14.6GB) and vastly more disk (3.6TB), and it also removes the transport
  step since each session already has a worktree there. Rejected once the
  founder accepted the two costs that had been holding it back: moving to
  SSH-based sessions, and losing the DaVinci Resolve MCP, which only talks
  to Resolve on that machine. Linux end-to-end also retires a class of
  Windows friction - CRLF translation on every `git add`, `-c
  core.autocrlf=false` on archives, and the `frappeProxy` vite plugin that
  is disabled because its bench-path walk never terminates on Windows.
- **Keep one shared stack and serialise.** Rejected: the founder wants to
  review one ticket while others are still being built, which is the whole
  reason this came up.
- **Hostname routing through a reverse proxy** (`t6.aura.local`). Nicer to
  read than `:8006`, but it adds a proxy container plus DNS or hosts-file
  entries on every device a walkthrough happens from. Deferred, not
  rejected.

## Consequences

- LXC 102 grows to **8 cores / 16GB / 100G rootfs**. Cores overcommit
  harmlessly (the node already runs 23 vCPU across 12). The 16GB is a
  config ceiling, not an allocation - the node only has ~13GB genuinely
  available, because a macOS VM pins 12.3GB with ballooning off. Stopping
  that VM is the only lever if this ever proves tight.
- Sessions run over **VS Code Remote-SSH**, so an editor, a file tree and
  several concurrent Claude Code terminals all live on the box. The
  desktop app's browser pane and visual tooling are given up.
- **The tar-and-extract deploy is gone entirely** - each preview is its
  own clone of the branch, so no files travel between machines and
  `/opt/auraos` no longer accumulates leftovers from unmerged branches.
  (Git worktrees were the first attempt and do not work here: `bench
  get-app` clones `/workspace/repo` from inside the container, and a
  linked worktree's `.git` is a file pointing at a parent object store
  that isn't mounted there.)
- Concurrency is capped at **three running stacks**; a fourth stops the
  least-recently-used one, which restarts in seconds because its volume
  survives. A stack untouched for seven days is pruned when the next boots.
- The box stops hosting a `test_site`. A red test there had stopped
  meaning anything: 56 rows committed by an earlier build made two
  unrelated tests fail for everyone afterwards.
- Preview data is disposable and code is pushed to GitHub, so **nothing
  here needs backing up** - which keeps development outside T13's Synology
  backup scope. What does now matter is that the box is a single point of
  failure for day-to-day work, where before it only held a test site.
