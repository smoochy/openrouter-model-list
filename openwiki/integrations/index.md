# Files

- [Anthropic API Integration](anthropic.md) - Details how the system fetches Claude model metadata from the Anthropic API, scrapes pricing from the public pricing page, joins prices via slugify and alias table, handles long-context tiers, and fails closed on any pricing problem.
- [OpenRouter API Integration](openrouter.md) - Describes how the system fetches the OpenRouter model catalog, endpoint statistics, and performs 1-token sanity probes via the OpenAI-compatible API, including error handling and missing free endpoint behavior.
