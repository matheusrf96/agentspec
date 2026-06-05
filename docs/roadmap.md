# Roadmap

## Tier 1 — Core stability (done)

- [x] CLI tests (CliRunner for run, validate, init)
- [x] Reporter tests (terminal + JSON output)
- [x] OpenAI adapter tests (response parsing, errors, config)
- [x] Documentation (architecture, assertion types, MCP servers, CLI reference, contributing guide, FAQ)

## Tier 2 — Feature roadmap (from README) ✅

- [x] **LangChain adapter** — Wrap any LangChain agent as an `AgentAdapter` so specs can run against LangChain-based agents
- [x] **Directory-based specs** — `agentspec run ./specs/` discovers and runs all `.yaml` files in a directory, returning a consolidated report
- [x] **HTML report output** — `agentspec run --output html` generates a self-contained HTML page with pass/fail visualization and drill-down
- [x] **Test fixture system** — Specs gain a `fixtures` section for pre-seeded conversation history, mock tool definitions, and canned responses
- [x] **GitHub Actions integration** — Reusable action that runs eval specs and posts result tables on PRs

## Tier 3 — More adapters ✅

- [x] **Ollama adapter** — Zero-cost local evaluation (OpenAI-compatible, just needs dedicated defaults)
- [x] **Anthropic adapter** — Native Claude support via `anthropic` SDK with proper message format conversion

## Tier 4 — Power features ✅

- [x] **Concurrent evaluation** — Run tests in parallel via `asyncio.gather()` with configurable concurrency limits
- [x] **Caching layer** — `CachingAdapter` wraps any adapter to cache LLM responses keyed by `(prompt, system, model)` for deterministic re-runs
- [x] **New assertion types**
  - `tool_call_count` — Assert exact/min/max number of tool calls
  - `output_not_contains` — Assert absence of content (safety checks)
  - `cost_under` — Assert cost under threshold (token pricing config)
  - `output_length_between` — Min/max output length in chars/tokens
- [x] **Spec composition** — `!include` YAML tag to import tests from other files

## Tier 5 — Quality of life ✅

- [x] **CLI improvements**
  - `agentspec list [path]` — List specs in a directory
  - `agentspec compare <id1> <id2>` — Compare two runs
  - `agentspec results prune` — Keep only the N most recent runs
  - `agentspec results export` — Export runs as CSV
  - `agentspec results history` — Show recent run list
  - `agentspec results get <id>` — Show full run details
  - `agentspec completion <shell>` — Print tab completion script
  - Progress bar on `run` (use `--no-progress` to disable)
- [x] **VSCode JSON Schema** — `spec-schema.json` generated from Pydantic models; enables autocomplete and validation in editors
- [x] **Results store backends** — `JsonFileBackend` (default) and `SqliteBackend` via `results_backend.py`
