import types
from typing import Any, Dict, List, Literal, Optional, Type, get_args, get_origin
from uuid import UUID, uuid4

import pytest
from autogen_core.utils._json_to_pydantic import (
    FORMAT_MAPPING,
    TYPE_MAPPING,
    FormatNotSupportedError,
    ReferenceNotFoundError,
    UnsupportedKeywordError,
    _JSONSchemaToPydantic,  # pyright: ignore[reportPrivateUsage]
)
from pydantic import BaseModel, EmailStr, Field, ValidationError


# ✅ Define Pydantic models for testing
class Address(BaseModel):
    street: str
    city: str
    zipcode: str


class User(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    age: int = Field(..., ge=18)  # Minimum age = 18
    address: Address


class Employee(BaseModel):
    id: UUID
    name: str
    manager: Optional["Employee"] = None  # Recursive self-reference


class Department(BaseModel):
    name: str
    employees: List[Employee]  # Array of objects


class ComplexModel(BaseModel):
    user: User
    extra_info: Optional[Dict[str, Any]] = None  # Optional dictionary
    sub_items: List[Employee]  # List of Employees


@pytest.fixture
def converter() -> _JSONSchemaToPydantic:
    """Fixture to create a fresh instance of JSONSchemaToPydantic for every test."""
    return _JSONSchemaToPydantic()


@pytest.fixture
def sample_json_schema() -> Dict[str, Any]:
    """Fixture that returns a JSON schema dynamically using model_json_schema()."""
    return User.model_json_schema()


@pytest.fixture
def sample_json_schema_recursive() -> Dict[str, Any]:
    """Fixture that returns a self-referencing JSON schema."""
    return Employee.model_json_schema()


@pytest.fixture
def sample_json_schema_nested() -> Dict[str, Any]:
    """Fixture that returns a nested schema with arrays of objects."""
    return Department.model_json_schema()


@pytest.fixture
def sample_json_schema_complex() -> Dict[str, Any]:
    """Fixture that returns a complex schema with multiple structures."""
    return ComplexModel.model_json_schema()


@pytest.mark.parametrize(
    "schema_fixture, model_name, expected_fields",
    [
        (sample_json_schema, "User", ["id", "name", "email", "age", "address"]),
        (sample_json_schema_recursive, "Employee", ["id", "name", "manager"]),
        (sample_json_schema_nested, "Department", ["name", "employees"]),
        (sample_json_schema_complex, "ComplexModel", ["user", "extra_info", "sub_items"]),
    ],
)
def test_json_schema_to_pydantic(
    converter: _JSONSchemaToPydantic,
    schema_fixture: Any,
    model_name: str,
    expected_fields: List[str],
    request: Any,
) -> None:
    """Test conversion of JSON Schema to Pydantic model using the class instance."""
    schema = request.getfixturevalue(schema_fixture.__name__)
    Model = converter.json_schema_to_pydantic(schema, model_name)

    for field in expected_fields:
        assert field in Model.__annotations__, f"Expected '{field}' missing in {model_name}Model"


# ✅ **Valid Data Tests**
@pytest.mark.parametrize(
    "schema_fixture, model_name, valid_data",
    [
        (
            sample_json_schema,
            "User",
            {
                "id": str(uuid4()),
                "name": "Alice",
                "email": "alice@example.com",
                "age": 25,
                "address": {"street": "123 Main St", "city": "Metropolis", "zipcode": "12345"},
            },
        ),
        (
            sample_json_schema_recursive,
            "Employee",
            {
                "id": str(uuid4()),
                "name": "Alice",
                "manager": {
                    "id": str(uuid4()),
                    "name": "Bob",
                },
            },
        ),
        (
            sample_json_schema_nested,
            "Department",
            {
                "name": "Engineering",
                "employees": [
                    {
                        "id": str(uuid4()),
                        "name": "Alice",
                        "manager": {
                            "id": str(uuid4()),
                            "name": "Bob",
                        },
                    }
                ],
            },
        ),
        (
            sample_json_schema_complex,
            "ComplexModel",
            {
                "user": {
                    "id": str(uuid4()),
                    "name": "Charlie",
                    "email": "charlie@example.com",
                    "age": 30,
                    "address": {"street": "456 Side St", "city": "Gotham", "zipcode": "67890"},
                },
                "extra_info": {"hobby": "Chess", "level": "Advanced"},
                "sub_items": [
                    {"id": str(uuid4()), "name": "Eve"},
                    {"id": str(uuid4()), "name": "David", "manager": {"id": str(uuid4()), "name": "Frank"}},
                ],
            },
        ),
    ],
)
def test_valid_data_model(
    converter: _JSONSchemaToPydantic,
    schema_fixture: Any,
    model_name: str,
    valid_data: Dict[str, Any],
    request: Any,
) -> None:
    """Test that valid data is accepted by the generated model."""
    schema = request.getfixturevalue(schema_fixture.__name__)
    Model = converter.json_schema_to_pydantic(schema, model_name)

    instance = Model(**valid_data)
    assert instance
    dumped = instance.model_dump(mode="json", exclude_none=True)
    assert dumped == valid_data, f"Model output mismatch.\nExpected: {valid_data}\nGot: {dumped}"


# ✅ **Invalid Data Tests**
@pytest.mark.parametrize(
    "schema_fixture, model_name, invalid_data",
    [
        (
            sample_json_schema,
            "User",
            {
                "id": "not-a-uuid",  # Invalid UUID
                "name": "Alice",
                "email": "not-an-email",  # Invalid email
                "age": 17,  # Below minimum
                "address": {"street": "123 Main St", "city": "Metropolis"},
            },
        ),
        (
            sample_json_schema_recursive,
            "Employee",
            {
                "id": str(uuid4()),
                "name": "Alice",
                "manager": {
                    "id": "not-a-uuid",  # Invalid UUID
                    "name": "Bob",
                },
            },
        ),
        (
            sample_json_schema_nested,
            "Department",
            {
                "name": "Engineering",
                "employees": [
                    {
                        "id": "not-a-uuid",  # Invalid UUID
                        "name": "Alice",
                        "manager": {
                            "id": str(uuid4()),
                            "name": "Bob",
                        },
                    }
                ],
            },
        ),
        (
            sample_json_schema_complex,
            "ComplexModel",
            {
                "user": {
                    "id": str(uuid4()),
                    "name": "Charlie",
                    "email": "charlie@example.com",
                    "age": "thirty",  # Invalid: Should be an int
                    "address": {"street": "456 Side St", "city": "Gotham", "zipcode": "67890"},
                },
                "extra_info": "should-be-dictionary",  # Invalid type
                "sub_items": [
                    {"id": "invalid-uuid", "name": "Eve"},  # Invalid UUID
                    {"id": str(uuid4()), "name": 123},  # Invalid name type
                ],
            },
        ),
    ],
)
def test_invalid_data_model(
    converter: _JSONSchemaToPydantic,
    schema_fixture: Any,
    model_name: str,
    invalid_data: Dict[str, Any],
    request: Any,
) -> None:
    """Test that invalid data raises ValidationError."""
    schema = request.getfixturevalue(schema_fixture.__name__)
    Model = converter.json_schema_to_pydantic(schema, model_name)

    with pytest.raises(ValidationError):
        Model(**invalid_data)


class ListDictModel(BaseModel):
    """Example for `List[Dict[str, Any]]`"""

    data: List[Dict[str, Any]]


class DictListModel(BaseModel):
    """Example for `Dict[str, List[Any]]`"""

    mapping: Dict[str, List[Any]]


class NestedListModel(BaseModel):
    """Example for `List[List[str]]`"""

    matrix: List[List[str]]


@pytest.fixture
def sample_json_schema_list_dict() -> Dict[str, Any]:
    """Fixture for `List[Dict[str, Any]]`"""
    return ListDictModel.model_json_schema()


@pytest.fixture
def sample_json_schema_dict_list() -> Dict[str, Any]:
    """Fixture for `Dict[str, List[Any]]`"""
    return DictListModel.model_json_schema()


@pytest.fixture
def sample_json_schema_nested_list() -> Dict[str, Any]:
    """Fixture for `List[List[str]]`"""
    return NestedListModel.model_json_schema()


@pytest.mark.parametrize(
    "schema_fixture, model_name, expected_fields",
    [
        (sample_json_schema_list_dict, "ListDictModel", ["data"]),
        (sample_json_schema_dict_list, "DictListModel", ["mapping"]),
        (sample_json_schema_nested_list, "NestedListModel", ["matrix"]),
    ],
)
def test_json_schema_to_pydantic_nested(
    converter: _JSONSchemaToPydantic,
    schema_fixture: Any,
    model_name: str,
    expected_fields: list[str],
    request: Any,
) -> None:
    """Test conversion of JSON Schema to Pydantic model using the class instance."""
    schema = request.getfixturevalue(schema_fixture.__name__)
    Model = converter.json_schema_to_pydantic(schema, model_name)

    for field in expected_fields:
        assert field in Model.__annotations__, f"Expected '{field}' missing in {model_name}Model"


# ✅ **Valid Data Tests**
@pytest.mark.parametrize(
    "schema_fixture, model_name, valid_data",
    [
        (
            sample_json_schema_list_dict,
            "ListDictModel",
            {
                "data": [
                    {"key1": "value1", "key2": 10},
                    {"another_key": False, "nested": {"subkey": "data"}},
                ]
            },
        ),
        (
            sample_json_schema_dict_list,
            "DictListModel",
            {
                "mapping": {
                    "first": ["a", "b", "c"],
                    "second": [1, 2, 3, 4],
                    "third": [True, False, True],
                }
            },
        ),
        (
            sample_json_schema_nested_list,
            "NestedListModel",
            {"matrix": [["A", "B"], ["C", "D"], ["E", "F"]]},
        ),
    ],
)
def test_valid_data_model_nested(
    converter: _JSONSchemaToPydantic,
    schema_fixture: Any,
    model_name: str,
    valid_data: Dict[str, Any],
    request: Any,
) -> None:
    """Test that valid data is accepted by the generated model."""
    schema = request.getfixturevalue(schema_fixture.__name__)
    Model = converter.json_schema_to_pydantic(schema, model_name)

    instance = Model(**valid_data)
    assert instance
    for field, value in valid_data.items():
        assert (
            getattr(instance, field) == value
        ), f"Mismatch in field `{field}`: expected `{value}`, got `{getattr(instance, field)}`"


# ✅ **Invalid Data Tests**
@pytest.mark.parametrize(
    "schema_fixture, model_name, invalid_data",
    [
        (
            sample_json_schema_list_dict,
            "ListDictModel",
            {
                "data": "should-be-a-list",  # ❌ Should be a list of dicts
            },
        ),
        (
            sample_json_schema_dict_list,
            "DictListModel",
            {
                "mapping": [
                    "should-be-a-dictionary",  # ❌ Should be a dict of lists
                ]
            },
        ),
        (
            sample_json_schema_nested_list,
            "NestedListModel",
            {"matrix": [["A", "B"], "C", ["D", "E"]]},  # ❌ "C" is not a list
        ),
    ],
)
def test_invalid_data_model_nested(
    converter: _JSONSchemaToPydantic,
    schema_fixture: Any,
    model_name: str,
    invalid_data: Dict[str, Any],
    request: Any,
) -> None:
    """Test that invalid data raises ValidationError."""
    schema = request.getfixturevalue(schema_fixture.__name__)
    Model = converter.json_schema_to_pydantic(schema, model_name)

    with pytest.raises(ValidationError):
        Model(**invalid_data)


def test_reference_not_found(converter: _JSONSchemaToPydantic) -> None:
    schema = {"type": "object", "properties": {"manager": {"$ref": "#/$defs/MissingRef"}}}
    with pytest.raises(ReferenceNotFoundError):
        converter.json_schema_to_pydantic(schema, "MissingRefModel")


def test_format_not_supported(converter: _JSONSchemaToPydantic) -> None:
    schema = {"type": "object", "properties": {"custom_field": {"type": "string", "format": "unsupported-format"}}}
    with pytest.raises(FormatNotSupportedError):
        converter.json_schema_to_pydantic(schema, "UnsupportedFormatModel")


def test_unsupported_keyword(converter: _JSONSchemaToPydantic) -> None:
    schema = {"type": "object", "properties": {"broken_field": {"title": "Missing type"}}}
    with pytest.raises(UnsupportedKeywordError):
        converter.json_schema_to_pydantic(schema, "MissingTypeModel")


def test_enum_field_schema() -> None:
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["pending", "approved", "rejected"]},
            "priority": {"type": "integer", "enum": [1, 2, 3]},
        },
        "required": ["status"],
    }

    converter: _JSONSchemaToPydantic = _JSONSchemaToPydantic()
    Model = converter.json_schema_to_pydantic(schema, "Task")

    status_ann = Model.model_fields["status"].annotation
    assert get_origin(status_ann) is Literal
    assert set(get_args(status_ann)) == {"pending", "approved", "rejected"}

    priority_ann = Model.model_fields["priority"].annotation
    args = get_args(priority_ann)
    assert type(None) in args
    assert Literal[1, 2, 3] in args

    instance = Model(status="approved", priority=2)
    assert instance.status == "approved"  # type: ignore[attr-defined]
    assert instance.priority == 2  # type: ignore[attr-defined]


def test_metadata_title_description(converter: _JSONSchemaToPydantic) -> None:
    schema = {
        "title": "CustomerProfile",
        "description": "A profile containing personal and contact info",
        "type": "object",
        "properties": {
            "first_name": {"type": "string", "title": "First Name", "description": "Given name of the user"},
            "age": {"type": "integer", "title": "Age", "description": "Age in years"},
            "contact": {
                "type": "object",
                "title": "Contact Information",
                "description": "How to reach the user",
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "title": "Email Address",
                        "description": "Primary email",
                    }
                },
            },
        },
        "required": ["first_name"],
    }

    Model: Type[BaseModel] = converter.json_schema_to_pydantic(schema, "CustomerProfile")
    generated_schema = Model.model_json_schema()

    assert generated_schema["title"] == "CustomerProfile"

    props = generated_schema["properties"]
    assert props["first_name"]["title"] == "First Name"
    assert props["first_name"]["description"] == "Given name of the user"
    assert props["age"]["title"] == "Age"
    assert props["age"]["description"] == "Age in years"

    contact = props["contact"]
    assert contact["title"] == "Contact Information"
    assert contact["description"] == "How to reach the user"

    # Follow the $ref
    ref_key = contact["anyOf"][0]["$ref"].split("/")[-1]
    contact_def = generated_schema["$defs"][ref_key]
    email = contact_def["properties"]["email"]
    assert email["title"] == "Email Address"
    assert email["description"] == "Primary email"


def test_oneof_with_discriminator(converter: _JSONSchemaToPydantic) -> None:
    schema = {
        "title": "PetWrapper",
        "type": "object",
        "properties": {
            "pet": {
                "oneOf": [{"$ref": "#/$defs/Cat"}, {"$ref": "#/$defs/Dog"}],
                "discriminator": {"propertyName": "pet_type"},
            }
        },
        "required": ["pet"],
        "$defs": {
            "Cat": {
                "type": "object",
                "properties": {"pet_type": {"type": "string", "enum": ["cat"]}, "hunting_skill": {"type": "string"}},
                "required": ["pet_type", "hunting_skill"],
                "title": "Cat",
            },
            "Dog": {
                "type": "object",
                "properties": {"pet_type": {"type": "string", "enum": ["dog"]}, "pack_size": {"type": "integer"}},
                "required": ["pet_type", "pack_size"],
                "title": "Dog",
            },
        },
    }

    Model = converter.json_schema_to_pydantic(schema, "PetWrapper")

    # Instantiate with a Cat
    cat = Model(pet={"pet_type": "cat", "hunting_skill": "expert"})
    assert cat.pet.pet_type == "cat"  # type: ignore[attr-defined]

    # Instantiate with a Dog
    dog = Model(pet={"pet_type": "dog", "pack_size": 4})
    assert dog.pet.pet_type == "dog"  # type: ignore[attr-defined]

    # Check round-trip schema includes discriminator
    model_schema = Model.model_json_schema()
    assert "discriminator" in model_schema["properties"]["pet"]
    assert model_schema["properties"]["pet"]["discriminator"]["propertyName"] == "pet_type"


def test_allof_merging_with_refs(converter: _JSONSchemaToPydantic) -> None:
    schema = {
        "title": "EmployeeWithDepartment",
        "allOf": [{"$ref": "#/$defs/Employee"}, {"$ref": "#/$defs/Department"}],
        "$defs": {
            "Employee": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
                "required": ["id", "name"],
                "title": "Employee",
            },
            "Department": {
                "type": "object",
                "properties": {"department": {"type": "string"}},
                "required": ["department"],
                "title": "Department",
            },
        },
    }

    Model = converter.json_schema_to_pydantic(schema, "EmployeeWithDepartment")
    instance = Model(id="123", name="Alice", department="Engineering")
    assert instance.id == "123"  # type: ignore[attr-defined]
    assert instance.name == "Alice"  # type: ignore[attr-defined]
    assert instance.department == "Engineering"  # type: ignore[attr-defined]

    dumped = instance.model_dump()
    assert dumped == {"id": "123", "name": "Alice", "department": "Engineering"}


def test_nested_allof_merging(converter: _JSONSchemaToPydantic) -> None:
    schema = {
        "title": "ContainerModel",
        "type": "object",
        "properties": {
            "nested": {
                "type": "object",
                "properties": {
                    "data": {
                        "allOf": [
                            {"$ref": "#/$defs/Base"},
                            {"type": "object", "properties": {"extra": {"type": "string"}}, "required": ["extra"]},
                        ]
                    }
                },
                "required": ["data"],
            }
        },
        "required": ["nested"],
        "$defs": {
            "Base": {
                "type": "object",
                "properties": {"base_field": {"type": "string"}},
                "required": ["base_field"],
                "title": "Base",
            }
        },
    }

    Model = converter.json_schema_to_pydantic(schema, "ContainerModel")
    instance = Model(nested={"data": {"base_field": "abc", "extra": "xyz"}})

    assert instance.nested.data.base_field == "abc"  # type: ignore[attr-defined]
    assert instance.nested.data.extra == "xyz"  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "schema, field_name, valid_values, invalid_values",
    [
        # String constraints
        (
            {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "minLength": 3, "maxLength": 10, "pattern": "^[a-zA-Z0-9_]+$"}
                },
                "required": ["username"],
            },
            "username",
            ["user_123", "abc", "Name2023"],
            ["", "ab", "toolongusername123", "invalid!char"],
        ),
        # Integer constraints
        (
            {
                "type": "object",
                "properties": {"age": {"type": "integer", "minimum": 18, "maximum": 99}},
                "required": ["age"],
            },
            "age",
            [18, 25, 99],
            [17, 100, -1],
        ),
        # Float constraints
        (
            {
                "type": "object",
                "properties": {"score": {"type": "number", "minimum": 0.0, "exclusiveMaximum": 1.0}},
                "required": ["score"],
            },
            "score",
            [0.0, 0.5, 0.999],
            [-0.1, 1.0, 2.5],
        ),
        # Array constraints
        (
            {
                "type": "object",
                "properties": {"tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3}},
                "required": ["tags"],
            },
            "tags",
            [["a"], ["a", "b"], ["x", "y", "z"]],
            [[], ["one", "two", "three", "four"]],
        ),
    ],
)
def test_field_constraints(
    schema: Dict[str, Any],
    field_name: str,
    valid_values: List[Any],
    invalid_values: List[Any],
) -> None:
    converter = _JSONSchemaToPydantic()
    Model = converter.json_schema_to_pydantic(schema, "ConstraintModel")

    for value in valid_values:
        instance = Model(**{field_name: value})
        assert getattr(instance, field_name) == value

    for value in invalid_values:
        with pytest.raises(ValidationError):
            Model(**{field_name: value})


@pytest.mark.parametrize(
    "schema",
    [
        # Top-level field
        {"type": "object", "properties": {"weird": {"type": "abc"}}, "required": ["weird"]},
        # Inside array items
        {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "abc"}}}, "required": ["items"]},
        # Inside anyOf
        {
            "type": "object",
            "properties": {"choice": {"anyOf": [{"type": "string"}, {"type": "abc"}]}},
            "required": ["choice"],
        },
    ],
)
def test_unknown_type_raises(schema: Dict[str, Any]) -> None:
    converter = _JSONSchemaToPydantic()
    with pytest.raises(UnsupportedKeywordError):
        converter.json_schema_to_pydantic(schema, "UnknownTypeModel")


@pytest.mark.parametrize("json_type, expected_type", list(TYPE_MAPPING.items()))
def test_basic_type_mapping(json_type: str, expected_type: type) -> None:
    schema = {
        "type": "object",
        "properties": {"field": {"type": json_type}},
        "required": ["field"],
    }
    converter = _JSONSchemaToPydantic()
    Model = converter.json_schema_to_pydantic(schema, f"{json_type.capitalize()}Model")

    assert "field" in Model.__annotations__
    field_type = Model.__annotations__["field"]

    # For array/object/null we check the outer type only
    if json_type == "null":
        assert field_type is type(None)
    elif json_type == "array":
        assert getattr(field_type, "__origin__", None) is list
    elif json_type == "object":
        assert field_type in (dict, Dict) or getattr(field_type, "__origin__", None) in (dict, Dict)

    else:
        assert field_type == expected_type


@pytest.mark.parametrize("format_name, expected_type", list(FORMAT_MAPPING.items()))
def test_format_mapping(format_name: str, expected_type: Any) -> None:
    schema = {
        "type": "object",
        "properties": {"field": {"type": "string", "format": format_name}},
        "required": ["field"],
    }
    converter = _JSONSchemaToPydantic()
    Model = converter.json_schema_to_pydantic(schema, f"{format_name.capitalize()}Model")

    assert "field" in Model.__annotations__
    field_type = Model.__annotations__["field"]
    if isinstance(expected_type, types.FunctionType):  # if it's a constrained constructor (e.g., conint)
        assert callable(field_type)
    else:
        assert field_type == expected_type


def test_unknown_format_raises() -> None:
    schema = {
        "type": "object",
        "properties": {"bad_field": {"type": "string", "format": "definitely-not-a-format"}},
    }
    converter = _JSONSchemaToPydantic()
    with pytest.raises(FormatNotSupportedError):
        converter.json_schema_to_pydantic(schema, "UnknownFormatModel")
