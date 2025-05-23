"""
JARTIC Traffic Data MCP Server
国土交通省交通量データMCPサーバー
"""

import os
import aiohttp
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
import mcp.types as types

# JARTIC API設定
JARTIC_BASE_URL = "https://www.jartic-open-traffic.org/api/v1"

server = Server("JARTIC-TRAFFIC-mcp")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JarticAPIClient:
    """JARTIC API クライアント"""
    
    def __init__(self):
        self.base_url = JARTIC_BASE_URL
        
    async def make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        API リクエストを実行
        
        Args:
            endpoint: APIエンドポイント
            params: リクエストパラメータ
            
        Returns:
            APIレスポンスのJSONデータ
        """
        if params is None:
            params = {}
            
        headers = {
            "User-Agent": "JARTIC-MCP-Client/1.0",
            "Accept": "application/json"
        }
                    
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request error: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {"error": f"JSON decode error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    利用可能なツールのリストを返す
    """
    return [
        types.Tool(
            name="get_traffic_flow",
            description="指定地点・区間の交通量データを取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "location_id": {"type": "string", "description": "地点ID"},
                    "road_code": {"type": "string", "description": "道路コード"},
                    "date": {"type": "string", "description": "取得日付 (YYYY-MM-DD形式)"},
                    "time_range": {"type": "string", "description": "時間範囲 (hour/day/week/month)"}
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    ツール呼び出しのハンドラー
    """
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    try:
        result = ""
        
        if name == "get_traffic_flow":
            result = await get_traffic_flow(**arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        # 結果が文字列であることを確認
        if not isinstance(result, str):
            logger.warning(f"Result is not string, converting: {type(result)}")
            result = str(result)
        
        logger.info(f"Tool {name} completed successfully")
        return [types.TextContent(type="text", text=result)]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        error_msg = f"Error executing {name}: {str(e)}"
        return [types.TextContent(type="text", text=error_msg)]

async def get_traffic_flow(
    location_id: str = "",
    road_code: str = "",
    date: str = "",
    time_range: str = "hour"
) -> str:
    """交通量データを取得"""
    
    params = {}
    if location_id:
        params["location_id"] = location_id
    if road_code:
        params["road_code"] = road_code
    if date:
        params["date"] = date
    if time_range:
        params["time_range"] = time_range
    
    result = await jartic_client.make_request("traffic/flow", params)
    return json.dumps(result, ensure_ascii=False, indent=2)

async def main():
    """メイン関数"""
    try:
        # 方法1: stdio_server を使用
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, 
                write_stream, 
                InitializationOptions(
                    server_name="JARTIC-TRAFFIC-mcp",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )
    except ImportError:
        # 方法2: 直接的なstdio実装
        import sys
        from mcp.server import stdio
        
        await server.run_stdio()

if __name__ == "__main__":
    # イベントループを直接実行
    import asyncio
    asyncio.run(main())
