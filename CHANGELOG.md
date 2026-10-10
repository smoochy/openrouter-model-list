# Changelog

## 2026-10-10

### Changed

- `.github/workflows/update-anthropic-models.yml` runs daily at 03:15 UTC instead of Tuesdays only. A weekly cron makes the worst-case lag between a model shipping and appearing in `anthropic-models.json` almost seven days, and that is not a theoretical bound: `claude-haiku-5-5` shipped the day after the 2026-10-06 run and was still missing on 2026-10-10 with the next run three days out. Consumers that pick a model from this file therefore cannot see a new model for up to a week. The 03:15 offset against `update-models.yml` at 03:00 stays, as does the shared `update-model-lists` concurrency group, so the two jobs still never overlap. Runner minutes are free on a public repository, and `peter-evans/create-pull-request` only opens a pull request when the file actually changed, so a daily schedule adds no pull-request noise on days when Anthropic ships nothing
- `README.md` states the Anthropic list's real cadence in all three places that name it: the file table, the Anthropic Model List section, and the workflow sentence. The last one also said 03:00 UTC, which was wrong before this change too - the cron has been at 03:15 since the offset against `update-models.yml` was introduced, so a reader comparing the two schedules would have concluded they collide

### Added

- `scripts/generate_anthropic_models.py`: replaces the inline `python3 -c` block in `.github/workflows/update-anthropic-models.yml`. Fetches `/v1/models` with pagination (the old inline script read only the first page and would silently drop entries once the catalogue passed 20 models), scrapes the markdown pricing table at `https://platform.claude.com/docs/en/about-claude/pricing`, and joins each row onto an API model id by slugifying the page's model name, falling back to `anthropic-price-aliases.yaml` for dated ids and the Haiku 5.5 split-row case that slugify can't reach
- Each entry in `anthropic-models.json` now carries a `pricing` object (`input`, `cache_write_5m`, `cache_write_1h`, `cache_read`, `output`, all `$/MTok`) alongside the existing Anthropic API fields. The file stays a bare array - the wrapper shape (`{generated_at, schema_version, models}`) used by `models-*.json` was deliberately not adopted here, since it would break the one known consumer (`smoochy/yt-transcript-distiller`, branch `claude/yt-distiller-v2`) for no requirement in this ticket; left for a future ticket if that branch's code is updated to unwrap first
- `anthropic-price-aliases.yaml`: the alias fallback table for the join above
- Fails closed: the run exits non-zero (no file written, no PR opened, last-known-good `anthropic-models.json` stays committed) on a model with no price after the join, the pricing table header not found or its column count changed, or a price that is zero or doesn't parse
- Tests: `tests/test_generate_anthropic_models.py` covers slugify, pricing-table parsing (happy path, missing header, schema change, zero/unparseable price), the join (direct match, alias match, split-row alias, unmapped model), pagination, and the end-to-end `generate()` write/fail-closed paths
- `README.md`'s Anthropic Model List section documents the new script, the pricing fields, and the alias file

## 2026-09-07

### Changed

- `thresholds-openwiki.yaml` allowlists `thinkingmachines/inkling:free`, `poolside/laguna-s-2.1:free`, `cohere/north-mini-code:free` and `nvidia/nemotron-3.5-lightning:free`. `min_param_b` reads the parameter count out of the model id, and most current free models carry no size token in their slug, so the 70B floor dropped 15 of 21 free models untested and left exactly two Nvidia Nemotron models - a single provider, and the same one whose non-retryable 404s kill the OpenWiki documentation runs. All four allowlisted models clear the context, output and tool-calling thresholds on their catalog metadata; only the unparseable size kept them out. The candidate pool goes from 2 models on 1 provider to 6 on 4. Config only: `filters.py` and its `min_param_b` hard-floor semantics are unchanged, so the `mengram` and `yt-summarizer` profiles keep their current behaviour

## 2026-08-23

### Changed

- `.github/workflows/update-models.yml` and `.github/workflows/update-anthropic-models.yml` no longer mint a GitHub App token to push straight to `main`; both dropped the `actions/create-github-app-token` step and the `AUTOMATION_APP_ID`/`AUTOMATION_APP_KEY` secrets, and the checkout step is back on the default `GITHUB_TOKEN`. The hand-rolled `git config` / `git commit` / `git pull --rebase` / `git push` block is replaced with `peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8`, opening `automation/update-models` and `automation/update-anthropic-models` respectively, and each job gained `pull-requests: write` next to its existing `contents: write`. A step right after tries to merge the new pull request immediately under `GITHUB_TOKEN`; this repository has `required_approving_review_count: 0` and no required status checks, so the immediate self-merge is an audit trail rather than a review bypass, and a refused merge is tolerated on purpose - it leaves the pull request open for `fleet-timed-pr-automerge` in `homelab-private` to merge as the App instead, which is the designed floor, not an error.

## 2026-08-05

### Changed

- `.github/workflows/openwiki-update.yaml` keeps every `sanity_ok` model from `models-openwiki.json` as a fallback candidate rather than taking only the top-scoring one, and the run step walks the list in score order until one succeeds. `sanity_ok` records that a smoke call returned something, which is a weaker claim than surviving a full documentation run: a scheduled mengram run died on `Received empty response from chat model call.` from the top free model while the second candidate was untouched. The list stays free-only; no paid model enters the rotation

## 2026-07-19

### Added

- `openwiki` profile (`thresholds-openwiki.yaml`, output `models-openwiki.json`): 70B floor, 128k context, 16k output, tool-calling required — for OpenWiki repo-documentation runs
- `require_tools` threshold flag + `supports_tools()` filter (checks `tools`/`tool_choice` in `supported_parameters`); soft-allowlisted models missing tool support are excluded with a warning
- `models-openwiki.json` generation step in `update-models.yml`
- Tests: `supports_tools`, `require_tools` filtering, allowlist tool-warning

## 2026-06-20

### Added

- `--profile` CLI argument to `scripts/generate_models.py` with `mengram` (default) and `yt-summarizer` profiles
- `resolve_profile(name)` function mapping profile names to thresholds/output paths
- `thresholds-yt-summarizer.yaml` for YouTube transcript summarization use-case (14B floor, 32k context, no structured output required)
- Three new tests for `resolve_profile` in `tests/test_generate_models.py`
- Renamed `thresholds.yaml` → `thresholds-mengram.yaml` for naming parity with `thresholds-yt-summarizer.yaml`; updated all references in `scripts/thresholds.py`, `scripts/generate_models.py`, `tests/test_generate_models.py`, and `README.md`
- Added `.github/workflows/update-anthropic-models.yml`: weekly (Tuesday 03:00 UTC) workflow that fetches `https://api.anthropic.com/v1/models` and commits `anthropic-models.json` (`[{id, name}]`, type==model only, sorted by id)
- Updated `README.md`: added `anthropic-models.json` to Available Model Lists table; added "Anthropic Model List" section

## 2026-06-15

### Initial release
