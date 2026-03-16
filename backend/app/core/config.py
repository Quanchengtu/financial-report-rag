import os
from dotenv import load_dotenv

load_dotenv()

SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "Quanchengtu; quanchengtu@gmail.com"
)