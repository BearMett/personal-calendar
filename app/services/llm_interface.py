from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class LLMInterface(ABC):
    """Abstract interface for Language Model services."""

    @abstractmethod
    async def generate_completion(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        """
        Generate a text completion based on the prompt.

        Args:
            prompt: The user prompt to send to the LLM
            system_prompt: Optional system instructions to guide the LLM
            **kwargs: Additional parameters specific to the LLM service

        Returns:
            The generated text response
        """
        pass

    @abstractmethod
    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a structured output (JSON) that matches the provided schema.

        Args:
            prompt: The user prompt to send to the LLM
            output_schema: The schema that defines the structure of the output
            system_prompt: Optional system instructions to guide the LLM

        Returns:
            Structured data according to the schema
        """
        pass

    @abstractmethod
    async def extract_entities(
        self, text: str, entity_types: List[str]
    ) -> Dict[str, Any]:
        """
        Extract specific entities from the text.

        Args:
            text: The text to analyze
            entity_types: Types of entities to extract (e.g., 'date', 'time', 'location')

        Returns:
            Dictionary of extracted entities
        """
        pass
