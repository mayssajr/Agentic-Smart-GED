from mcp_client import call_mcp_tool
from core.constants import MCP_SPECS
result = call_mcp_tool(MCP_SPECS['google_calendar'], 'create-event', {
    'calendarId': 'primary',
    'summary': 'Test Entretien',
    'start': '2026-05-09T10:00:00',
    'end':   '2026-05-09T11:00:00',
    'attendees': [{'email': 'mayssa.jarray@isimg.tn'}],
    'sendUpdates': 'all',
})
print('RESULT:', result[:300])