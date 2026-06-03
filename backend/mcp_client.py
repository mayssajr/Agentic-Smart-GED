import asyncio
import concurrent.futures
import json
import logging
import os
import sys

from mcp              import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.getLogger("mcp.client.stdio").setLevel(logging.CRITICAL)


async def _async_call_stdio(server, tool_name: str, arguments: dict) -> str:
    if isinstance(server, dict):
        params = StdioServerParameters(
            command = server["command"],
            args    = server["args"],
            env     = {**os.environ.copy(), **server.get("env", {})},
        )
    else:
        params = StdioServerParameters(
            command = sys.executable,
            args    = [server],
            env     = os.environ.copy(),
        )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

            # DEBUG : log la réponse brute complète
            is_calendar = isinstance(server, dict) and "google_calendar" in str(
                server.get("args", ""))
            if is_calendar or tool_name in ("freebusy", "create_event", "list_events"):
                print(
                    f"[mcp_client/DEBUG] tool={tool_name} | "
                    f"content_len={len(result.content) if result.content else 0} | "
                    f"isError={getattr(result, 'isError', None)} | "
                    f"raw={str(result.content)[:200]}",
                    file=sys.stderr,
                )

            if not result.content:
                # Vérifier si c'est une erreur MCP
                if getattr(result, "isError", False):
                    print(f"[mcp_client] MCP error on {tool_name}: {result}",
                          file=sys.stderr)
                return ""

            first = result.content[0]

            # Log le type et contenu du premier élément
            if is_calendar or tool_name in ("freebusy", "create_event", "list_events"):
                print(
                    f"[mcp_client/DEBUG] first type={type(first).__name__} | "
                    f"text={getattr(first, 'text', '')[:150]}",
                    file=sys.stderr,
                )

            if hasattr(first, "text"):
                return first.text or ""
            if isinstance(first, str):
                return first
            return str(first)


async def _async_call_sse(server: dict, tool_name: str, arguments: dict) -> str:

    url     = server["url"]
    headers = server.get("headers", {})

    try:
        from mcp.client.streamable_http import streamablehttp_client
        async with streamablehttp_client(url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if not result.content:
                    return ""
                first = result.content[0]
                if hasattr(first, "text"):
                    return first.text or ""
                if isinstance(first, str):
                    return first
                return str(first)
    except Exception as exc:
        print(
            f"[mcp_client] streamablehttp_client failed ({type(exc).__name__}: {exc})"
            f" → essai sse_client",
            file=sys.stderr,
        )

    try:
        from mcp.client.sse import sse_client
        async with sse_client(url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if not result.content:
                    return ""
                first = result.content[0]
                if hasattr(first, "text"):
                    return first.text or ""
                if isinstance(first, str):
                    return first
                return str(first)
    except Exception as exc:
        print(
            f"[mcp_client] sse_client failed ({type(exc).__name__}: {exc})"
            f" → HTTP fallback",
            file=sys.stderr,
        )

    return await _http_fallback(server, tool_name, arguments)


async def _http_fallback(server: dict, tool_name: str, arguments: dict) -> str:
    import aiohttp
    url     = server["url"]
    headers = {
        "Content-Type": "application/json",
        "Accept":       "application/json, text/event-stream",
    }
    payload = {
        "jsonrpc": "2.0",
        "id":      "1",
        "method":  "tools/call",
        "params":  {"name": tool_name, "arguments": arguments},
    }
    print(f"[mcp_client] HTTP fallback → POST {url[:80]} | tool={tool_name}",
          file=sys.stderr)

    async with aiohttp.ClientSession() as http_session:
        async with http_session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(
                    f"HTTP {resp.status} | tool={tool_name} | response={body[:300]}")
            content_type = resp.headers.get("Content-Type", "")
            if "event-stream" in content_type:
                text = await resp.text()
                for line in text.split("\n"):
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data and data != "[DONE]":
                            try:
                                obj     = json.loads(data)
                                result  = obj.get("result", {})
                                content = result.get("content", [])
                                if content and isinstance(content, list):
                                    first = content[0]
                                    if isinstance(first, dict):
                                        return first.get("text", str(first))
                                    return str(first)
                            except json.JSONDecodeError:
                                continue
                return ""
            else:
                data    = await resp.json()
                if "error" in data:
                    err = data["error"]
                    raise RuntimeError(
                        f"JSON-RPC error {err.get('code')}: {err.get('message', str(err))}")
                result  = data.get("result", {})
                content = result.get("content", [])
                if content:
                    first = content[0]
                    if isinstance(first, dict):
                        return first.get("text", str(first))
                    return str(first)
                return str(result)


async def _async_call(server, tool_name: str, arguments: dict) -> str:
    is_sse = (
        isinstance(server, dict)
        and (server.get("type") == "sse" or "url" in server)
    )
    if is_sse:
        return await _async_call_sse(server, tool_name, arguments)
    else:
        return await _async_call_stdio(server, tool_name, arguments)


def call_mcp_tool(server, tool_name: str, arguments: dict) -> str:
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_call(server, tool_name, arguments))
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(run).result(timeout=60)