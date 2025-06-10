# 国土交通省交通量データMCPサーバー

国土交通省の交通量データAPI（日本道路交通情報センター提供）を利用して、交通量データを検索できるMCP（Model Context Protocol）サーバーです。

## 機能

- 条件を設定したデータの検索、取得

## 利用可能なツール
#### 1. get_traffic_flow

条件を指定して交通量データを検索、取得する

## 依存関係

pip install aiohttp mcp

## 使い方（自分の環境で動作した手順）

ローカルにクローンして使用する場合：

```bash
# リポジトリをクローン
git clone https://github.com/hrko9gis/JARTIC-open-traffic-mcp.git
cd JARTIC-open-traffic-mcp

# Python仮想環境を使用
uv venv
.venv\Scripts\activate
pip install aiohttp mcp
```

## Claude Desktop での使用

Claude Desktop でMCPサーバーを追加して利用することができます。

1. Claude Desktop で設定画面を開きます

2. このMCPサーバーを追加します
```json
{
    "mcpServers": {
        "JARTIC-open-traffic-mcp": {
            "command": "/Users/***/.local/bin/uv",
            "args": [
                "--directory",
                "＜JARTIC-open-traffic-mcp.pyが存在するディレクトリを絶対パスで指定＞"
                "run",
                "JARTIC-open-traffic-mcp.py"
            ]
        }
    }
}
```

3. 保存します

4. 接続します

## Claude Desktop での使用（自分の環境で動作した設定）
Claude Desktop でMCPサーバーを追加して利用することができます。

1. Claude Desktop で設定画面を開きます

2. このMCPサーバーを追加します
```json
{
    "mcpServers": {
        "JARTIC-open-traffic-mcp": {
            "command": "＜JARTIC-open-traffic-mcpのディレクトリを絶対パスで指定＞\\venv\\Scripts\\python.exe",
            "args": ["＜JARTIC-open-traffic-mcpのディレクトリを絶対パスで指定＞\\JARTIC-open-traffic-mcp.py"]
        }
    }
}
```

3. 保存します

4. 接続します

## ライセンス

MIT

## 出典の記載
このサービスは、交通量 API 機能を使用していますが、サービスの内容は国土交通省によって保証されたものではありません。

利用者は、本機能により取得した情報を用いたウェブサイトや資料等を公表する場合、交通量AIP利用規約の内容に従って出典等を記載してください。
交通量API利用規約
https://www.jartic-open-traffic.org/

## 謝辞

このプロジェクトは、国土交通省の交通量データAPI（日本道路交通情報センター提供）を利用しています。APIの提供に感謝いたします。
