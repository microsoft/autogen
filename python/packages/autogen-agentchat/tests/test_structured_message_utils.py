from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
from autogen_agentchat.utils import JSONSchemaToPydantic
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
def converter():
    """Fixture to create a fresh instance of JSONSchemaToPydantic for every test."""
    return JSONSchemaToPydantic()


@pytest.fixture
def sample_json_schema():
    """Fixture that returns a JSON schema dynamically using model_json_schema()."""
    return User.model_json_schema()


@pytest.fixture
def sample_json_schema_recursive():
    """Fixture that returns a self-referencing JSON schema."""
    return Employee.model_json_schema()


@pytest.fixture
def sample_json_schema_nested():
    """Fixture that returns a nested schema with arrays of objects."""
    return Department.model_json_schema()


@pytest.fixture
def sample_json_schema_complex():
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
def test_json_schema_to_pydantic(converter, schema_fixture, model_name, expected_fields, request):
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
def test_valid_data_model(converter, schema_fixture, model_name, valid_data, request):
    """Test that valid data is accepted by the generated model."""
    schema = request.getfixturevalue(schema_fixture.__name__)
    Model = converter.json_schema_to_pydantic(schema, model_name)

    instance = Model(**valid_data)
    assert instance


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
def test_invalid_data_model(converter, schema_fixture, model_name, invalid_data, request):
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
def sample_json_schema_list_dict():
    """Fixture for `List[Dict[str, Any]]`"""
    return ListDictModel.model_json_schema()


@pytest.fixture
def sample_json_schema_dict_list():
    """Fixture for `Dict[str, List[Any]]`"""
    return DictListModel.model_json_schema()


@pytest.fixture
def sample_json_schema_nested_list():
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
def test_json_schema_to_pydantic_nested(converter, schema_fixture, model_name, expected_fields, request):
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
def test_valid_data_model_nested(converter, schema_fixture, model_name, valid_data, request):
    """Test that valid data is accepted by the generated model."""
    schema = request.getfixturevalue(schema_fixture.__name__)
    Model = converter.json_schema_to_pydantic(schema, model_name)

    instance = Model(**valid_data)
    assert instance


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
def test_invalid_data_model_nested(converter, schema_fixture, model_name, invalid_data, request):
    """Test that invalid data raises ValidationError."""
    schema = request.getfixturevalue(schema_fixture.__name__)
    Model = converter.json_schema_to_pydantic(schema, model_name)

    with pytest.raises(ValidationError):
        Model(**invalid_data)
