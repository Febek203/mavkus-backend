#!/usr/bin/env python
"""
MAVKUS AI - Entry Point
"""
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MAVKUS AI Server - Versione 3.0")
    print("=" * 60)
    print("📡 API disponibile su: http://localhost:8000")
    print("📚 Documentazione: http://localhost:8000/docs")
    print("=" * 60)
    
    # Su Windows, usa reload=False
    import sys
    use_reload = "--reload" in sys.argv and sys.platform != "win32"
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=use_reload,
        log_level="info"
    )