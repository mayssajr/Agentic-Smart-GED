import json, sys, os
sys.path.insert(0, r"D:\poc_multi_agents_platform\backend")

from core.constants import MCP_LOCAL
from mcp_client import call_mcp_tool

print("=== Test 1 : get_documents ===")
raw = call_mcp_tool(MCP_LOCAL["miniged"], "get_documents", {"user_id": 1, "limit": 5})
docs = json.loads(raw)
print(json.dumps(docs, indent=2, ensure_ascii=False))

print("\n=== Test 2 : get_document (id=1) ===")
raw = call_mcp_tool(MCP_LOCAL["miniged"], "get_document", {"document_id": 1})
doc = json.loads(raw)
print(json.dumps(doc, indent=2, ensure_ascii=False))

print("\n=== Test 3 : get_file_status (id=1) ===")
raw = call_mcp_tool(MCP_LOCAL["miniged"], "get_file_status", {"document_id": 1})
status = json.loads(raw)
print(json.dumps(status, indent=2, ensure_ascii=False))

print("\n=== Test 4 : search_documents ===")
raw = call_mcp_tool(MCP_LOCAL["miniged"], "search_documents",
                    {"query": "contrat", "user_id": 1})
results = json.loads(raw)
print(json.dumps(results, indent=2, ensure_ascii=False))