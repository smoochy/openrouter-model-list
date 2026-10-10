import json

import httpx
import pytest
import respx

from generate_anthropic_models import (
    MODELS_API_URL,
    PricingError,
    fetch_models,
    generate,
    join_prices,
    parse_pricing_table,
    slugify,
)

HEADER = (
    "| Model | Base input tokens | 5m cache writes | 1h cache writes "
    "| Cache hits and refreshes | Output tokens |"
)
SEP = "| --- | --- | --- | --- | --- | --- |"


def table_md(rows: list[str]) -> str:
    return "\n".join([HEADER, SEP, *rows])


def test_slugify_matches_dotted_version():
    assert slugify("Claude Opus 5.5") == "claude-opus-5-5"


def test_slugify_strips_punctuation_and_links():
    assert slugify("Claude Haiku 5.5 (for prompts up to 100,000 tokens)") == (
        "claude-haiku-5-5-for-prompts-up-to-100000-tokens"
    )


def test_parse_pricing_table_happy_path():
    md = table_md([
        "| Claude Opus 5.5 | $4 / MTok | $5 / MTok | $8 / MTok | $0.20 / MTok<sup>2</sup> | $20 / MTok |",
    ])
    table = parse_pricing_table(md)
    assert table["Claude Opus 5.5"] == {
        "input": 4.0,
        "cache_write_5m": 5.0,
        "cache_write_1h": 8.0,
        "cache_read": 0.20,
        "output": 20.0,
    }


def test_parse_pricing_table_tolerates_header_column_padding():
    padded_header = "| Model                | Base input tokens | 5m cache writes | 1h cache writes | Cache hits and refreshes | Output tokens |"
    md = "\n".join([
        padded_header,
        SEP,
        "| Claude Opus 5.5 | $4 / MTok | $5 / MTok | $8 / MTok | $0.20 / MTok | $20 / MTok |",
    ])
    assert "Claude Opus 5.5" in parse_pricing_table(md)


def test_parse_pricing_table_missing_header_fails_closed():
    with pytest.raises(PricingError, match="header not found"):
        parse_pricing_table("no table here at all")


def test_parse_pricing_table_schema_change_fails_closed():
    md = table_md(["| Claude Opus 5.5 | $4 / MTok | $5 / MTok |"])  # wrong column count
    with pytest.raises(PricingError, match="columns"):
        parse_pricing_table(md)


def test_parse_pricing_table_zero_price_fails_closed():
    md = table_md([
        "| Claude Opus 5.5 | $0 / MTok | $5 / MTok | $8 / MTok | $0.20 / MTok | $20 / MTok |",
    ])
    with pytest.raises(PricingError, match="zero/invalid price"):
        parse_pricing_table(md)


def test_parse_pricing_table_unparseable_price_fails_closed():
    md = table_md([
        "| Claude Opus 5.5 | contact sales | $5 / MTok | $8 / MTok | $0.20 / MTok | $20 / MTok |",
    ])
    with pytest.raises(PricingError, match="unparseable price"):
        parse_pricing_table(md)


def test_join_prices_direct_slug_match():
    pricing_table = {"Claude Opus 5.5": {"input": 4.0}}
    priced = join_prices(["claude-opus-5-5"], pricing_table, aliases={})
    assert priced == {"claude-opus-5-5": {"input": 4.0}}


def test_join_prices_alias_covers_dated_id():
    pricing_table = {"Claude Haiku 4.5": {"input": 1.0}}
    aliases = {"claude-haiku-4-5": ["claude-haiku-4-5-20251001"]}
    priced = join_prices(["claude-haiku-4-5-20251001"], pricing_table, aliases)
    assert priced == {"claude-haiku-4-5-20251001": {"input": 1.0}}


def test_join_prices_alias_covers_split_row():
    pricing_table = {
        "Claude Haiku 5.5 (for prompts up to 100,000 tokens)": {"input": 0.10},
        "Claude Haiku 5.5 (for prompts over 100,000 tokens)": {"input": 0.50},
    }
    aliases = {
        "claude-haiku-5-5-for-prompts-up-to-100000-tokens": ["claude-haiku-5-5"],
    }
    priced = join_prices(["claude-haiku-5-5"], pricing_table, aliases)
    assert priced == {"claude-haiku-5-5": {"input": 0.10}}


def test_join_prices_unmapped_model_fails_closed():
    pricing_table = {"Claude Opus 5.5": {"input": 4.0}}
    with pytest.raises(PricingError, match="claude-fable-5"):
        join_prices(["claude-opus-5-5", "claude-fable-5"], pricing_table, aliases={})


def test_generate_writes_output_and_history(tmp_path):
    output_path = tmp_path / "anthropic-models.json"
    history_path = tmp_path / "history" / "anthropic-models.jsonl"

    def fetch_models_fn(api_key):
        return [{"type": "model", "id": "claude-opus-5-5", "display_name": "Claude Opus 5.5"}]

    def fetch_pricing_fn():
        return table_md([
            "| Claude Opus 5.5 | $4 / MTok | $5 / MTok | $8 / MTok | $0.20 / MTok | $20 / MTok |",
        ])

    result = generate(
        api_key="test-key",
        fetch_models_fn=fetch_models_fn,
        fetch_pricing_fn=fetch_pricing_fn,
        aliases={},
        now="2026-10-10T00:00:00Z",
        output_path=output_path,
        history_path=history_path,
    )

    assert result[0]["pricing"]["input"] == 4.0

    written = json.loads(output_path.read_text())
    assert written[0]["id"] == "claude-opus-5-5"
    assert written[0]["pricing"]["output"] == 20.0

    history_lines = history_path.read_text().strip().splitlines()
    assert len(history_lines) == 1
    assert json.loads(history_lines[0])["timestamp"] == "2026-10-10T00:00:00Z"


@respx.mock
def test_fetch_models_filters_to_type_model():
    respx.get(MODELS_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"type": "model", "id": "claude-opus-5-5"},
                    {"type": "deprecated", "id": "claude-old-1"},
                ],
                "has_more": False,
            },
        )
    )

    result = fetch_models("test-key")

    assert [m["id"] for m in result] == ["claude-opus-5-5"]


@respx.mock
def test_fetch_models_follows_pagination():
    route = respx.get(MODELS_API_URL)
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": [{"type": "model", "id": "claude-a"}],
                "has_more": True,
                "last_id": "claude-a",
            },
        ),
        httpx.Response(
            200,
            json={"data": [{"type": "model", "id": "claude-b"}], "has_more": False},
        ),
    ]

    result = fetch_models("test-key")

    assert sorted(m["id"] for m in result) == ["claude-a", "claude-b"]
    assert route.calls.last.request.url.params["after_id"] == "claude-a"


def test_generate_fails_closed_without_writing_on_missing_price(tmp_path):
    output_path = tmp_path / "anthropic-models.json"
    history_path = tmp_path / "history" / "anthropic-models.jsonl"

    def fetch_models_fn(api_key):
        return [{"type": "model", "id": "claude-unpriced-9", "display_name": "Claude Unpriced 9"}]

    def fetch_pricing_fn():
        return table_md([
            "| Claude Opus 5.5 | $4 / MTok | $5 / MTok | $8 / MTok | $0.20 / MTok | $20 / MTok |",
        ])

    with pytest.raises(PricingError):
        generate(
            api_key="test-key",
            fetch_models_fn=fetch_models_fn,
            fetch_pricing_fn=fetch_pricing_fn,
            aliases={},
            now="2026-10-10T00:00:00Z",
            output_path=output_path,
            history_path=history_path,
        )

    assert not output_path.exists()
    assert not history_path.exists()
