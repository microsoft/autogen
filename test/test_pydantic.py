from typing import Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from autogen._pydantic import model_dump, model_dump_json, type2schema


def test_type2schema() -> None:
    assert type2schema(str) == {"type": "string"}
    assert type2schema(int) == {"type": "integer"}
    assert type2schema(float) == {"type": "number"}
    assert type2schema(bool) == {"type": "boolean"}
    assert type2schema(None) == {"type": "null"}
    assert type2schema(Optional[int]) == {"anyOf": [{"type": "integer"}, {"type": "null"}]}
    assert type2schema(List[int]) == {"items": {"type": "integer"}, "type": "array"}
    assert type2schema(Tuple[int, float, str]) == {
        "maxItems": 3,
        "minItems": 3,
        "prefixItems": [{"type": "integer"}, {"type": "number"}, {"type": "string"}],
        "type": "array",
    }
    assert type2schema(Dict[str, int]) == {"additionalProperties": {"type": "integer"}, "type": "object"}
    assert type2schema(Annotated[str, "some text"]) == {"type": "string"}
    assert type2schema(Union[int, float]) == {"anyOf": [{"type": "integer"}, {"type": "number"}]}


def test_model_dump() -> None:
    class A(BaseModel):
        a: str
        b: int = 2

    assert model_dump(A(a="aaa")) == {"a": "aaa", "b": 2}


def test_model_dump_json() -> None:
    class A(BaseModel):
        a: str
        b: int = 2

    assert model_dump_json(A(a="aaa")).replace(" ", "") == '{"a":"aaa","b":2}'
