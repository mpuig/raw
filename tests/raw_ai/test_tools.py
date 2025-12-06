"""Tests for raw_ai tool conversion utilities."""

from raw_ai.tools import (
    _extract_function_description,
    _extract_param_description,
    _type_to_json_schema,
    to_ai_tool,
)


class TestTypeToJsonSchema:
    """Tests for _type_to_json_schema."""

    def test_string_type(self) -> None:
        assert _type_to_json_schema(str) == {"type": "string"}

    def test_int_type(self) -> None:
        assert _type_to_json_schema(int) == {"type": "integer"}

    def test_float_type(self) -> None:
        assert _type_to_json_schema(float) == {"type": "number"}

    def test_bool_type(self) -> None:
        assert _type_to_json_schema(bool) == {"type": "boolean"}

    def test_list_type(self) -> None:
        result = _type_to_json_schema(list[str])
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_list_of_int(self) -> None:
        result = _type_to_json_schema(list[int])
        assert result == {"type": "array", "items": {"type": "integer"}}

    def test_dict_type(self) -> None:
        result = _type_to_json_schema(dict[str, int])
        assert result == {"type": "object"}

    def test_unknown_type_defaults_to_string(self) -> None:
        class CustomType:
            pass

        result = _type_to_json_schema(CustomType)
        assert result == {"type": "string"}


class TestExtractFunctionDescription:
    """Tests for _extract_function_description."""

    def test_simple_docstring(self) -> None:
        result = _extract_function_description("Get the current weather.")
        assert result == "Get the current weather."

    def test_multiline_description(self) -> None:
        docstring = """Get the current weather.

        This function fetches weather data.

        Args:
            city: The city name

        Returns:
            Weather data
        """
        result = _extract_function_description(docstring)
        assert "Get the current weather." in result
        assert "This function fetches weather data." in result

    def test_empty_docstring(self) -> None:
        result = _extract_function_description("")
        assert result == ""

    def test_stops_at_args(self) -> None:
        docstring = """Short description.

        Args:
            x: something
        """
        result = _extract_function_description(docstring)
        assert result == "Short description."


class TestExtractParamDescription:
    """Tests for _extract_param_description."""

    def test_extracts_param(self) -> None:
        docstring = """Get weather.

        Args:
            city: The city to get weather for
            units: Temperature units

        Returns:
            Weather data
        """
        result = _extract_param_description(docstring, "city")
        assert result == "The city to get weather for"

    def test_extracts_second_param(self) -> None:
        docstring = """Get weather.

        Args:
            city: The city to get weather for
            units: Temperature units
        """
        result = _extract_param_description(docstring, "units")
        assert result == "Temperature units"

    def test_missing_param_returns_default(self) -> None:
        docstring = """Get weather.

        Args:
            city: The city
        """
        result = _extract_param_description(docstring, "unknown")
        assert result == "Parameter unknown"

    def test_empty_docstring(self) -> None:
        result = _extract_param_description("", "param")
        assert result == "Parameter param"


class TestToAiTool:
    """Tests for to_ai_tool conversion."""

    def test_simple_function(self) -> None:
        def get_weather(city: str) -> str:
            """Get the weather for a city.

            Args:
                city: The city name

            Returns:
                Weather description
            """
            return f"Weather in {city}"

        tool = to_ai_tool(get_weather)

        assert tool["name"] == "get_weather"
        assert tool["description"] == "Get the weather for a city."
        assert tool["function"] is get_weather
        assert "parameters" in tool
        assert tool["parameters"]["properties"]["city"]["type"] == "string"
        assert "city" in tool["parameters"]["required"]

    def test_function_with_defaults(self) -> None:
        def search(query: str, limit: int = 10) -> list[str]:
            """Search for items.

            Args:
                query: Search query
                limit: Max results
            """
            return []

        tool = to_ai_tool(search)

        assert "query" in tool["parameters"]["required"]
        assert "limit" not in tool["parameters"]["required"]

    def test_function_multiple_types(self) -> None:
        def process(name: str, count: int, active: bool) -> dict:
            """Process data."""
            return {}

        tool = to_ai_tool(process)

        props = tool["parameters"]["properties"]
        assert props["name"]["type"] == "string"
        assert props["count"]["type"] == "integer"
        assert props["active"]["type"] == "boolean"

    def test_function_no_docstring(self) -> None:
        def simple(x: int) -> int:
            return x * 2

        tool = to_ai_tool(simple)

        assert tool["name"] == "simple"
        assert tool["description"] == "Call simple"
