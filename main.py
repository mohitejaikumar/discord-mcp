import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.discord import DiscordProvider
from dotenv import load_dotenv

load_dotenv()

auth = DiscordProvider(
    client_id='1481244802073890889',
    client_secret='7TZ6eeATl5UXKB3eIJJw0ZLg9KJlfj7X',
    base_url='http://127.0.0.1:8000',
    required_scopes=["identify", "email", "guilds.join", "guilds"],
)


mcp = FastMCP('Discord MCP', auth=auth)


@mcp.tool
def add_number(a:int, b:int) -> int:
    """Add two number"""
    return 2*(a + b)

@mcp.tool
async def get_user_info() -> dict:
    """Returns information about the authenticated Discord user."""
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()
    print(token.claims.get("sub"))
    return {
        "discord_id": token.claims.get("sub"),
        "username": token.claims.get("username"),
        "avatar": token.claims.get("avatar"),
    }

def main():
    mcp.run(transport="streamable-http", port=8000)


