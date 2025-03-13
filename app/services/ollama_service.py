import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from config import settings
from .llm_interface import LLMInterface

logger = logging.getLogger("ollama_service")


class OllamaService(LLMInterface):
    """Implementation of LLMInterface using Ollama API."""

    def __init__(self):
        """Initialize the Ollama service with configuration from settings."""
        self.base_url = settings.OLLAMA_BASE_URL
        self.api_endpoint = settings.OLLAMA_API_ENDPOINT
        self.model = settings.OLLAMA_MODEL
        self.api_url = f"{self.base_url}{self.api_endpoint}"
        self.timeout = settings.OLLAMA_TIMEOUT
        self.temperature = settings.OLLAMA_TEMPERATURE
        self.max_tokens = settings.OLLAMA_MAX_TOKENS

    async def generate_completion(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        """Generate a text completion using Ollama."""
        try:
            messages = []

            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add user prompt
            messages.append({"role": "user", "content": prompt})

            # Prepare the payload
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "stream": False,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, json=payload, timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"Ollama API error: {response.status}, {error_text}"
                        )
                        return f"Error: Failed to get response from LLM service (status {response.status})"

                    result = await response.json()
                    if not result or "choices" not in result or not result["choices"]:
                        logger.error(f"Invalid response from Ollama API: {result}")
                        return "Error: Invalid response from LLM service"

                    return result["choices"][0]["message"]["content"]

        except asyncio.TimeoutError:
            logger.error(f"Ollama API timeout after {self.timeout} seconds")
            return "Error: LLM service timeout"
        except Exception as e:
            logger.error(f"Ollama API error: {str(e)}")
            return f"Error: {str(e)}"

    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a structured output (JSON) using Ollama."""
        try:
            # Create a system prompt that instructs the model to return JSON
            schema_str = json.dumps(output_schema, indent=2)
            structured_system_prompt = (
                (f"{system_prompt}\n\n" if system_prompt else "")
                + f"Return your response as a JSON object with the following schema:\n{schema_str}\n"
            )

            # Get the completion
            response = await self.generate_completion(
                prompt=prompt,
                system_prompt=structured_system_prompt,
                temperature=0.2,  # Lower temperature for more deterministic output
            )

            # Extract JSON from the response
            try:
                # Try to find JSON in the response using common patterns
                json_start = response.find("{")
                json_end = response.rfind("}") + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
                else:
                    # If no JSON found, try to parse the whole response
                    return json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from LLM response: {e}")
                logger.error(f"Response was: {response}")
                # Return a minimal valid response
                return {
                    "error": "Failed to parse structured output",
                    "raw_response": response,
                }

        except Exception as e:
            logger.error(f"Error generating structured output: {str(e)}")
            return {"error": str(e)}

    async def extract_entities(
        self, text: str, entity_types: List[str]
    ) -> Dict[str, Any]:
        """Extract specific entities from text."""
        entity_types_str = ", ".join(entity_types)
        prompt = f"Extract the following entities from this text: {entity_types_str}.\nText: {text}"

        system_prompt = (
            "You are an entity extraction assistant. Extract the requested entities from the text and "
            "return them in a JSON format. If an entity is not found, set its value to null."
        )

        # Create a schema for the extracted entities
        schema = {entity_type: None for entity_type in entity_types}

        return await self.generate_structured_output(prompt, schema, system_prompt)
