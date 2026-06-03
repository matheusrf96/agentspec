# Add Evaluation Spec

Guided workflow for creating a new evaluation spec file.

## Steps

1. **Choose template** — Ask user which template fits: `tool-calling`, `rag`, `chat`, `code-gen`, `structured-output`. Use the `spec-templates` MCP server.
2. **Customize** — Modify the spec: set `name`, `model`, `system_prompt`, adjust test cases.
3. **Validate** — Run `agentspec validate <path>` to check the spec.
4. **Test with mock** — Use `mock-agent` MCP to run the spec without an API key.
5. **Save** — Commit the file or save to `examples/` directory.

## Template Locations

| Template | Description |
|----------|-------------|
| `tool-calling` | Basic tool-use evaluation |
| `rag` | RAG quality checks |
| `chat` | General chat quality |
| `code-gen` | Code generation correctness |
| `structured-output` | JSON schema compliance |
