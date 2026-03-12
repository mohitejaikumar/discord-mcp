import os
import httpx
from fastmcp import FastMCP
from fastmcp.server.auth.providers.discord import DiscordProvider
from fastmcp.server.dependencies import get_access_token
from dotenv import load_dotenv

load_dotenv()

DISCORD_API = "https://discord.com/api/v10"
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
APP_URL = os.getenv("APP_URL")

auth = DiscordProvider(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    base_url=APP_URL,
    required_scopes=["identify", "email", "guilds.join", "guilds", "guilds.members.read", "connections"],
)

mcp = FastMCP('Discord MCP', auth=auth)


# ── Helpers ──


async def discord_request(endpoint: str) -> dict | list:
    """Make authenticated requests using the user's OAuth token."""
    token = get_access_token()
    discord_token = token.token
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DISCORD_API}{endpoint}",
            headers={"Authorization": f"Bearer {discord_token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def bot_request(method: str, endpoint: str, json_data: dict | None = None) -> dict | list:
    """Make requests using the bot token."""
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            f"{DISCORD_API}{endpoint}",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
            json=json_data,
        )
        resp.raise_for_status()
        if resp.status_code == 204:
            return {"success": True}
        return resp.json()


# ── User OAuth tools ──


@mcp.tool
async def get_user_profile() -> dict:
    """Get the authenticated Discord user's full profile (id, username, email, avatar, banner, etc.)."""
    return await discord_request("/users/@me")


@mcp.tool
async def get_user_guilds() -> list[dict]:
    """List all Discord servers/guilds the authenticated user is a member of."""
    return await discord_request("/users/@me/guilds")


@mcp.tool
async def get_user_connections() -> list[dict]:
    """List the authenticated user's connected accounts (Twitch, GitHub, Spotify, etc.)."""
    return await discord_request("/users/@me/connections")


@mcp.tool
async def get_guild_member(guild_id: str) -> dict:
    """Get the authenticated user's membership info in a specific guild (nickname, roles, joined date)."""
    return await discord_request(f"/users/@me/guilds/{guild_id}/member")


# ── Server Information ──


@mcp.tool
async def get_server_info(guild_id: str) -> dict:
    """Get detailed Discord server information (name, icon, owner, member count, features, boosts, etc.)."""
    return await bot_request("GET", f"/guilds/{guild_id}?with_counts=true")


# ── User Management ──


@mcp.tool
async def get_user_id_by_name(guild_id: str, username: str) -> dict:
    """Get a Discord user's ID by username in a guild. Useful for pinging with <@id>."""
    members = await bot_request("GET", f"/guilds/{guild_id}/members?limit=1000")
    for member in members:
        user = member.get("user", {})
        if user.get("username") == username or member.get("nick") == username:
            return {"user_id": user["id"], "username": user["username"], "mention": f"<@{user['id']}>"}
    return {"error": f"User '{username}' not found in this guild"}


@mcp.tool
async def send_private_message(user_id: str, content: str) -> dict:
    """Send a private/DM message to a specific user."""
    dm_channel = await bot_request("POST", "/users/@me/channels", {"recipient_id": user_id})
    return await bot_request("POST", f"/channels/{dm_channel['id']}/messages", {"content": content})


@mcp.tool
async def edit_private_message(user_id: str, message_id: str, content: str) -> dict:
    """Edit a private message sent by the bot to a specific user."""
    dm_channel = await bot_request("POST", "/users/@me/channels", {"recipient_id": user_id})
    return await bot_request("PATCH", f"/channels/{dm_channel['id']}/messages/{message_id}", {"content": content})


@mcp.tool
async def delete_private_message(user_id: str, message_id: str) -> dict:
    """Delete a private message from a DM with a specific user."""
    dm_channel = await bot_request("POST", "/users/@me/channels", {"recipient_id": user_id})
    return await bot_request("DELETE", f"/channels/{dm_channel['id']}/messages/{message_id}")


@mcp.tool
async def read_private_messages(user_id: str, limit: int = 25) -> list[dict]:
    """Read recent message history from a DM with a specific user."""
    dm_channel = await bot_request("POST", "/users/@me/channels", {"recipient_id": user_id})
    return await bot_request("GET", f"/channels/{dm_channel['id']}/messages?limit={limit}")


# ── Message Management ──


@mcp.tool
async def send_message(channel_id: str, content: str) -> dict:
    """Send a message to a specific channel."""
    return await bot_request("POST", f"/channels/{channel_id}/messages", {"content": content})


@mcp.tool
async def edit_message(channel_id: str, message_id: str, content: str) -> dict:
    """Edit a message in a specific channel (bot must be the author)."""
    return await bot_request("PATCH", f"/channels/{channel_id}/messages/{message_id}", {"content": content})


@mcp.tool
async def delete_message(channel_id: str, message_id: str) -> dict:
    """Delete a message from a specific channel."""
    return await bot_request("DELETE", f"/channels/{channel_id}/messages/{message_id}")


@mcp.tool
async def read_messages(channel_id: str, limit: int = 25) -> list[dict]:
    """Read recent message history from a specific channel."""
    return await bot_request("GET", f"/channels/{channel_id}/messages?limit={limit}")


@mcp.tool
async def add_reaction(channel_id: str, message_id: str, emoji: str) -> dict:
    """Add a reaction (emoji) to a specific message. Use URL-encoded emoji (e.g. '%F0%9F%91%8D' for thumbs up, or 'name:id' for custom)."""
    return await bot_request("PUT", f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me")


@mcp.tool
async def remove_reaction(channel_id: str, message_id: str, emoji: str) -> dict:
    """Remove the bot's reaction (emoji) from a message."""
    return await bot_request("DELETE", f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me")


# ── Channel Management ──


@mcp.tool
async def create_text_channel(guild_id: str, name: str, parent_id: str | None = None) -> dict:
    """Create a text channel in a guild. Optionally place it under a category using parent_id."""
    data = {"name": name, "type": 0}
    if parent_id:
        data["parent_id"] = parent_id
    return await bot_request("POST", f"/guilds/{guild_id}/channels", data)


@mcp.tool
async def delete_channel(channel_id: str) -> dict:
    """Delete a channel permanently."""
    return await bot_request("DELETE", f"/channels/{channel_id}")


@mcp.tool
async def find_channel(guild_id: str, name: str) -> dict:
    """Find a channel by name in a guild. Returns channel type and ID."""
    channels = await bot_request("GET", f"/guilds/{guild_id}/channels")
    for ch in channels:
        if ch["name"] == name:
            return {"id": ch["id"], "name": ch["name"], "type": ch["type"]}
    return {"error": f"Channel '{name}' not found"}


@mcp.tool
async def list_channels(guild_id: str) -> list[dict]:
    """List all channels in a guild."""
    return await bot_request("GET", f"/guilds/{guild_id}/channels")


# ── Category Management ──


@mcp.tool
async def create_category(guild_id: str, name: str) -> dict:
    """Create a new category for channels in a guild."""
    return await bot_request("POST", f"/guilds/{guild_id}/channels", {"name": name, "type": 4})


@mcp.tool
async def delete_category(category_id: str) -> dict:
    """Delete a category. Channels inside it will become uncategorized."""
    return await bot_request("DELETE", f"/channels/{category_id}")


@mcp.tool
async def find_category(guild_id: str, name: str) -> dict:
    """Find a category ID by name in a guild."""
    channels = await bot_request("GET", f"/guilds/{guild_id}/channels")
    for ch in channels:
        if ch["type"] == 4 and ch["name"] == name:
            return {"id": ch["id"], "name": ch["name"]}
    return {"error": f"Category '{name}' not found"}


@mcp.tool
async def list_channels_in_category(guild_id: str, category_id: str) -> list[dict]:
    """List all channels in a specific category."""
    channels = await bot_request("GET", f"/guilds/{guild_id}/channels")
    return [ch for ch in channels if ch.get("parent_id") == category_id]


# ── Webhook Management ──


@mcp.tool
async def create_webhook(channel_id: str, name: str) -> dict:
    """Create a new webhook on a specific channel."""
    return await bot_request("POST", f"/channels/{channel_id}/webhooks", {"name": name})


@mcp.tool
async def delete_webhook(webhook_id: str) -> dict:
    """Delete a webhook."""
    return await bot_request("DELETE", f"/webhooks/{webhook_id}")


@mcp.tool
async def list_webhooks(channel_id: str) -> list[dict]:
    """List all webhooks on a specific channel."""
    return await bot_request("GET", f"/channels/{channel_id}/webhooks")


@mcp.tool
async def send_webhook_message(webhook_id: str, webhook_token: str, content: str, username: str | None = None) -> dict:
    """Send a message via webhook. No bot auth needed — uses webhook token."""
    data = {"content": content}
    if username:
        data["username"] = username
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISCORD_API}/webhooks/{webhook_id}/{webhook_token}?wait=true",
            json=data,
        )
        resp.raise_for_status()
        return resp.json()


# ── Role Management ──


@mcp.tool
async def list_roles(guild_id: str) -> list[dict]:
    """Get a list of all roles on the server with their details."""
    return await bot_request("GET", f"/guilds/{guild_id}/roles")


@mcp.tool
async def create_role(guild_id: str, name: str, color: int = 0, hoist: bool = False, mentionable: bool = False) -> dict:
    """Create a new role on the server. Color is an integer (e.g. 0xFF0000 for red)."""
    return await bot_request("POST", f"/guilds/{guild_id}/roles", {
        "name": name,
        "color": color,
        "hoist": hoist,
        "mentionable": mentionable,
    })


@mcp.tool
async def edit_role(guild_id: str, role_id: str, name: str | None = None, color: int | None = None, hoist: bool | None = None, mentionable: bool | None = None) -> dict:
    """Modify an existing role's settings. Only provided fields will be updated."""
    data = {}
    if name is not None:
        data["name"] = name
    if color is not None:
        data["color"] = color
    if hoist is not None:
        data["hoist"] = hoist
    if mentionable is not None:
        data["mentionable"] = mentionable
    return await bot_request("PATCH", f"/guilds/{guild_id}/roles/{role_id}", data)


@mcp.tool
async def delete_role(guild_id: str, role_id: str) -> dict:
    """Permanently delete a role from the server."""
    return await bot_request("DELETE", f"/guilds/{guild_id}/roles/{role_id}")


@mcp.tool
async def assign_role(guild_id: str, user_id: str, role_id: str) -> dict:
    """Assign a role to a user."""
    return await bot_request("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}")


@mcp.tool
async def remove_role(guild_id: str, user_id: str, role_id: str) -> dict:
    """Remove a role from a user."""
    return await bot_request("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}")


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8000)
