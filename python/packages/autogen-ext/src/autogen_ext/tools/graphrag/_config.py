from typing import Callable, Literal, Optional

from pydantic import BaseModel, Field


class DataConfig(BaseModel):
    """Base configuration for data sources"""

    input_dir: str
    entity_table: str = "create_final_nodes"
    entity_embedding_table: str = "create_final_entities"
    community_level: int = 2


class BaseContextConfig(BaseModel):
    """Base configuration for context building"""

    max_data_tokens: int = 8000


class BaseSearchConfig(BaseModel):
    """Base configuration for search parameters"""

    max_tokens: int = 1500
    temperature: float = 0.0
    response_type: str = "multiple paragraphs"


class LocalDataConfig(DataConfig):
    """Data configuration specific to local search"""

    relationship_table: str = "create_final_relationships"
    text_unit_table: str = "create_final_text_units"


class LocalContextConfig(BaseContextConfig):
    """Context configuration specific to local search"""

    text_unit_prop: float = 0.5
    community_prop: float = 0.25
    include_entity_rank: bool = True
    rank_description: str = "number of relationships"
    include_relationship_weight: bool = True
    relationship_ranking_attribute: str = "rank"
    max_data_tokens: int = 8000


class GlobalDataConfig(DataConfig):
    """Data configuration specific to global search"""

    community_table: str = "create_final_communities"
    community_report_table: str = "create_final_community_reports"


class GlobalContextConfig(BaseContextConfig):
    """Context configuration specific to global search"""

    use_community_summary: bool = False
    shuffle_data: bool = True
    include_community_rank: bool = True
    min_community_rank: int = 0
    community_rank_name: str = "rank"
    include_community_weight: bool = True
    community_weight_name: str = "occurrence weight"
    normalize_community_weight: bool = True
    max_data_tokens: int = 12000


class MapReduceConfig(BaseSearchConfig):
    """Configuration specific to map-reduce operations in global search"""

    map_max_tokens: int = 1000
    map_temperature: float = 0.0
    reduce_max_tokens: int = 2000
    reduce_temperature: float = 0.0
    allow_general_knowledge: bool = False
    json_mode: bool = False


class EmbeddingConfig(BaseModel):
    """Configuration for text embedding model"""

    api_key: str | None = None
    azure_ad_token_provider: Callable | None = None
    model: str = "text-embedding-3-small"
    deployment_name: str | None = None
    api_base: str | None = None
    api_version: str | None = None
    api_type: Literal["openai", "azure"] = "openai"
    organization: str | None = None
    encoding_name: str = "cl100k_base"
    max_tokens: int = 8191
    max_retries: int = 10
    request_timeout: float = 180.0
