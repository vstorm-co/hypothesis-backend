from databases.interfaces import Record
from sqlalchemy import insert, select, update

from src.chat.constants import MODEL_NAME
from src.chat.schemas import MessageDetails
from src.database import TokenUsage, database
from src.token_usage.constants import token_prices
from src.token_usage.schemas import TokenUsageInput
from src.tokenizer.tiktoken import count_message_tokens


async def create_token_usage_in_db(token_usage_data: TokenUsageInput) -> Record | None:
    insert_values = {
        **token_usage_data.model_dump(),
    }

    insert_query = insert(TokenUsage).values(**insert_values).returning(TokenUsage)
    token_usage = await database.fetch_one(insert_query)

    return token_usage


def get_token_usage_input_from_message(message: MessageDetails) -> TokenUsageInput:
    token_counts: int = count_message_tokens(message)
    token_usage_type = "prompt" if message.created_by == "user" else "completion"
    model_name = MODEL_NAME
    price_per_token = token_prices[model_name][token_usage_type]
    divider = token_prices[model_name]["divider"]
    token_usage_value = (token_counts / divider) * price_per_token

    return TokenUsageInput(
        type=token_usage_type,
        count=token_counts,
        value=token_usage_value,
    )


async def get_token_usage_by_id(token_usage_id: int) -> Record | None:
    select_query = select(TokenUsage).where(TokenUsage.id == token_usage_id)

    return await database.fetch_one(select_query)


async def update_token_usage_in_db(
    token_id: int, token_usage_data: TokenUsageInput
) -> Record | None:
    update_query = (
        update(TokenUsage)
        .where(TokenUsage.id == token_id)
        .values(**token_usage_data.model_dump())
        .returning(TokenUsage)
    )

    return await database.fetch_one(update_query)
