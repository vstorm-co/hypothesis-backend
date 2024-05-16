import json
from json import JSONDecodeError
from logging import getLogger
from typing import Any, Type

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.output_parsers.json import parse_json_markdown
from langchain_core.outputs import Generation
from pydantic import BaseModel, ValidationError

logger = getLogger(__name__)


class CustomPydanticOutputParser(PydanticOutputParser):
    """Parse an output using a pydantic model."""

    pydantic_object: Type[BaseModel]  # type: ignore
    """The pydantic model to parse.

    Attention: To avoid potential compatibility issues, it's recommended to use
        pydantic <2 or leverage the v1 namespace in pydantic >= 2.
    """

    @staticmethod
    def get_json_object(result: list[Generation], partial: bool = False) -> Any:
        text = result[0].text
        text = text.strip()

        if partial:
            try:
                return parse_json_markdown(text)
            except JSONDecodeError:
                return None
        else:
            try:
                return parse_json_markdown(text)
            except JSONDecodeError as e:
                msg = f"Invalid json output: {text}"
                logger.error("Failed to parse: %s", text)
                raise OutputParserException(msg, llm_output=text) from e

    def parse_result(self, result: list[Generation], *, partial: bool = False) -> Any:
        json_object = self.get_json_object(result, partial)
        try:
            return self.pydantic_object.model_validate(json_object)
        except ValidationError as e:
            name = self.pydantic_object.__name__
            logger.error("Failed to validate %s: %s", name, e)
            logger.error("json_object: %s", json_object)

            # return empty pydantic object
            return self.pydantic_object()

    def get_format_instructions(self) -> str:
        # Copy schema to avoid altering original Pydantic schema.
        schema = {k: v for k, v in self.pydantic_object.model_json_schema().items()}

        # Remove extraneous fields.
        reduced_schema = schema
        if "title" in reduced_schema:
            del reduced_schema["title"]
        if "type" in reduced_schema:
            del reduced_schema["type"]
        # Ensure json in context is well-formed with double quotes.
        schema_str = json.dumps(reduced_schema)

        return _PYDANTIC_FORMAT_INSTRUCTIONS.format(schema=schema_str)

    @property
    def _type(self) -> str:
        return "pydantic"

    @property
    def OutputType(self) -> Type[BaseModel]:  # type: ignore
        """Return the pydantic model."""
        return self.pydantic_object


_PYDANTIC_FORMAT_INSTRUCTIONS = """The output should be formatted as a JSON instance that conforms to the JSON schema below.

As an example, for the schema {{"properties": {{"foo": {{"title": "Foo", "description": "a list of strings", "type": "array", "items": {{"type": "string"}}}}}}, "required": ["foo"]}}
the object {{"foo": ["bar", "baz"]}} is a well-formatted instance of the schema. The object {{"properties": {{"foo": ["bar", "baz"]}}}} is not well-formatted.

Here is the output schema:
```
{schema}
```"""  # noqa: E501
