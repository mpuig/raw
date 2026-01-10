"""Tests for enhanced response parsing in @agentic decorator."""

from typing import Literal, Optional, Union

import pytest
from pydantic import BaseModel, Field

from raw_runtime.agentic_parser import (
    ResponseParsingError,
    extract_json,
    parse_bool,
    parse_dict,
    parse_float,
    parse_int,
    parse_list,
    parse_literal,
    parse_optional,
    parse_pydantic_model,
    parse_response,
    parse_union,
)


class TestExtractJson:
    """Tests for JSON extraction from responses."""

    def test_extract_from_json_code_block(self) -> None:
        """Test extracting JSON from ```json code block."""
        response = '```json\n{"key": "value"}\n```'
        result = extract_json(response)
        assert result == '{"key": "value"}'

    def test_extract_from_plain_code_block(self) -> None:
        """Test extracting JSON from ``` code block."""
        response = '```\n["a", "b", "c"]\n```'
        result = extract_json(response)
        assert result == '["a", "b", "c"]'

    def test_extract_from_text_with_braces(self) -> None:
        """Test extracting JSON object from text."""
        response = 'The result is: {"status": "ok", "count": 5}'
        result = extract_json(response)
        assert result == '{"status": "ok", "count": 5}'

    def test_extract_from_text_with_brackets(self) -> None:
        """Test extracting JSON array from text."""
        response = 'Here are the items: [1, 2, 3, 4]'
        result = extract_json(response)
        assert result == '[1, 2, 3, 4]'

    def test_extract_raw_json_object(self) -> None:
        """Test extracting raw JSON object."""
        response = '{"name": "John", "age": 30}'
        result = extract_json(response)
        assert result == '{"name": "John", "age": 30}'

    def test_extract_raw_json_array(self) -> None:
        """Test extracting raw JSON array."""
        response = '[1, 2, 3]'
        result = extract_json(response)
        assert result == '[1, 2, 3]'

    def test_no_json_returns_original(self) -> None:
        """Test that non-JSON returns original string."""
        response = 'Just plain text'
        result = extract_json(response)
        assert result == 'Just plain text'


class TestParseBool:
    """Tests for boolean parsing."""

    def test_parse_true_variants(self) -> None:
        """Test parsing various true representations."""
        assert parse_bool("true") is True
        assert parse_bool("True") is True
        assert parse_bool("TRUE") is True
        assert parse_bool("yes") is True
        assert parse_bool("Yes") is True
        assert parse_bool("1") is True
        assert parse_bool("y") is True
        assert parse_bool("Y") is True

    def test_parse_false_variants(self) -> None:
        """Test parsing various false representations."""
        assert parse_bool("false") is False
        assert parse_bool("False") is False
        assert parse_bool("FALSE") is False
        assert parse_bool("no") is False
        assert parse_bool("No") is False
        assert parse_bool("0") is False
        assert parse_bool("n") is False
        assert parse_bool("N") is False

    def test_parse_whitespace(self) -> None:
        """Test parsing with whitespace."""
        assert parse_bool("  true  ") is True
        assert parse_bool("\nfalse\n") is False

    def test_parse_ambiguous_raises(self) -> None:
        """Test that ambiguous values raise error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_bool("maybe")
        assert "Ambiguous boolean value" in str(exc_info.value)
        assert "suggestions" in str(exc_info.value).lower()

    def test_parse_empty_raises(self) -> None:
        """Test that empty string raises error."""
        with pytest.raises(ResponseParsingError):
            parse_bool("")


class TestParseInt:
    """Tests for integer parsing."""

    def test_parse_plain_int(self) -> None:
        """Test parsing plain integer."""
        assert parse_int("42") == 42
        assert parse_int("0") == 0
        assert parse_int("-5") == -5

    def test_parse_int_from_text(self) -> None:
        """Test extracting integer from text."""
        assert parse_int("The answer is 42") == 42
        assert parse_int("Count: 100 items") == 100
        assert parse_int("Temperature is -5 degrees") == -5

    def test_parse_whitespace(self) -> None:
        """Test parsing with whitespace."""
        assert parse_int("  42  ") == 42
        assert parse_int("\n100\n") == 100

    def test_parse_invalid_raises(self) -> None:
        """Test that invalid input raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_int("not a number")
        assert "No valid integer found" in str(exc_info.value)
        assert "suggestions" in str(exc_info.value).lower()

    def test_parse_float_as_int_extracts_first(self) -> None:
        """Test that float extracts integer part."""
        # Note: This extracts the first integer sequence
        assert parse_int("3.14") == 3


class TestParseFloat:
    """Tests for float parsing."""

    def test_parse_plain_float(self) -> None:
        """Test parsing plain float."""
        assert parse_float("3.14") == 3.14
        assert parse_float("0.5") == 0.5
        assert parse_float("-2.5") == -2.5

    def test_parse_scientific_notation(self) -> None:
        """Test parsing scientific notation."""
        assert parse_float("1.5e-10") == 1.5e-10
        assert parse_float("1E5") == 1e5
        assert parse_float("-2.5e3") == -2.5e3

    def test_parse_integer_as_float(self) -> None:
        """Test parsing integer as float."""
        assert parse_float("42") == 42.0
        assert parse_float("-5") == -5.0

    def test_parse_float_from_text(self) -> None:
        """Test extracting float from text."""
        assert parse_float("The value is 3.14") == 3.14
        assert parse_float("Temperature: -2.5 degrees") == -2.5

    def test_parse_whitespace(self) -> None:
        """Test parsing with whitespace."""
        assert parse_float("  3.14  ") == 3.14
        assert parse_float("\n-2.5\n") == -2.5

    def test_parse_invalid_raises(self) -> None:
        """Test that invalid input raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_float("not a number")
        assert "No valid float found" in str(exc_info.value)


class TestParseLiteral:
    """Tests for Literal type parsing."""

    def test_parse_exact_match(self) -> None:
        """Test parsing exact match."""
        result = parse_literal("high", Literal["critical", "high", "medium", "low"])
        assert result == "high"

    def test_parse_case_insensitive(self) -> None:
        """Test parsing with case insensitivity."""
        result = parse_literal("HIGH", Literal["critical", "high", "medium", "low"])
        assert result == "high"

    def test_parse_invalid_raises(self) -> None:
        """Test that invalid value raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_literal("invalid", Literal["critical", "high", "medium", "low"])
        assert "not in allowed values" in str(exc_info.value)
        assert "critical" in str(exc_info.value)
        assert "suggestions" in str(exc_info.value).lower()

    def test_parse_whitespace(self) -> None:
        """Test parsing with whitespace."""
        result = parse_literal("  high  ", Literal["critical", "high", "medium", "low"])
        assert result == "high"


class TestParsePydanticModel:
    """Tests for Pydantic model parsing."""

    def test_parse_simple_model(self) -> None:
        """Test parsing simple Pydantic model."""

        class User(BaseModel):
            name: str
            age: int

        result = parse_pydantic_model('{"name": "John", "age": 30}', User)
        assert isinstance(result, User)
        assert result.name == "John"
        assert result.age == 30

    def test_parse_from_code_block(self) -> None:
        """Test parsing from JSON code block."""

        class User(BaseModel):
            name: str
            age: int

        response = '```json\n{"name": "Jane", "age": 25}\n```'
        result = parse_pydantic_model(response, User)
        assert isinstance(result, User)
        assert result.name == "Jane"
        assert result.age == 25

    def test_parse_from_text(self) -> None:
        """Test parsing JSON from text."""

        class User(BaseModel):
            name: str

        response = 'The user data is: {"name": "Alice"}'
        result = parse_pydantic_model(response, User)
        assert result.name == "Alice"

    def test_parse_with_validation(self) -> None:
        """Test that Pydantic validation is enforced."""

        class User(BaseModel):
            name: str
            age: int = Field(ge=0, le=150)

        # Valid
        result = parse_pydantic_model('{"name": "John", "age": 30}', User)
        assert result.age == 30

        # Invalid - negative age
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_pydantic_model('{"name": "John", "age": -5}', User)
        assert "Validation failed" in str(exc_info.value)

    def test_parse_invalid_json_raises(self) -> None:
        """Test that invalid JSON raises error."""

        class User(BaseModel):
            name: str

        with pytest.raises(ResponseParsingError) as exc_info:
            parse_pydantic_model("not json", User)
        assert "Invalid JSON" in str(exc_info.value)
        assert "suggestions" in str(exc_info.value).lower()

    def test_parse_missing_field_raises(self) -> None:
        """Test that missing required field raises error."""

        class User(BaseModel):
            name: str
            age: int

        with pytest.raises(ResponseParsingError) as exc_info:
            parse_pydantic_model('{"name": "John"}', User)
        assert "Validation failed" in str(exc_info.value)


class TestParseList:
    """Tests for list parsing."""

    def test_parse_simple_list(self) -> None:
        """Test parsing simple list."""
        result = parse_list("[1, 2, 3]", list[int])
        assert result == [1, 2, 3]

    def test_parse_from_code_block(self) -> None:
        """Test parsing from code block."""
        response = '```json\n["a", "b", "c"]\n```'
        result = parse_list(response, list[str])
        assert result == ["a", "b", "c"]

    def test_parse_from_text(self) -> None:
        """Test parsing from text."""
        response = 'The items are: [1, 2, 3]'
        result = parse_list(response, list[int])
        assert result == [1, 2, 3]

    def test_parse_empty_list(self) -> None:
        """Test parsing empty list."""
        result = parse_list("[]", list)
        assert result == []

    def test_parse_invalid_json_raises(self) -> None:
        """Test that invalid JSON raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_list("not json", list)
        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_non_array_raises(self) -> None:
        """Test that non-array JSON raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_list('{"key": "value"}', list)
        assert "Expected array" in str(exc_info.value)


class TestParseDict:
    """Tests for dict parsing."""

    def test_parse_simple_dict(self) -> None:
        """Test parsing simple dict."""
        result = parse_dict('{"key": "value", "count": 5}', dict)
        assert result == {"key": "value", "count": 5}

    def test_parse_from_code_block(self) -> None:
        """Test parsing from code block."""
        response = '```json\n{"status": "ok"}\n```'
        result = parse_dict(response, dict)
        assert result == {"status": "ok"}

    def test_parse_from_text(self) -> None:
        """Test parsing from text."""
        response = 'The data is: {"name": "test"}'
        result = parse_dict(response, dict)
        assert result == {"name": "test"}

    def test_parse_empty_dict(self) -> None:
        """Test parsing empty dict."""
        result = parse_dict("{}", dict)
        assert result == {}

    def test_parse_invalid_json_raises(self) -> None:
        """Test that invalid JSON raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_dict("not json", dict)
        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_non_object_raises(self) -> None:
        """Test that non-object JSON raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_dict("[1, 2, 3]", dict)
        assert "Expected object" in str(exc_info.value)


class TestParseUnion:
    """Tests for Union type parsing."""

    def test_parse_first_matching_type(self) -> None:
        """Test that first matching type is used."""
        result = parse_union("42", Union[int, str])
        assert result == 42
        assert isinstance(result, int)

    def test_parse_fallback_to_second_type(self) -> None:
        """Test fallback to second type."""
        result = parse_union("not a number", Union[int, str])
        assert result == "not a number"
        assert isinstance(result, str)

    def test_parse_complex_union(self) -> None:
        """Test parsing complex union."""
        # Note: int parsing extracts first number from text, so list must come first
        result = parse_union("[1, 2, 3]", Union[list, int, str])
        assert result == [1, 2, 3]

    def test_parse_no_match_raises(self) -> None:
        """Test that no match raises error with all attempts."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_union("invalid", Union[int, float])
        assert "Could not parse as any union member" in str(exc_info.value)
        # Should show both types attempted
        error_str = str(exc_info.value)
        assert "int" in error_str
        assert "float" in error_str


class TestParseOptional:
    """Tests for Optional type parsing."""

    def test_parse_none_value(self) -> None:
        """Test parsing None values."""
        assert parse_optional("none", Optional[int]) is None
        assert parse_optional("null", Optional[int]) is None
        assert parse_optional("", Optional[int]) is None

    def test_parse_case_insensitive_none(self) -> None:
        """Test parsing None with different cases."""
        assert parse_optional("None", Optional[int]) is None
        assert parse_optional("NULL", Optional[int]) is None
        assert parse_optional("Null", Optional[int]) is None

    def test_parse_value(self) -> None:
        """Test parsing actual value."""
        result = parse_optional("42", Optional[int])
        assert result == 42

    def test_parse_complex_optional(self) -> None:
        """Test parsing optional complex type."""

        class User(BaseModel):
            name: str

        result = parse_optional('{"name": "John"}', Optional[User])
        assert isinstance(result, User)
        assert result.name == "John"


class TestParseResponse:
    """Integration tests for main parse_response function."""

    def test_parse_str(self) -> None:
        """Test parsing string response."""
        result = parse_response("hello world", str)
        assert result == "hello world"

    def test_parse_str_strips_whitespace(self) -> None:
        """Test that string parsing strips whitespace."""
        result = parse_response("  hello  ", str)
        assert result == "hello"

    def test_parse_int(self) -> None:
        """Test parsing integer response."""
        result = parse_response("42", int)
        assert result == 42

    def test_parse_int_from_text(self) -> None:
        """Test parsing integer from text."""
        result = parse_response("The answer is 42", int)
        assert result == 42

    def test_parse_float(self) -> None:
        """Test parsing float response."""
        result = parse_response("3.14", float)
        assert result == 3.14

    def test_parse_bool(self) -> None:
        """Test parsing boolean response."""
        assert parse_response("yes", bool) is True
        assert parse_response("no", bool) is False

    def test_parse_literal(self) -> None:
        """Test parsing Literal type."""
        result = parse_response("high", Literal["critical", "high", "medium", "low"])
        assert result == "high"

    def test_parse_pydantic_model(self) -> None:
        """Test parsing Pydantic model from JSON."""

        class Response(BaseModel):
            status: str
            count: int

        result = parse_response('{"status": "ok", "count": 5}', Response)
        assert isinstance(result, Response)
        assert result.status == "ok"
        assert result.count == 5

    def test_parse_pydantic_from_markdown(self) -> None:
        """Test parsing Pydantic model from markdown code block."""

        class User(BaseModel):
            name: str

        response = '```json\n{"name": "John"}\n```'
        result = parse_response(response, User)
        assert isinstance(result, User)
        assert result.name == "John"

    def test_parse_list(self) -> None:
        """Test parsing list from JSON."""
        result = parse_response('["a", "b", "c"]', list[str])
        assert result == ["a", "b", "c"]

    def test_parse_list_from_markdown(self) -> None:
        """Test parsing list from markdown."""
        result = parse_response("```json\n[1, 2, 3]\n```", list[int])
        assert result == [1, 2, 3]

    def test_parse_dict(self) -> None:
        """Test parsing dict from JSON."""
        result = parse_response('{"key": "value"}', dict)
        assert result == {"key": "value"}

    def test_parse_union(self) -> None:
        """Test parsing Union type."""
        result = parse_response("42", Union[int, str])
        assert result == 42
        assert isinstance(result, int)

    def test_parse_optional_none(self) -> None:
        """Test parsing Optional with None value."""
        result = parse_response("none", Optional[int])
        assert result is None

    def test_parse_optional_value(self) -> None:
        """Test parsing Optional with actual value."""
        result = parse_response("42", Optional[int])
        assert result == 42

    def test_parse_none_type(self) -> None:
        """Test parsing None type."""
        result = parse_response("anything", type(None))
        assert result is None

    def test_parse_empty_response_raises(self) -> None:
        """Test that empty response raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("", int)
        assert "Empty response" in str(exc_info.value)

    def test_parse_empty_response_none_type_ok(self) -> None:
        """Test that empty response is OK for None type."""
        result = parse_response("", type(None))
        assert result is None

    def test_parse_fallback_to_string(self) -> None:
        """Test that unknown types fallback to string."""

        class UnknownType:
            pass

        result = parse_response("some text", UnknownType)
        assert result == "some text"

    def test_error_includes_response_preview(self) -> None:
        """Test that error includes preview of response."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("not a number", int)
        assert "not a number" in str(exc_info.value)

    def test_error_includes_expected_type(self) -> None:
        """Test that error includes expected type."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("invalid", int)
        assert "int" in str(exc_info.value)

    def test_error_includes_suggestions(self) -> None:
        """Test that error includes helpful suggestions."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("maybe", bool)
        assert "suggestions" in str(exc_info.value).lower()


class TestErrorMessages:
    """Tests for error message quality."""

    def test_response_truncated_in_error(self) -> None:
        """Test that long responses are truncated in error message."""
        long_response = "x" * 1000

        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response(long_response, int)

        error_str = str(exc_info.value)
        # Should be truncated to 500 chars
        assert len([line for line in error_str.split('\n') if line.startswith('x')][0]) <= 500

    def test_error_shows_type_name(self) -> None:
        """Test that error shows readable type name."""

        class MyModel(BaseModel):
            value: int

        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("invalid json", MyModel)

        assert "MyModel" in str(exc_info.value)

    def test_error_shows_union_members(self) -> None:
        """Test that Union error shows all attempted types."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("invalid", Union[int, float, bool])

        error_str = str(exc_info.value)
        assert "int" in error_str
        assert "float" in error_str
        assert "bool" in error_str

    def test_optional_shown_as_optional(self) -> None:
        """Test that Optional[X] is shown nicely."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("invalid", Optional[int])

        error_str = str(exc_info.value)
        # Should try to parse as int first, show that error
        assert "int" in error_str


class TestEdgeCases:
    """Tests for edge cases and corner cases."""

    def test_parse_whitespace_only(self) -> None:
        """Test parsing whitespace-only response."""
        with pytest.raises(ResponseParsingError):
            parse_response("   \n  \t  ", int)

    def test_parse_with_unicode(self) -> None:
        """Test parsing with unicode characters."""
        result = parse_response("Hello 世界", str)
        assert result == "Hello 世界"

    def test_parse_nested_json(self) -> None:
        """Test parsing nested JSON structures."""

        class Inner(BaseModel):
            value: int

        class Outer(BaseModel):
            inner: Inner

        response = '{"inner": {"value": 42}}'
        result = parse_response(response, Outer)
        assert result.inner.value == 42

    def test_parse_json_with_extra_text(self) -> None:
        """Test parsing JSON with surrounding text."""
        response = "Here is the data: ```json\n{\"key\": \"value\"}\n```\nThank you!"
        result = parse_response(response, dict)
        assert result == {"key": "value"}

    def test_parse_multiple_json_blocks(self) -> None:
        """Test that first JSON block is used."""
        response = "```json\n{\"first\": 1}\n```\n```json\n{\"second\": 2}\n```"
        result = parse_response(response, dict)
        assert result == {"first": 1}
