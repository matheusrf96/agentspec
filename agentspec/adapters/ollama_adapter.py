from __future__ import annotations

import os

from agentspec.adapters.openai_compatible_adapter import (
    AdapterConfig,
    OpenAICompatibleAdapter,
)

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_DEFAULT_MODEL = "llama3"


class OllamaAdapter(OpenAICompatibleAdapter):
    def __init__(self, config: AdapterConfig | None = None):
        resolved = config or AdapterConfig(
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
            base_url=os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL),
            model=os.getenv("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL),
        )
        super().__init__(resolved)
