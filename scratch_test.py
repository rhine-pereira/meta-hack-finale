import os
import sys
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Parameters to start the server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "server.app"],
        env=os.environ.copy()
    )

    print("Starting GENESIS MCP Server smoke test...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print(f"Registered tools: {[t.name for t in tools.tools]}")
            
            episode_id = "smoke_test_1"
            
            # 1. Reset
            print("\nTesting 'reset'...")
            res = await session.call_tool("reset", {"episode_id": episode_id, "difficulty": 2})
            print(f"Reset response: {res.content[0].text}")
            
            # 2. Daily Briefing (as CEO)
            print("\nTesting 'get_daily_briefing' (CEO)...")
            res = await session.call_tool("get_daily_briefing", {"episode_id": episode_id, "agent_role": "ceo"})
            print(f"Briefing response: {res.content[0].text[:200]}...")
            
            # 3. Build Feature (as CTO)
            print("\nTesting 'build_feature' (CTO)...")
            res = await session.call_tool("build_feature", {
                "episode_id": episode_id, 
                "agent_role": "cto", 
                "name": "Cloud Scaling", 
                "complexity": "medium", 
                "engineers": 2
            })
            print(f"Build Feature response: {res.content[0].text}")
            
            # 4. Unauthorized Check
            print("\nTesting unauthorized 'build_feature' (CEO)...")
            res = await session.call_tool("build_feature", {
                "episode_id": episode_id, 
                "agent_role": "ceo", 
                "name": "Secret Feature", 
                "complexity": "low", 
                "engineers": 1
            })
            print(f"Unauthorized response: {res.content[0].text}")

            print("\nSmoke test passed!")

if __name__ == "__main__":
    asyncio.run(main())
