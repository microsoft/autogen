from pydantic import BaseModel


class DataConfig(BaseModel):
    input_dir: str
    entity_table: str = "entities"
    entity_embedding_table: str = "entities"
    community_table: str = "communities"
    community_level: int = 2


class GlobalDataConfig(DataConfig):
    community_report_table: str = "community_reports"


class LocalDataConfig(DataConfig):
    relationship_table: str = "relationships"
    text_unit_table: str = "text_units"


class ContextConfig(BaseModel):
    max_data_tokens: int = 8000


class GlobalContextConfig(ContextConfig):
    use_community_summary: bool = False
    shuffle_data: bool = True
    include_community_rank: bool = True
    min_community_rank: int = 0
    community_rank_name: str = "rank"
    include_community_weight: bool = True
    community_weight_name: str = "occurrence weight"
    normalize_community_weight: bool = True
    max_data_tokens: int = 12000


class LocalContextConfig(ContextConfig):
    text_unit_prop: float = 0.5
    community_prop: float = 0.25
    include_entity_rank: bool = True
    rank_description: str = "number of relationships"
    include_relationship_weight: bool = True
    relationship_ranking_attribute: str = "rank"


class MapReduceConfig(BaseModel):
    map_max_tokens: int = 1000
    map_temperature: float = 0.0
    reduce_max_tokens: int = 2000
    reduce_temperature: float = 0.0
    allow_general_knowledge: bool = False
    json_mode: bool = False
    response_type: str = "multiple paragraphs"


class SearchConfig(BaseModel):
    max_tokens: int = 1500
    temperature: float = 0.0
    response_type: str = "multiple paragraphs"
