"""启动毛选思维引擎 Web 服务。
用法: python run_server.py [--port=8080] [--reload]
"""
import sys, os
from dotenv import load_dotenv
load_dotenv()
import uvicorn

def main():
    port = int(os.getenv("WEB_PORT", "8000"))
    reload = "--reload" in sys.argv
    for a in sys.argv:
        if a.startswith("--port="):
            port = int(a.split("=")[1])
    print(f"\n  📖 毛选思维引擎  http://localhost:{port}\n")
    uvicorn.run("web.app:app", host="0.0.0.0", port=port, reload=reload)

if __name__ == "__main__":
    main()
