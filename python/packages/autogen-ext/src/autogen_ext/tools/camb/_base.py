import asyncio
import os
import struct
import tempfile
from abc import abstractmethod
from typing import Any, Generic, Optional, TypeVar

from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool
from pydantic import BaseModel
from typing_extensions import Self

from ._config import CambToolConfig

ArgsT = TypeVar("ArgsT", bound=BaseModel)
ReturnT = TypeVar("ReturnT")


class CambBaseTool(BaseTool[ArgsT, ReturnT], Component[CambToolConfig], Generic[ArgsT, ReturnT]):
    """Abstract base class for CAMB.AI tools.

    Manages the AsyncCambAI client lifecycle and provides shared utilities
    for polling async tasks, saving audio, and detecting audio formats.
    Uses the ``camb-sdk`` package with its native async client.
    """

    component_type = "tool"
    component_config_schema = CambToolConfig

    def __init__(
        self,
        args_type: type[ArgsT],
        return_type: type[ReturnT],
        name: str,
        description: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(
            args_type=args_type,
            return_type=return_type,
            name=name,
            description=description,
        )
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._max_poll_attempts = max_poll_attempts
        self._poll_interval = poll_interval
        self._client: Any = None

    def _get_api_key(self) -> str:
        """Resolve API key from parameter or environment variable."""
        key = self._api_key or os.environ.get("CAMB_API_KEY")
        if not key:
            raise ValueError(
                "CAMB.AI API key is required. Provide it via the api_key parameter "
                "or set the CAMB_API_KEY environment variable."
            )
        return key

    def _get_client(self) -> Any:
        """Get or create the AsyncCambAI client (lazy initialization)."""
        if self._client is None:
            from camb.client import AsyncCambAI

            kwargs: dict[str, Any] = {"api_key": self._get_api_key()}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            if self._timeout is not None:
                kwargs["timeout"] = self._timeout
            self._client = AsyncCambAI(**kwargs)
        return self._client

    async def _poll_task_status(
        self,
        status_func: Any,
        task_id: str,
    ) -> Any:
        """Poll an async task until completion or failure.

        Args:
            status_func: Async function to call for status checks (e.g. client.transcription.get_transcription_task_status).
            task_id: The task ID to poll.

        Returns:
            The final status result when the task completes.

        Raises:
            RuntimeError: If the task fails or times out.
        """
        for _ in range(self._max_poll_attempts):
            result = await status_func(task_id)
            status = getattr(result, "status", None)
            if status is None and hasattr(result, "message"):
                status = getattr(result.message, "status", None)
            if status in ("SUCCESS", "complete", "completed"):
                return result
            if status in ("ERROR", "TIMEOUT", "PAYMENT_REQUIRED", "failed", "error"):
                reason = getattr(result, "exception_reason", "") or ""
                raise RuntimeError(f"CAMB.AI task failed with status: {status}. {reason}")
            await asyncio.sleep(self._poll_interval)
        raise RuntimeError(
            f"CAMB.AI task timed out after {self._max_poll_attempts * self._poll_interval}s"
        )

    @staticmethod
    def _detect_audio_format(data: bytes) -> str:
        """Detect audio format from raw bytes."""
        if data[:4] == b"RIFF":
            return "wav"
        if data[:3] == b"ID3" or data[:2] == b"\xff\xfb":
            return "mp3"
        if data[:4] == b"fLaC":
            return "flac"
        if data[:4] == b"OggS":
            return "ogg"
        return "wav"

    @staticmethod
    def _add_wav_header(
        raw_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16
    ) -> bytes:
        """Add a WAV header to raw PCM audio data."""
        data_size = len(raw_data)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,
            1,  # PCM format
            channels,
            sample_rate,
            sample_rate * channels * bits_per_sample // 8,
            channels * bits_per_sample // 8,
            bits_per_sample,
            b"data",
            data_size,
        )
        return header + raw_data

    @staticmethod
    def _save_audio(data: bytes, extension: str = "wav") -> str:
        """Save audio data to a temporary file and return the file path."""
        with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=False) as f:
            f.write(data)
            return f.name

    def _to_config(self) -> CambToolConfig:
        return CambToolConfig(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=self._timeout,
            max_poll_attempts=self._max_poll_attempts,
            poll_interval=self._poll_interval,
        )

    @classmethod
    @abstractmethod
    def _from_config(cls, config: CambToolConfig) -> Self:
        ...
