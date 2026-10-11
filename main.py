import os

from arcadepy import Arcade
from dotenv import load_dotenv

load_dotenv()

client = Arcade()  # reads ARCADE_API_KEY from the environment
user_id = os.environ["ARCADE_USER_ID"]

# Sanity check: run a tool that needs no OAuth
result = client.tools.execute(
    tool_name="Math.Sqrt",
    input={"a": "625"},
    user_id=user_id,
)
print("Math.Sqrt(625) =", result.output.value)
