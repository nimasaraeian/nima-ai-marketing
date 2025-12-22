import sys
import asyncio

def main():
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    import uvicorn
    uvicorn.run("visual_trust_service.app:app", host="127.0.0.1", port=8011, reload=False)

if __name__ == "__main__":
    main()
















