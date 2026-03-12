Recommended files to upload to ChatGPT 5.4 Pro for a strong review.

Use Tier 1 first. Add Tier 2 if you want deeper coverage. Tier 3 is only if you want near-full command-surface review.

Tier 1: smallest strong bundle

- `README.md`
- `SKILL.md`
- `pyproject.toml`
- `src/clinstagram/cli.py`
- `src/clinstagram/config.py`
- `src/clinstagram/models.py`
- `src/clinstagram/media.py`
- `src/clinstagram/auth/keychain.py`
- `src/clinstagram/auth/private_login.py`
- `src/clinstagram/commands/_dispatch.py`
- `src/clinstagram/commands/auth.py`
- `src/clinstagram/commands/dm.py`
- `src/clinstagram/commands/post.py`
- `src/clinstagram/commands/story.py`
- `src/clinstagram/commands/comments.py`
- `src/clinstagram/commands/followers.py`
- `src/clinstagram/commands/config_cmd.py`
- `src/clinstagram/backends/base.py`
- `src/clinstagram/backends/capabilities.py`
- `src/clinstagram/backends/router.py`
- `src/clinstagram/backends/graph.py`
- `src/clinstagram/backends/private.py`
- `tests/test_dispatch.py`
- `tests/test_router.py`
- `tests/test_capabilities.py`
- `tests/test_private_login.py`
- `tests/test_backends_base.py`
- `tests/test_media.py`
- `tests/test_e2e.py`
- `tests/test_cli.py`

Why Tier 1 matters:
- It gives the model the claimed product behavior, the CLI entrypoint, the real routing spine, auth/session logic, both backends, and the highest-signal tests.
- This is enough for ChatGPT to evaluate logic, gaps, and where the tests may be masking issues.

Tier 2: add these if you want a deeper review

- `src/clinstagram/commands/user.py`
- `src/clinstagram/commands/analytics.py`
- `src/clinstagram/commands/like.py`
- `src/clinstagram/commands/hashtag.py`
- `tests/test_models.py`
- `tests/test_config.py`
- `tests/test_config_persistence.py`
- `tests/test_keychain.py`

Why Tier 2 matters:
- It fills out the rest of the public CLI surface and config/secret persistence behavior.

Tier 3: upload the rest of `src/clinstagram/commands/` and `tests/` only if browser limits are not an issue

- Anything under `src/clinstagram/commands/` not already listed
- Anything under `tests/` not already listed

Suggested upload order if you do it manually

1. `README.md`
2. `pyproject.toml`
3. `src/clinstagram/cli.py`
4. `src/clinstagram/commands/_dispatch.py`
5. `src/clinstagram/backends/capabilities.py`
6. `src/clinstagram/backends/router.py`
7. `src/clinstagram/backends/graph.py`
8. `src/clinstagram/backends/private.py`
9. `src/clinstagram/auth/private_login.py`
10. `src/clinstagram/media.py`
11. `src/clinstagram/auth/keychain.py`
12. command files
13. tests

If you want the most compressed version possible, upload only these 12 files

- `README.md`
- `src/clinstagram/cli.py`
- `src/clinstagram/commands/_dispatch.py`
- `src/clinstagram/commands/auth.py`
- `src/clinstagram/commands/dm.py`
- `src/clinstagram/commands/story.py`
- `src/clinstagram/backends/capabilities.py`
- `src/clinstagram/backends/router.py`
- `src/clinstagram/backends/graph.py`
- `src/clinstagram/backends/private.py`
- `src/clinstagram/auth/private_login.py`
- `tests/test_dispatch.py`

That compressed set is enough for a first-pass logic review, but it is weaker on config, storage, and test-gap analysis.
