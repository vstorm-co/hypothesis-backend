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

        logger.info("text: %s", text)
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


if __name__ == "__main__":
    x = """```json
    {
      "selectors": [
        {
          "exact": "Ang dahilan nang pagsulat nitong libro,i, diliibakun diangmaka abuloy nang pagpapakalat nang mahalagang \vika nang Ingles nangayo,i, lumalatag salialos lahat nang manga naciones; kayaangnasanang sumulat ayangtumulonghindi lamang samanga Americano atIngles namay pitang matuto nang wicang Tagalog kundi lalonglalo nasamanga maginoong taga ritosaFilipinas nangayo,i, nagsusumikap sapagaaral nang \vikang Ingles.",
          "prefix": "PAUNAWA ",
          "suffix": "Pinagpilitan sapamamagitan nang masiyasatatmasinip napaghahalunkat ang pagtitipon nang lahat nangmanga matatanda atmanga batangsalita at wikang Tagalog sampo nangmanga kahulugan nang bawat isaupang mai- frnlog sawikang Inglesatgayon dinnaman angwikangitosaTagalog at gayondin naman pinihit angibinigaysabawatisang\vika sapaghuhulog ang halaga atkahulugan saiba atgayon dinnamanangmanga tinatauag na Frances baga, aypinilit angmag'-aroon nang tunay nakahulugan sakaniyang tunay nahalaga saiba.",
          "annotation": "The author explains the purpose of writing this book, which is to help spread the English language, which is becoming widespread among nations. The author aims to assist not only Americans and English people who want to learn Tagalog but also Filipinos who are striving to learn English."
        },
        {
          "exact": "The author'sobjectincompiling andpublishingthis book istoputbefore thepublicawork that will aid both theAmerican and theFilipinoinlearningeither English orTagalog whichever thecasemightbe.",
          "prefix": "PREFACE ",
          "suffix": "Ithastaken about three yearstocompileitand each word hasbeen thoroughly tested sothat the definitions willbefound correct.",
          "annotation": "The author states that the objective of compiling and publishing this book is to provide a resource that will help both Americans and Filipinos in learning either English or Tagalog."
        },
        {
          "exact": "Ithastaken about three yearstocompileitand each word hasbeen thoroughly tested sothat the definitions willbefound correct.",
          "prefix": "The author'sobjectincompiling andpublishingthis book istoputbefore thepublicawork that will aid both theAmerican and theFilipinoinlearningeither English orTagalog whichever thecasemightbe. ",
          "suffix": "Itiswritten inwhat iscalled theNew Tagalog which differs from the old inthefollowing respects.",
          "annotation": "The author mentions that it took about three years to compile the book and that each word has been thoroughly tested to ensure the accuracy of the definitions."
        },
        {
          "exact": "TheGhasbecome K,Guihasbeen shortened togi;qui hasbeenchangedtoKiandwisgenerally substituted forU.Therefore should aperson look foraword that begins withCand fail tofind itheshould turn toK; should, hebeunable tofindQuiIn*should turn toKi; and incase ofulieshould turn to \v.",
          "prefix": "Itiswritten inwhat iscalled theNew Tagalog which differs from the old inthefollowing respects. ",
          "suffix": "Angkaraniwang tunog ngdalawang letrang ohayparang tsh,kung na- sasaina sa salita. Tangi lamang angmanga sumusunod: Machine, Chagrin, Chivalry, Mustache, atChaise; ang sauanilo aylutunog nang ]>arangsh.",
          "annotation": "The author explains the changes in the New Tagalog orthography, where 'G' has become 'K', 'Gui' has been shortened to 'gi', 'qui' has been changed to 'Ki', and 'w' is generally substituted for 'U'."
        },
        {
          "exact": "1.Thevowels have butonesound. The a-ah, the e-a;the i-e; o-o;and u-u.",
          "prefix": "Rules forpronouncing Tagalog. ",
          "suffix": "2.When thengiswritten with awave over thenitliasthesound ofngin theterminationang,while without thewave itispronouncedas tisspelled",
          "annotation": "The first rule for pronouncing Tagalog vowels is that each vowel has only one sound: 'a' as in 'ah', 'e' as in 'a', 'i' as in 'e', 'o' as in 'o', and 'u' as in 'u'."
        }
      ]
    }
    ```"""  # noqa: E501
    res = parse_json_markdown(x)

    qa = 10
