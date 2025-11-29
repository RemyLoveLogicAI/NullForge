"""
Advanced LLM wrapper for AOL-CLI Fire Edition.

Supports multiple providers, streaming, and tool calling.
"""

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field, SecretStr

from aol_fire.core import FireConfig


class FireChatModel(BaseChatModel):
    """
    Unified chat model for AOL-CLI Fire Edition.
    
    Works with any OpenAI-compatible API including:
    - OpenAI
    - Venice AI
    - Ollama
    - Groq
    - Together AI
    - OpenRouter
    - Any custom endpoint
    """
    
    api_key: Optional[SecretStr] = None
    api_base: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    max_tokens: Optional[int] = 4096
    timeout: int = 120
    streaming: bool = False
    
    # Additional headers (useful for OpenRouter, etc.)
    extra_headers: Dict[str, str] = Field(default_factory=dict)
    
    # System prompt injection
    system_prompt: Optional[str] = None
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def _llm_type(self) -> str:
        return "fire-chat-model"
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "api_base": self.api_base,
            "temperature": self.temperature,
        }
    
    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        
        if self.api_key:
            key = self.api_key.get_secret_value() if isinstance(self.api_key, SecretStr) else self.api_key
            headers["Authorization"] = f"Bearer {key}"
        
        headers.update(self.extra_headers)
        return headers
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Convert LangChain messages to API format."""
        converted = []
        
        # Inject system prompt if needed
        if self.system_prompt:
            has_system = any(isinstance(m, SystemMessage) for m in messages)
            if not has_system:
                converted.append({"role": "system", "content": self.system_prompt})
        
        for msg in messages:
            if isinstance(msg, SystemMessage):
                converted.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                msg_dict = {"role": "assistant", "content": msg.content or ""}
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("args", {}))
                            }
                        }
                        for i, tc in enumerate(msg.tool_calls)
                    ]
                converted.append(msg_dict)
            elif isinstance(msg, ToolMessage):
                converted.append({
                    "role": "tool",
                    "content": str(msg.content),
                    "tool_call_id": msg.tool_call_id
                })
            else:
                converted.append({"role": "user", "content": str(msg.content)})
        
        return converted
    
    def _build_payload(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Build the request payload."""
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "temperature": self.temperature,
        }
        
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        
        if stop:
            payload["stop"] = stop
        
        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]
        
        if "tool_choice" in kwargs:
            payload["tool_choice"] = kwargs["tool_choice"]
        
        if self.streaming:
            payload["stream"] = True
        
        return payload
    
    def _parse_response(self, result: Dict[str, Any]) -> ChatResult:
        """Parse API response into ChatResult."""
        choice = result["choices"][0]
        message = choice["message"]
        
        ai_kwargs = {"content": message.get("content", "") or ""}
        
        if "tool_calls" in message and message["tool_calls"]:
            ai_kwargs["tool_calls"] = [
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": json.loads(tc["function"]["arguments"])
                }
                for tc in message["tool_calls"]
            ]
        
        ai_message = AIMessage(**ai_kwargs)
        
        generation = ChatGeneration(
            message=ai_message,
            generation_info={
                "finish_reason": choice.get("finish_reason"),
                "model": result.get("model"),
                "usage": result.get("usage", {}),
            }
        )
        
        return ChatResult(
            generations=[generation],
            llm_output={
                "model": result.get("model"),
                "usage": result.get("usage", {}),
            }
        )
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from the model."""
        payload = self._build_payload(messages, stop, **kwargs)
        endpoint = f"{self.api_base.rstrip('/')}/chat/completions"
        
        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = client.post(
                        endpoint,
                        headers=self._get_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    return self._parse_response(response.json())
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < self.max_retries - 1:
                        import time
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    raise ValueError(f"API error: {e.response.status_code} - {e.response.text}")
                except httpx.RequestError as e:
                    if attempt < self.max_retries - 1:
                        import time
                        time.sleep(self.retry_delay)
                        continue
                    raise ValueError(f"Request failed: {str(e)}")
        
        raise ValueError("Max retries exceeded")
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate response."""
        payload = self._build_payload(messages, stop, **kwargs)
        endpoint = f"{self.api_base.rstrip('/')}/chat/completions"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        endpoint,
                        headers=self._get_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    return self._parse_response(response.json())
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < self.max_retries - 1:
                        import asyncio
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    raise ValueError(f"API error: {e.response.status_code} - {e.response.text}")
                except httpx.RequestError as e:
                    if attempt < self.max_retries - 1:
                        import asyncio
                        await asyncio.sleep(self.retry_delay)
                        continue
                    raise ValueError(f"Request failed: {str(e)}")
        
        raise ValueError("Max retries exceeded")
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream response from the model."""
        payload = self._build_payload(messages, stop, **kwargs)
        payload["stream"] = True
        endpoint = f"{self.api_base.rstrip('/')}/chat/completions"
        
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream(
                "POST",
                endpoint,
                headers=self._get_headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk_data = json.loads(data)
                            delta = chunk_data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                chunk = ChatGenerationChunk(
                                    message=AIMessageChunk(content=content)
                                )
                                yield chunk
                                
                                if run_manager:
                                    run_manager.on_llm_new_token(content)
                        except json.JSONDecodeError:
                            continue


def create_chat_model(
    config: FireConfig,
    model_type: str = "orchestrator"
) -> FireChatModel:
    """
    Create a chat model from configuration.
    
    Args:
        config: Fire configuration
        model_type: One of "orchestrator", "planner", "coder", "fast"
    
    Returns:
        Configured FireChatModel
    """
    model_map = {
        "orchestrator": config.orchestrator_model,
        "planner": config.planner_model,
        "coder": config.coder_model,
        "fast": config.fast_model,
    }
    
    model_name = model_map.get(model_type, config.orchestrator_model)
    
    # Build extra headers for specific providers
    extra_headers = {}
    if config.llm_provider == "openrouter":
        extra_headers["HTTP-Referer"] = "https://github.com/aol-cli-fire"
        extra_headers["X-Title"] = "AOL-CLI Fire"
    
    return FireChatModel(
        api_key=SecretStr(config.get_api_key()) if config.get_api_key() else None,
        api_base=config.get_api_base(),
        model_name=model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        timeout=config.api_timeout,
        extra_headers=extra_headers,
    )


def create_tool_calling_model(
    config: FireConfig,
    tools: List[Any],
    model_type: str = "coder"
) -> FireChatModel:
    """Create a model configured for tool calling."""
    model = create_chat_model(config, model_type)
    
    # Convert tools to OpenAI format
    tool_defs = []
    for tool in tools:
        if hasattr(tool, 'name') and hasattr(tool, 'description'):
            schema = tool.args_schema.model_json_schema() if hasattr(tool, 'args_schema') else {}
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema,
                }
            })
    
    return model, tool_defs
