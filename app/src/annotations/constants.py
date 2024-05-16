TEXT_SELECTOR_PROMPT_TEMPLATE = """We will provide a text below. Go through the entire
text line by line, reading carefully. Then, thinking about the prompt we are supplying,
craft a number of annotations, either a specific number of them if provided,
or an appropriate amount if not. The annotations returned will be in a JSON format
that follows the Hypothes.is implementation of the W3C Web Annotation data model
so that we can directly feed the JSON to the Hypothesis API. Based on the prompt
the annotations should be fixed to entire passages, sentences, phrases, words, or
possibly even characters, such that they anchor effectively to the text leveraging
the Hypothes.is fuzzy anchoring strategy.
That strategy uses a 30 byte prefix and 30 byte suffix along with a quote of
the actual text.  For the prefix and suffix, provide as many characters
as possible up to 30 to properly bookend the quote for each.
Don't make the exact quote longer than needed to deliver the asked annotation.
JSON RULES:
`selectors` is a list of annotation objects.
Each annotation object has the following
`exact` is the quote selection of the original content to anchor to. Required.
`prefix` up to 30 characters directly before the exact quote. Required.
`suffix` up to 30 chars directly after the exact. Required.
`annotation` is the text of the annotation. Required.
Response model: json with key "selectors" and its value as list of annotation objects.
Output format: Make sure the output is valid json markdown.
Instructions: {format_instructions}
The text to review.: {scraped_data}
Text to review tips###
- We are processing {split_index} out of {total}.
- If you can't find the annotations but there are next splits,
skip by returning empty json with key "selectors" and its value empty list [].
also if the number of annotations to create are described in the prompt
- be aware that you can find them in next splits.
- Sometimes the words are intertwined, try to detect these cases and return
them separately
###
And the prompt: {prompt}
"""
DOCUMENT_TITLE_PROMPT_TEMPLATE = """Get the title of the document
from the input.
RULES:
- Return only the title and nothing else.
- Title can't be longer than 50 characters.
Input: {input}",
"""
UNIQUE_TEXT_SELECTOR_PROMPT_TEMPLATE = """Create a unique text that will be
representative of the given selector.
Have in mind, the question on the basis of which it was created: {question}.
Rules:
- Return only the unique text.
- Max 5 words.
Examples:
```
#1
question: "Make 2 annotations that can help a student
think critically about this text"
selector: "The love that follows us sometimes is our trouble"
return: "love follows us"
```
Selector: {selector}
"""
NUM_OF_SELECTORS_PROMPT_TEMPLATE = """How many things does the user ask for?
Return only the number and nothing more.
If there is no specific number return None.
Number must be in decimal system.
Example 1:
question: Annotate 10 passages where...
response: 10
Example 2:
question: Annotate the text...
response: None
Example 3:
question: Mark three facts about...
response: 3
User question: {question}
"""
