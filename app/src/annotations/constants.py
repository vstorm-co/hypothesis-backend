TEXT_SELECTOR_PROMPT_TEMPLATE = """Go through the text line by line and
{query}. Provide the exact text that its anchored, its suffix and prefix
and to and the annotation.
The annotation should be directly quoted as what we will feed API
for the intended target.
RULES:
- `exact` max few words that keep the context.
- `preffix` few chars right before the `exact`.
- `suffix` few chars right after the `exact`.
- `preffix` + `suffix` should be less than 64 characters.
- `annotation` should be directly quoted.
scraped data:
{scraped_data}
instructions:
{format_instructions}
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
User question: {question}
"""
