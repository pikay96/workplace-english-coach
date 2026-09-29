"""All remote model traffic goes through the pinned LiveKit Inference SDK."""

import asyncio
import copy
import time
from collections.abc import Callable

from livekit.agents import APIConnectOptions, inference, llm
from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.observability import metric


class ProviderUnavailable(Exception):
    pass


# PCM stays in memory for one reply and is discarded on completion/cancellation.
MAX_SPEECH_BYTES = 24000 * 2 * 90
SPEECH_SYNTHESIS_TIMEOUT = 60


def response_format(schema: type[BaseModel]) -> dict:
    """Provider schema; application validation retains every field bound and invariant.

    LiveKit 1.8.2's response_format dict overload raises TypeError. Its public
    extra_kwargs supports the OpenAI envelope used by LiveKit Inference.
    """
    document = copy.deepcopy(schema.model_json_schema())

    def portable(node):
        if isinstance(node, list):
            return [portable(item) for item in node]
        if not isinstance(node, dict):
            return node
        result = {
            key: portable(value)
            for key, value in node.items()
            if key
            not in {
                "title",
                "default",
                "minItems",
                "maxItems",
                "minLength",
                "maxLength",
                "minimum",
                "maximum",
                "discriminator",
            }
        }
        if "const" in result:
            result["enum"] = [result.pop("const")]
        if "oneOf" in result:
            result["anyOf"] = result.pop("oneOf")
        if result.get("type") == "object":
            result["required"] = list(result.get("properties", {}))
        return result

    return {
        "type": "json_schema",
        "json_schema": {"name": schema.__name__, "schema": portable(document), "strict": True},
    }


class Inference:
    def __init__(self, config: Settings):
        self.config = config

    def auth(self):
        return {
            "api_key": self.config.livekit_api_key.get_secret_value(),
            "api_secret": self.config.livekit_api_secret.get_secret_value(),
        }

    def stt(self):
        return inference.STT(
            model=self.config.transcription_model,
            language=self.config.transcription_language,
            **self.auth(),
            extra_kwargs={
                "filler_words": True,
                "smart_format": False,
                "numerals": False,
                "punctuate": True,
            },
        )

    def tts(self):
        # LiveKit forwards Cartesia's speaking-rate multiplier at synthesis time.
        # https://docs.livekit.io/agents/models/tts/cartesia/#model-parameters
        options = (
            {"speed": self.config.tts_speed}
            if self.config.tts_model.startswith("cartesia/")
            else {}
        )
        return inference.TTS(
            model=self.config.tts_model,
            voice=self.config.tts_voice,
            sample_rate=24000,
            extra_kwargs=options,
            **self.auth(),
        )

    async def speech(self, text: str):
        """Prepare one complete reply so provider delivery gaps never reach playout.

        Bound first provider audio to eight seconds, total synthesis to sixty,
        and mono PCM16 storage to ninety seconds. Never play a truncated reply.
        """
        client = self.tts()
        frames = []
        size = 0
        try:
            async with (
                asyncio.timeout(SPEECH_SYNTHESIS_TIMEOUT),
                client.stream(conn_options=APIConnectOptions(max_retry=0, timeout=8)) as stream,
            ):
                stream.push_text(text)
                stream.end_input()
                async with asyncio.timeout(8):
                    first = await anext(stream)
                frames.append(first.frame)
                size = first.frame.data.nbytes
                if size > MAX_SPEECH_BYTES:
                    raise ProviderUnavailable("speech_too_large")
                async for chunk in stream:
                    size += chunk.frame.data.nbytes
                    if size > MAX_SPEECH_BYTES:
                        raise ProviderUnavailable("speech_too_large")
                    frames.append(chunk.frame)
                if not size:
                    raise ProviderUnavailable("empty_speech")
        finally:
            await client.aclose()
        for frame in frames:
            yield frame

    async def structured[T: BaseModel](
        self,
        schema: type[T],
        system: str,
        data: str,
        *,
        model: str,
        timeout: float = 8,  # noqa: ASYNC109
        validate: Callable[[T], object] | None = None,
    ) -> T:
        started = time.monotonic()
        client = inference.LLM(model=model, **self.auth())
        ctx = llm.ChatContext()
        ctx.add_message(role="system", content=system)
        ctx.add_message(role="user", content=data)
        try:
            async with asyncio.timeout(timeout):
                for attempt in range(2):
                    pieces = []
                    async with client.chat(
                        chat_ctx=ctx,
                        extra_kwargs={"response_format": response_format(schema)},
                        conn_options=APIConnectOptions(max_retry=0, timeout=timeout),
                    ) as stream:
                        async for chunk in stream:
                            if chunk.delta and chunk.delta.content:
                                pieces.append(chunk.delta.content)
                            if chunk.usage:
                                metric(
                                    "model_usage",
                                    model=model,
                                    input_tokens=chunk.usage.prompt_tokens,
                                    output_tokens=chunk.usage.completion_tokens,
                                )
                    try:
                        result = schema.model_validate_json("".join(pieces))
                        if validate:
                            validate(result)
                        return result
                    except (ValidationError, ValueError) as error:
                        category = "schema" if isinstance(error, ValidationError) else str(error)
                        paths = category
                        if isinstance(error, ValidationError):
                            fields = []
                            for item in error.errors(include_input=False, include_context=False)[
                                :4
                            ]:
                                root = item["loc"][0] if item["loc"] else "response"
                                # Log schema-owned names; exclude generated extra keys.
                                root = root if root in schema.model_fields else "response"
                                fields.append(f"{root} ({item['type']})")
                            paths = "; ".join(fields)
                        metric(
                            "model_invalid_result", model=model, error_type=category, location=paths
                        )
                        if attempt:
                            raise ProviderUnavailable("invalid_model_result") from None
                        # Errors are sent to the model without provider payloads or secret state.
                        ctx.add_message(
                            role="user",
                            content=(
                                "Regenerate the structured result from the same evidence. "
                                f"The previous result failed validation: {category}; "
                                f"fields: {paths}."
                            ),
                        )
            raise ProviderUnavailable("model_timeout")
        except ProviderUnavailable:
            raise
        except Exception as error:
            category = type(error).__name__
            status = getattr(error, "status_code", None)
            raise ProviderUnavailable(f"inference_{category}_{status}") from None
        finally:
            await client.aclose()
            metric(
                "model_request", model=model, duration_ms=round((time.monotonic() - started) * 1000)
            )
