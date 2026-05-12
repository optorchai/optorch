"""provider extractor registry"""
from typing import Type, cast
from optorch.llm.responses.helpers.extractor_protocol import StreamExtractor
from optorch.llm.responses.helpers.openai_extractor import OpenAIExtractor
from optorch.llm.responses.helpers.ollama_extractor import OllamaExtractor

def get_extractor(provider: str) -> Type[StreamExtractor]:
    """get extractor class for provider"""
    if provider == "ollama":
        return cast(Type[StreamExtractor], OllamaExtractor)
    return cast(Type[StreamExtractor], OpenAIExtractor)
