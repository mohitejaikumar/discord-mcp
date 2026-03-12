from fastmcp import Client
import asyncio

async def main():
    async with Client("http://localhost:8000/mcp", auth="oauth") as client:
        print("✓ Authenticated with Discord!")

        import json
        result = await client.call_tool("get_user_info")
        user_info = json.loads(result.content[0].text)
        
        print(f"Discord user: {user_info['username']}")

if __name__ == "__main__":
    asyncio.run(main())