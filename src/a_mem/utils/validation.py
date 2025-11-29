"""
Parameter validation utilities for A-MEM MCP tools.
"""
import re
from typing import Any, Dict, List, Optional, Tuple


def validate_uuid(uuid_str: str) -> bool:
    """Validates UUID format."""
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_str))


def validate_string(value: Any, min_length: int = 1, max_length: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """Validates string parameter."""
    if not isinstance(value, str):
        return False, f"Expected string, got {type(value).__name__}"
    if len(value) < min_length:
        return False, f"String too short (minimum: {min_length} characters)"
    if max_length and len(value) > max_length:
        return False, f"String too long (maximum: {max_length} characters)"
    return True, None


def validate_integer(value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """Validates integer parameter."""
    if not isinstance(value, (int, float)):
        return False, f"Expected number, got {type(value).__name__}"
    int_value = int(value)
    if min_value is not None and int_value < min_value:
        return False, f"Value too small (minimum: {min_value})"
    if max_value is not None and int_value > max_value:
        return False, f"Value too large (maximum: {max_value})"
    return True, None


def validate_float(value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """Validates float parameter."""
    if not isinstance(value, (int, float)):
        return False, f"Expected number, got {type(value).__name__}"
    float_value = float(value)
    if min_value is not None and float_value < min_value:
        return False, f"Value too small (minimum: {min_value})"
    if max_value is not None and float_value > max_value:
        return False, f"Value too large (maximum: {max_value})"
    return True, None


def validate_boolean(value: Any) -> Tuple[bool, Optional[str]]:
    """Validates boolean parameter."""
    if not isinstance(value, bool):
        return False, f"Expected boolean, got {type(value).__name__}"
    return True, None


def validate_note_id(note_id: Any) -> Tuple[bool, Optional[str]]:
    """Validates note ID (UUID format)."""
    if not isinstance(note_id, str):
        return False, f"Expected string, got {type(note_id).__name__}"
    if not validate_uuid(note_id):
        return False, f"Invalid UUID format: {note_id}"
    return True, None


def validate_relation_type(relation_type: Any) -> Tuple[bool, Optional[str]]:
    """Validates relation type."""
    if not isinstance(relation_type, str):
        return False, f"Expected string, got {type(relation_type).__name__}"
    valid_types = ["relates_to", "similar_to", "contradicts", "supports", "references", "depends_on"]
    if relation_type not in valid_types:
        return False, f"Invalid relation_type: {relation_type}. Valid types: {', '.join(valid_types)}"
    return True, None


def validate_weight(weight: Any) -> Tuple[bool, Optional[str]]:
    """Validates edge weight (0.0-1.0)."""
    if not isinstance(weight, (int, float)):
        return False, f"Expected number, got {type(weight).__name__}"
    weight_value = float(weight)
    if weight_value < 0.0 or weight_value > 1.0:
        return False, f"Weight must be between 0.0 and 1.0, got {weight_value}"
    return True, None


def validate_tool_parameters(tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
    """
    Validates parameters for a specific tool.
    
    Args:
        tool_name: Name of the tool
        arguments: Dictionary of arguments
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if tool_name == "create_atomic_note":
        # content: required string
        if "content" not in arguments:
            errors.append("'content' is required")
        elif not isinstance(arguments["content"], str):
            errors.append("'content' must be a string")
        elif len(arguments["content"].strip()) == 0:
            errors.append("'content' cannot be empty")
        
        # source: optional string
        if "source" in arguments and not isinstance(arguments["source"], str):
            errors.append("'source' must be a string")
    
    elif tool_name == "retrieve_memories":
        # query: required string
        if "query" not in arguments:
            errors.append("'query' is required")
        elif not isinstance(arguments["query"], str):
            errors.append("'query' must be a string")
        elif len(arguments["query"].strip()) == 0:
            errors.append("'query' cannot be empty")
        
        # max_results: optional integer (1-20)
        if "max_results" in arguments:
            is_valid, error = validate_integer(arguments["max_results"], min_value=1, max_value=20)
            if not is_valid:
                errors.append(f"'max_results': {error}")
    
    elif tool_name == "add_file":
        # file_path or file_content: at least one required
        if "file_path" not in arguments and "file_content" not in arguments:
            errors.append("Either 'file_path' or 'file_content' is required")
        
        # file_path: optional string
        if "file_path" in arguments and not isinstance(arguments["file_path"], str):
            errors.append("'file_path' must be a string")
        
        # file_content: optional string
        if "file_content" in arguments and not isinstance(arguments["file_content"], str):
            errors.append("'file_content' must be a string")
        
        # chunk_size: optional integer (1000-16384)
        if "chunk_size" in arguments:
            is_valid, error = validate_integer(arguments["chunk_size"], min_value=1000, max_value=16384)
            if not is_valid:
                errors.append(f"'chunk_size': {error}")
    
    elif tool_name == "get_note":
        # note_id: required UUID
        if "note_id" not in arguments:
            errors.append("'note_id' is required")
        else:
            is_valid, error = validate_note_id(arguments["note_id"])
            if not is_valid:
                errors.append(f"'note_id': {error}")
    
    elif tool_name == "update_note":
        # note_id: required UUID
        if "note_id" not in arguments:
            errors.append("'note_id' is required")
        else:
            is_valid, error = validate_note_id(arguments["note_id"])
            if not is_valid:
                errors.append(f"'note_id': {error}")
        
        # data: required object
        if "data" not in arguments:
            errors.append("'data' is required")
        elif not isinstance(arguments["data"], dict):
            errors.append("'data' must be an object")
    
    elif tool_name == "delete_atomic_note":
        # note_id: required UUID
        if "note_id" not in arguments:
            errors.append("'note_id' is required")
        else:
            is_valid, error = validate_note_id(arguments["note_id"])
            if not is_valid:
                errors.append(f"'note_id': {error}")
    
    elif tool_name == "list_relations":
        # note_id: optional UUID
        if "note_id" in arguments:
            is_valid, error = validate_note_id(arguments["note_id"])
            if not is_valid:
                errors.append(f"'note_id': {error}")
    
    elif tool_name == "add_relation":
        # source_id: required UUID
        if "source_id" not in arguments:
            errors.append("'source_id' is required")
        else:
            is_valid, error = validate_note_id(arguments["source_id"])
            if not is_valid:
                errors.append(f"'source_id': {error}")
        
        # target_id: required UUID
        if "target_id" not in arguments:
            errors.append("'target_id' is required")
        else:
            is_valid, error = validate_note_id(arguments["target_id"])
            if not is_valid:
                errors.append(f"'target_id': {error}")
        
        # relation_type: optional string (valid types)
        if "relation_type" in arguments:
            is_valid, error = validate_relation_type(arguments["relation_type"])
            if not is_valid:
                errors.append(f"'relation_type': {error}")
        
        # reasoning: optional string
        if "reasoning" in arguments and not isinstance(arguments["reasoning"], str):
            errors.append("'reasoning' must be a string")
        
        # weight: optional float (0.0-1.0)
        if "weight" in arguments:
            is_valid, error = validate_weight(arguments["weight"])
            if not is_valid:
                errors.append(f"'weight': {error}")
    
    elif tool_name == "remove_relation":
        # source_id: required UUID
        if "source_id" not in arguments:
            errors.append("'source_id' is required")
        else:
            is_valid, error = validate_note_id(arguments["source_id"])
            if not is_valid:
                errors.append(f"'source_id': {error}")
        
        # target_id: required UUID
        if "target_id" not in arguments:
            errors.append("'target_id' is required")
        else:
            is_valid, error = validate_note_id(arguments["target_id"])
            if not is_valid:
                errors.append(f"'target_id': {error}")
    
    elif tool_name == "get_graph":
        # save: optional boolean
        if "save" in arguments:
            is_valid, error = validate_boolean(arguments["save"])
            if not is_valid:
                errors.append(f"'save': {error}")
    
    elif tool_name == "research_and_store":
        # query: required string
        if "query" not in arguments:
            errors.append("'query' is required")
        elif not isinstance(arguments["query"], str):
            errors.append("'query' must be a string")
        elif len(arguments["query"].strip()) == 0:
            errors.append("'query' cannot be empty")
        
        # context: optional string
        if "context" in arguments and not isinstance(arguments["context"], str):
            errors.append("'context' must be a string")
        
        # max_sources: optional integer (1-20)
        if "max_sources" in arguments:
            is_valid, error = validate_integer(arguments["max_sources"], min_value=1, max_value=20)
            if not is_valid:
                errors.append(f"'max_sources': {error}")
    
    # Tools without parameters: get_memory_stats, reset_memory, list_notes
    # These don't need validation
    
    return len(errors) == 0, errors if errors else None

