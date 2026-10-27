"""End-to-end MCP check: launch `doctopus mcp` as a subprocess and call its tools over stdio."""
import asyncio, json, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command="uv", args=["run", "--no-sync", "doctopus", "mcp", "--root", "fixtures"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("tools:", [t.name for t in tools.tools])
            res = await s.call_tool("explain_routing", {"path": "attention_2col.pdf"})
            print("explain:", res.content[0].text[:200])
            res = await s.call_tool("parse_document", {"path": "attention_2col.pdf", "max_chars": 200})
            d = json.loads(res.content[0].text)
            print("parse:", d["processing"]["backend"], d["total_chars"], "chars,", len(d["tables"]), "tables")
            res = await s.call_tool("chunk_document", {"path": "attention_2col.pdf", "limit": 2})
            d = json.loads(res.content[0].text)
            print("chunk:", d["total"], "chunks; first:", d["chunks"][0]["heading_path"], d["chunks"][1]["pages"])
            res = await s.call_tool("parse_document", {"path": "../pyproject.toml"})
            print("escape attempt:", res.content[0].text[:120])

asyncio.run(main())
