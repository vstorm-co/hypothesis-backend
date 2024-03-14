text_selector_prompt_template = """Annotate the data by provided query
query: {query}
IMPORTANT:
- `exact` max few words that keep the context.
- `preffix` few chars right before the `exact`.
- `suffix` few chars right after the `exact`.
- `preffix` + `suffix` should be less than 64 characters.
scraped data:
{scraped_data}
instructions:
{format_instructions}
"""
