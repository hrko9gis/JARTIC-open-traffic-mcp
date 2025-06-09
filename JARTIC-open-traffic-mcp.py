import os
import aiohttp
import asyncio
import json
import logging
import math
import csv
from io import StringIO
from typing import List, Dict
from datetime import datetime, timedelta

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

server = Server("JARTIC-open-traffic-mcp")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JARTIC_API_URL = "https://api.jartic-open-traffic.org/geoserver"
DEFAULT_TYPENAME = "t_travospublic_measure_5m"

def compute_bbox_from_center(lat: float, lon: float, radius_km: float) -> str:
    earth_radius = 6371.0
    delta_lat = (radius_km / earth_radius) * (180 / math.pi)
    delta_lon = (radius_km / earth_radius) * (180 / math.pi) / math.cos(math.radians(lat))
    lat_min = lat - delta_lat
    lat_max = lat + delta_lat
    lon_min = lon - delta_lon
    lon_max = lon + delta_lon
    return f"{lon_min},{lat_min},{lon_max},{lat_max}"

def convert_features_to_csv(features: List[Dict]) -> str:
    if not features:
        return ""
    output = StringIO()
    fieldnames = set()
    for feature in features:
        fieldnames.update(feature.get("properties", {}).keys())
    fieldnames = sorted(fieldnames)
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for feature in features:
        props = feature.get("properties", {})
        writer.writerow({key: props.get(key, "") for key in fieldnames})
    return output.getvalue()

@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="get_traffic_data",
            description="指定した条件で交通量データを取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "roadType": {"type": "string", "enum": ["1", "3"], "description": "道路種別コード（1: 高速道路, 3: 一般国道）"},
                    "startTime": {"type": "string", "format": "date-time", "description": "開始時刻（ISO8601形式）"},
                    "endTime": {"type": "string", "format": "date-time", "description": "終了時刻（ISO8601形式）"},
                    "bbox": {"type": "string", "description": "BBOX形式 例: 139.15,35.14,139.32,35.56"},
                    "centerLat": {"type": "number"},
                    "centerLon": {"type": "number"},
                    "radiusKm": {"type": "number"},
                    "pointCodes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "常時観測点コードのリスト",
                        "nullable": True
                    },
                    "outputFormat": {
                        "type": "string",
                        "enum": ["geojson", "csv"],
                        "default": "geojson"
                    }
                },
                "required": ["roadType", "startTime", "endTime"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    if name == "get_traffic_data":
        result = await get_traffic_data(**arguments)
        if isinstance(result, dict) and result.get("type") == "text/csv":
            return [TextContent(type="text", text=result["data"])]
        else:
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def get_traffic_data(
    roadType: str,
    startTime: str,
    endTime: str,
    bbox: str = None,
    centerLat: float = None,
    centerLon: float = None,
    radiusKm: float = None,
    pointCodes: List[str] = None,
    outputFormat: str = "geojson"
) -> Dict:
    headers = {"Accept": "application/json"}
    results = []

    try:
        start = datetime.fromisoformat(startTime)
        end = datetime.fromisoformat(endTime)
    except ValueError as e:
        return {"error": f"Invalid date format: {e}"}

    if bbox:
        final_bbox = bbox
    elif None not in (centerLat, centerLon, radiusKm):
        final_bbox = compute_bbox_from_center(centerLat, centerLon, radiusKm)
    else:
        return {"error": "bbox または centerLat + centerLon + radiusKm の指定が必要です"}

    async with aiohttp.ClientSession() as session:
        current = start
        while current <= end:
            time_code = current.strftime("%Y%m%d%H%M")

            filters = [
                f"道路種別='{roadType}'",
                f"時間コード={time_code}",
                f"BBOX(ジオメトリ,{final_bbox},'EPSG:4326')"
            ]

            if pointCodes:
                if len(pointCodes) == 1:
                    filters.append(f"常時観測点コード='{pointCodes[0]}'")
                else:
                    codes = ",".join([f"'{code}'" for code in pointCodes])
                    filters.append(f"常時観測点コード IN ({codes})")

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

    if outputFormat == "csv":
        return {"type": "text/csv", "data": convert_features_to_csv(results)}
    else:
        return {"type": "FeatureCollection", "features": results}

async def main():
    import sys
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (r, w):
        await server.run(
            r, w,
            InitializationOptions(
                server_name="JARTIC-open-traffic-mcp",
                server_version="1.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
