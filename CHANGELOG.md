# Changelog

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
