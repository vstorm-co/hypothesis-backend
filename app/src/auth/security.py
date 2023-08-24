import string
from random import choice

import bcrypt


def hash_password(password: str) -> bytes:
    pw = bytes(password, "utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw, salt)


def check_password(password: str, password_in_db: bytes) -> bool:
    password_bytes = bytes(password, "utf-8")
    return bcrypt.checkpw(password_bytes, password_in_db)


# Generate a random N-character password
def generate_random_password(length=30):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = "".join(choice(characters) for _ in range(length))
    return password
