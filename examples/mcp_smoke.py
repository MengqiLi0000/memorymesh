"""Start the MCP server over stdio with an agent key and call its tools via the official MCP client."""
import asyncio, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "memory_mesh_mcp.server"], env={**os.environ})
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("tools:", [t.name for t in tools.tools])
            res = await s.call_tool("remember", {"content": "I prefer answers with concrete numbers."})
            print("remember ->", res.content[0].text[:120].replace("\n", " "))
            res = await s.call_tool("build_context", {"task": "Summarize the market. Make it more professional."})
            print("build_context ->\n" + res.content[0].text[:600])

asyncio.run(main())
