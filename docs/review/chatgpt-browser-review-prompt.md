You are reviewing a Python CLI project as a skeptical principal engineer.

Project: `clinstagram`

What it is:
- A Python 3.10+ Typer CLI package.
- It exposes a single CLI, `clinstagram`.
- It is meant to route Instagram actions across three backends:
  - `graph_ig`: official Instagram Graph API
  - `graph_fb`: official Facebook Graph API
  - `private`: private Instagram API via `instagrapi`
- It has policy/compliance modes that are supposed to control what routing is allowed:
  - `official-only`
  - `hybrid-safe`
  - `private-enabled`
- It is designed for both human CLI use and AI-agent use.

Important CLI behavior to understand before reviewing:
- Global flags must come before the subcommand, for example:
  - `clinstagram --json dm inbox`
  - not `clinstagram dm inbox --json`
- The CLI can emit structured JSON.
- The dispatch layer is the real execution spine:
  - command -> feature enum -> router -> backend instance -> backend method -> JSON/error output
- The router is supposed to prefer official APIs first, then private, subject to capability support and compliance mode.
- Config is persisted under `~/.clinstagram` unless overridden.
- Secrets are stored via keyring in production and memory in test mode.

What I want from you:
- Do a real code review, not a summary.
- Assume the docs may overstate reality.
- Treat passing tests as weak evidence, not proof.
- Look for logic bugs, product gaps, hidden assumptions, routing mismatches, incomplete implementations, unsafe defaults, API misuse, and areas where the tests are giving false confidence.
- Be willing to say "this looks shipped but is not actually production-ready" if that is the right conclusion.

Review priorities:
1. Mismatches between:
   - README / claimed behavior
   - command layer
   - feature enum / capability matrix
   - router policy
   - backend implementations
   - test coverage
2. Routing and policy correctness:
   - whether the chosen backend is actually the right one
   - whether compliance modes block or allow the right operations
   - whether "safe" vs "growth" behavior is enforced consistently
3. Backend contract correctness:
   - whether backend methods actually match the APIs they claim to call
   - whether return shapes are consistent enough for CLI + agents
   - whether methods exist in the interface but are missing meaningful support in practice
4. Auth/session robustness:
   - session restore
   - relogin flow
   - 2FA/challenge handling
   - proxy/locale/device handling
5. Media handling:
   - local path vs URL behavior
   - Graph API URL requirements
   - temp file lifecycle
6. Test blind spots:
   - places where mocks hide real failures
   - missing integration points
   - missing negative-path coverage
7. Product/architecture gaps:
   - placeholder flows exposed as real commands
   - undocumented constraints
   - anything that will confuse agent callers or human users

Output format:
1. Findings
   - Ordered by severity.
   - For each finding, include:
     - short title
     - why it matters
     - exact file references
     - whether it is a correctness bug, production-risk gap, spec mismatch, or testing gap
2. Missing or weak assumptions
   - What the code seems to assume but does not prove
3. Missing tests
   - High-value tests that should exist but do not
4. Architecture/product gaps
   - Missing pieces that block the stated product vision
5. Short conclusion
   - Is this mainly sound but incomplete, or does it have deeper logic issues?

Important review stance:
- Do not just restate the code.
- Infer what is missing.
- Call out where the repo is internally consistent but still likely wrong in the real world.
- If something is clearly a planned placeholder, separate that from actual bugs, but still flag any place where the CLI/docs present placeholders as if they are implemented.

Extra context from local inspection:
- `pytest -q` currently passes: 135 passed.
- That should increase scrutiny on mocked behavior and overfit tests, not reduce it.

Start with the highest-signal findings first.
