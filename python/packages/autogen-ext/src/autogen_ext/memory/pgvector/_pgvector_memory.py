import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence, cast

from autogen_core import CancellationToken, Component
from autogen_core.memory import (
    Memory,
    MemoryContent,
    MemoryMimeType,
    MemoryQueryResult,
    UpdateContextResult,
)
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from pydantic import BaseModel, Field
from typing_extensions import Self

logger = logging.getLogger(__name__)

try:
    from pgvector.psycopg import register_vector_async
    from psycopg import sql
    from psycopg_pool import AsyncConnectionPool
except ImportError as e:
    raise ImportError(
        'To use PgvectorMemory you must install the pgvector extra: pip install "autogen-ext[pgvector]"'
    ) from e

# A synchronous callable that turns a batch of texts into their embedding vectors.
EmbeddingFunction = Callable[[Sequence[str]], Sequence[Sequence[float]]]

_TEXT_MIME_TYPES = (MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN)


class PgvectorMemoryConfig(BaseModel):
    """Configuration for :class:`PgvectorMemory`.

    The embedding model runs locally (SentenceTransformers) by default, and the
    vectors live in a PostgreSQL database you control, so the memory store does
    not depend on any managed cloud service.
    """

    dsn: str = Field(
        default="postgresql://localhost:5432/autogen",
        description="PostgreSQL connection string, e.g. postgresql://user:password@host:5432/dbname.",
    )
    table_name: str = Field(default="autogen_memory", description="Name of the table that stores memory entries.")
    create_extension: bool = Field(
        default=True,
        description="Run CREATE EXTENSION IF NOT EXISTS vector on first use. Set False on managed PostgreSQL where the "
        "extension is pre-provisioned and the application role lacks the privilege to create it.",
    )
    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="SentenceTransformers model used by the default embedder.",
    )
    embedding_dimension: int = Field(
        default=384,
        description="Dimension of the stored vectors. Must match the embedding model and stays fixed for the table.",
    )
    top_k: int = Field(default=10, description="Maximum number of memories returned by a query.")
    distance_threshold: Optional[float] = Field(
        default=None,
        description="Optional cosine-distance ceiling in [0, 2]; farther memories are dropped. None returns the top_k closest.",
    )
    hnsw_m: int = Field(default=16, description="pgvector HNSW index parameter m (graph degree).")
    hnsw_ef_construction: int = Field(
        default=64, description="pgvector HNSW index parameter ef_construction (build effort)."
    )


class PgvectorMemory(Memory, Component[PgvectorMemoryConfig]):
    """Store and retrieve memory using vector similarity search backed by PostgreSQL + pgvector.

    ``PgvectorMemory`` is a self-hosted, semantic memory: content is embedded and
    stored, with its vector, in a PostgreSQL table you own, and :meth:`query`
    returns the entries closest to the query by cosine distance using a pgvector
    HNSW index. Unlike the ChromaDB and Redis backends it keeps everything on a
    database you control, which suits on-premise, air-gapped, and
    data-residency-constrained deployments.

    This implementation requires the pgvector extra:

    .. code-block:: bash

        pip install "autogen-ext[pgvector]"

    You also need a PostgreSQL database with the ``vector`` extension available.
    The table and indexes are created on first use. The ``vector`` extension is
    also created then by default; on managed PostgreSQL where it is already
    provisioned and the application role cannot create extensions, set
    ``create_extension=False``.

    Args:
        config (PgvectorMemoryConfig | None): Configuration for the memory. If
            None, defaults to ``PgvectorMemoryConfig()``.
        connection_pool: Optional pre-configured ``psycopg_pool.AsyncConnectionPool``.
            When omitted, one is created lazily from ``config.dsn`` and managed
            (opened and closed) by this instance.
        embedding_function: Optional callable that embeds a batch of texts,
            overriding the default SentenceTransformers embedder. It is a runtime
            dependency and is not part of the serialized component config.

    Example:

        .. code-block:: python

            import asyncio
            from autogen_core.memory import MemoryContent, MemoryMimeType
            from autogen_ext.memory.pgvector import PgvectorMemory, PgvectorMemoryConfig


            async def main() -> None:
                memory = PgvectorMemory(PgvectorMemoryConfig(dsn="postgresql://postgres:pw@localhost:5432/autogen"))
                await memory.add(
                    MemoryContent(
                        content="The weather should be in metric units",
                        mime_type=MemoryMimeType.TEXT,
                        metadata={"category": "preferences"},
                    )
                )
                result = await memory.query("what units for weather?")
                print([m.content for m in result.results])
                await memory.close()


            asyncio.run(main())
    """

    component_config_schema = PgvectorMemoryConfig
    component_provider_override = "autogen_ext.memory.pgvector.PgvectorMemory"

    def __init__(
        self,
        config: PgvectorMemoryConfig | None = None,
        *,
        connection_pool: Any | None = None,
        embedding_function: EmbeddingFunction | None = None,
    ) -> None:
        self.config = config or PgvectorMemoryConfig()
        self._pool = connection_pool
        self._owns_pool = connection_pool is None
        self._pool_opened = False
        self._embedding_function = embedding_function
        self._default_model: Any = None
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    @property
    def _table(self) -> str:
        return self.config.table_name

    async def update_context(self, model_context: ChatCompletionContext) -> UpdateContextResult:
        """Query memory with the last message and append the results as a system message."""
        messages = await model_context.get_messages()
        last_message = str(messages[-1].content) if messages else ""

        query_results = await self.query(last_message)
        if query_results.results:
            stringified = "\n\n".join(str(m.content) for m in query_results.results)
            await model_context.add_message(SystemMessage(content=stringified))

        return UpdateContextResult(memories=query_results)

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        """Embed a memory content item and store it, with its vector, in PostgreSQL."""
        text, mime_type = self._content_to_text(content)
        embedding = (await self._embed([text]))[0]
        metadata = dict(content.metadata) if content.metadata else {}

        pool = await self._ensure_pool()
        async with pool.connection() as conn:
            await self._prepare_connection(conn)
            await conn.execute(
                sql.SQL(
                    "INSERT INTO {table} (id, content, mime_type, metadata, embedding)"
                    " VALUES (%s, %s, %s, %s::jsonb, %s::vector)"
                ).format(table=sql.Identifier(self._table)),
                (uuid.uuid4().hex, text, mime_type, json.dumps(metadata), list(embedding)),
            )

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Return the memories closest to ``query`` by cosine distance.

        Supported keyword arguments: ``top_k`` (int) and ``distance_threshold``
        (float, a cosine-distance ceiling), each overriding the config default.
        """
        top_k = kwargs.pop("top_k", self.config.top_k)
        threshold = kwargs.pop("distance_threshold", self.config.distance_threshold)

        text = query if isinstance(query, str) else self._content_to_text(query)[0]
        if not text.strip():
            return MemoryQueryResult(results=[])

        embedding = (await self._embed([text]))[0]
        pool = await self._ensure_pool()
        async with pool.connection() as conn:
            await self._prepare_connection(conn)
            cursor = await conn.execute(
                sql.SQL(
                    "SELECT content, mime_type, metadata, embedding <=> %s::vector AS distance"
                    " FROM {table} ORDER BY distance LIMIT %s"
                ).format(table=sql.Identifier(self._table)),
                (list(embedding), top_k),
            )
            rows = await cursor.fetchall()

        results: List[MemoryContent] = []
        for stored_content, mime_type, metadata, distance in rows:
            if threshold is not None and distance is not None and distance > threshold:
                continue
            results.append(self._row_to_memory(stored_content, mime_type, metadata, distance))
        return MemoryQueryResult(results=results)

    async def clear(self) -> None:
        """Delete all entries from the memory table, keeping the table itself."""
        pool = await self._ensure_pool()
        async with pool.connection() as conn:
            await self._prepare_connection(conn)
            await conn.execute(sql.SQL("DELETE FROM {table}").format(table=sql.Identifier(self._table)))

    async def close(self) -> None:
        """Close the connection pool if this instance created it."""
        if self._owns_pool and self._pool is not None and self._pool_opened:
            await self._pool.close()
            self._pool_opened = False

    def _to_config(self) -> PgvectorMemoryConfig:
        return self.config

    @classmethod
    def _from_config(cls, config: PgvectorMemoryConfig) -> Self:
        return cls(config=config)

    # --- Internals ------------------------------------------------------------

    @staticmethod
    def _content_to_text(content: MemoryContent) -> tuple[str, str]:
        """Returns the storable/embeddable text and the stored mime-type string."""
        if content.mime_type in _TEXT_MIME_TYPES:
            return str(content.content), _mime_value(content.mime_type)
        if content.mime_type == MemoryMimeType.JSON:
            return json.dumps(content.content), MemoryMimeType.JSON.value
        raise NotImplementedError(
            f"{content.mime_type} is not supported. Only MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN,"
            " and MemoryMimeType.JSON are currently supported."
        )

    @staticmethod
    def _row_to_memory(stored_content: str, mime_type: str, metadata: Any, distance: float | None) -> MemoryContent:
        if isinstance(metadata, dict):
            parsed_metadata: Dict[str, Any] = cast(Dict[str, Any], metadata)
        elif metadata:
            parsed_metadata = cast(Dict[str, Any], json.loads(metadata))
        else:
            parsed_metadata = {}
        if distance is not None:
            parsed_metadata = {**parsed_metadata, "score": float(distance)}
        try:
            resolved_mime: MemoryMimeType | str = MemoryMimeType(mime_type)
        except ValueError:
            resolved_mime = mime_type
        value: Any = json.loads(stored_content) if resolved_mime == MemoryMimeType.JSON else stored_content
        return MemoryContent(content=value, mime_type=resolved_mime, metadata=parsed_metadata)

    async def _embed(self, texts: Sequence[str]) -> List[List[float]]:
        embedder = self._embedding_function or self._default_embedder()
        vectors = await asyncio.to_thread(embedder, list(texts))
        return [[float(v) for v in vector] for vector in vectors]

    def _default_embedder(self) -> EmbeddingFunction:
        """Builds (once) a SentenceTransformers embedder from ``config.model_name``."""
        if self._default_model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found,import-untyped]
            except ImportError as e:
                raise ImportError(
                    "The default embedder needs sentence-transformers. Install the pgvector extra"
                    ' (pip install "autogen-ext[pgvector]") or pass embedding_function.'
                ) from e
            self._default_model = cast(Any, SentenceTransformer(self.config.model_name))
        model: Any = self._default_model

        def _encode(batch: Sequence[str]) -> List[List[float]]:
            return cast(List[List[float]], model.encode(list(batch)).tolist())

        return _encode

    def _get_pool(self) -> Any:
        if self._pool is None:
            self._pool = AsyncConnectionPool(self.config.dsn, open=False)
        return self._pool

    async def _ensure_pool(self) -> Any:
        """Returns the pool, opening it once if this instance created it."""
        pool = self._get_pool()
        if self._owns_pool and not self._pool_opened:
            await pool.open()
            self._pool_opened = True
        return pool

    async def _prepare_connection(self, conn: Any) -> None:
        if register_vector_async is not None:
            await register_vector_async(conn)
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            await self._ensure_schema(conn)
            self._schema_ready = True

    async def _ensure_schema(self, conn: Any) -> None:
        if self.config.create_extension:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        table = sql.Identifier(self._table)
        await conn.execute(
            sql.SQL(
                "CREATE TABLE IF NOT EXISTS {table} ("
                " id text PRIMARY KEY,"
                " content text NOT NULL,"
                " mime_type text NOT NULL,"
                " metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,"
                " embedding vector({dim}) NOT NULL,"
                " created_at timestamptz NOT NULL DEFAULT now()"
                ")"
            ).format(table=table, dim=sql.Literal(self.config.embedding_dimension))
        )
        await conn.execute(
            sql.SQL(
                "CREATE INDEX IF NOT EXISTS {index} ON {table}"
                " USING hnsw (embedding vector_cosine_ops)"
                " WITH (m = {m}, ef_construction = {ef})"
            ).format(
                index=sql.Identifier(f"{self._table}_embedding_idx"),
                table=table,
                m=sql.Literal(self.config.hnsw_m),
                ef=sql.Literal(self.config.hnsw_ef_construction),
            )
        )


def _mime_value(mime_type: MemoryMimeType | str) -> str:
    return mime_type.value if isinstance(mime_type, MemoryMimeType) else mime_type
