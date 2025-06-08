"""
JARTIC Traffic Data MCP Server
国土交通省交通量データMCPサーバー
"""
import os
import aiohttp
import asyncio
import json
import logging
from typing import List, Dict

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

from datetime import datetime, timedelta

server = Server("JARTIC-open-traffic-mcp")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JARTIC_API_URL = "https://api.jartic-open-traffic.org/geoserver"
DEFAULT_TYPENAME = "t_travospublic_measure_5m"

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """
    利用可能なツールのリストを返す
    """
    return [
        Tool(
            name="get_traffic_data",
            description="指定した時間範囲・観測点・範囲から交通量データを取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "roadType": {"type": "string", "enum": ["1", "3"]},
                    "startTime": {"type": "string", "format": "date-time"},
                    "endTime": {"type": "string", "format": "date-time"},
                    "bbox": {"type": "string", "description": "BBOX形式 139.15,35.14,139.32,35.56"},
                    "pointCode": {"type": "string", "description": "常時観測点コード", "nullable": True}
                },
                "required": ["roadType", "startTime", "endTime", "bbox"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """
    ツール呼び出しのハンドラー
    """
    logger.info(f"Tool called: {name} with arguments: {arguments}")

    try:
        if name == "get_traffic_data":
            result = await get_traffic_data(**arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

async def get_traffic_data(
    roadType: str,
    startTime: str,
    endTime: str,
    bbox: str,
    pointCode: str = None
) -> Dict:
    headers = {"Accept": "application/json"}
    results = []

    try:
        start = datetime.fromisoformat(startTime)
        end = datetime.fromisoformat(endTime)
    except ValueError as e:
        return {"error": f"Invalid date format: {e}"}

    async with aiohttp.ClientSession() as session:
        current = start
        while current <= end:
            time_code = current.strftime("%Y%m%d%H%M")

            filters = [
                f"道路種別='{roadType}'",
                f"時間コード={time_code}",
                f"BBOX(ジオメトリ,{bbox},'EPSG:4326')"
            ]
            if pointCode:
                filters.append(f"常時観測点コード='{pointCode}'")

            params = {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": DEFAULT_TYPENAME,
                "srsName": "EPSG:4326",
                "outputFormat": "application/json",
                "cql_filter": " AND ".join(filters)
            }

            try:
                async with session.get(JARTIC_API_URL, params=params, headers=headers) as response:
                    data = await response.json()
                    results.extend(data.get("features", []))
            except Exception as e:
                logger.error(f"Error fetching {time_code}: {e}")

            current += timedelta(minutes=5)

    return {
        "type": "FeatureCollection",
        "features": results
    }

async def main():
    import sys
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (r, w):
        await server.run(
            r, w,
            InitializationOptions(
                server_name="JARTIC-open-traffic-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
