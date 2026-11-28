# Files

- [Anthropic API Integration](anthropic.md) - Details how Claude model metadata is fetched from the Anthropic API, pricing is scraped from the public pricing page, prices are joined via slugify and alias table, long-context tiers are attached, and the script fails closed on any pricing problem.
- [OpenRouter API Integration](openrouter.md) - Describes how the system fetches the OpenRouter model catalog, endpoint statistics, and performs 1-token sanity probes via the OpenAI-compatible API, including error handling and missing free endpoint behavior.
