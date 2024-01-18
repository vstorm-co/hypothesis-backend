from src.chat.schemas import MessageDBWithTokenUsage


def get_room_elapsed_time_by_messages(
    messages_schema: list[MessageDBWithTokenUsage],
) -> dict:
    elapsed_time: float = 0.0
    for index, message in enumerate(messages_schema):
        if isinstance(message.elapsed_time, float):
            elapsed_time += message.elapsed_time

    return {
        "elapsed_time": elapsed_time,
    }
