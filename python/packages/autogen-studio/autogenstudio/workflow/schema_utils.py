"""
Schema utilities for type handling and coercion in workflow components.
"""

from typing import Any, Dict, List, Type, Union
from pydantic import BaseModel


def extract_primary_type_from_schema(field_schema: Dict[str, Any]) -> str:
    """
    Extract the primary (non-null) type from a JSON schema field definition.
    
    Handles both direct type schemas and anyOf schemas (common for Optional types).
    
    Args:
        field_schema: JSON schema field definition
        
    Returns:
        Primary type as string (e.g., 'integer', 'string', 'object')
    """
    # Handle direct type
    if 'type' in field_schema:
        return field_schema['type']
    
    # Handle anyOf schemas (common for Optional types like Optional[int])
    if 'anyOf' in field_schema:
        # Find the first non-null type
        for type_option in field_schema['anyOf']:
            if isinstance(type_option, dict) and type_option.get('type') != 'null':
                return type_option.get('type', 'string')
    
    # Fallback to string
    return 'string'


def coerce_value_to_schema_type(value: Any, field_name: str, model_schema: Dict[str, Any]) -> Any:
    """
    Coerce a value to match the expected type based on a Pydantic model schema.
    
    This provides defensive type conversion to handle cases where values don't
    match the expected schema types (e.g., after serialization/deserialization).
    
    Args:
        value: The value to coerce
        field_name: Name of the field in the schema
        model_schema: The full Pydantic model JSON schema
        
    Returns:
        Coerced value that should match the schema expectations
    """
    if value is None:
        return value
        
    # Get field schema
    properties = model_schema.get('properties', {})
    field_schema = properties.get(field_name, {})
    
    if not field_schema:
        return value
    
    # Extract the target type
    target_type = extract_primary_type_from_schema(field_schema)
    
    # Perform type coercion based on target type
    try:
        if target_type == 'integer' and isinstance(value, (int, float, str)):
            if isinstance(value, str) and value.isdigit():
                return int(value)
            elif isinstance(value, (int, float)):
                return int(value)
                
        elif target_type == 'number' and isinstance(value, (int, float, str)):
            if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                return float(value)
            elif isinstance(value, (int, float)):
                return float(value)
                
        elif target_type == 'string' and not isinstance(value, str):
            return str(value)
            
        elif target_type == 'boolean':
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(value, (int, float)):
                return bool(value)
                
        elif target_type == 'object' and isinstance(value, dict):
            return value
            
        elif target_type == 'array' and isinstance(value, list):
            return value
            
    except (ValueError, TypeError):
        # If coercion fails, return original value
        pass
    
    # Return original value if no coercion needed/possible
    return value


def get_python_type_from_json_schema_type(json_type: str) -> Type:
    """
    Map JSON schema type strings to Python types.
    
    Args:
        json_type: JSON schema type string
        
    Returns:
        Corresponding Python type
    """
    type_map = {
        'string': str,
        'integer': int,
        'number': float,
        'boolean': bool,
        'array': List[Any],
        'object': Dict[str, Any]
    }
    
    return type_map.get(json_type, str)