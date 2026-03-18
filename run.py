"""
Run the Abacus Game web server with automatic port selection.

If port 8000 is already in use, tries 8001, 8002, ... until a free port is found.
Prints the URL where the server is actually running.
Use: python run.py
Optional: python run.py --reload (for development auto-reload)
"""

import argparse
import socket
import sys


def find_available_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """
    Find the first available port starting from start_port.
    Returns the port number or raises RuntimeError if none found.
    """
    for attempt in range(max_attempts):
        port = start_port + attempt
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"No available port in range {start_port}..{start_port + max_attempts - 1}"
    )


def main() -> None:
    """Parse args, find port, run uvicorn."""
    parser = argparse.ArgumentParser(
        description="Run Abacus Game server with auto port selection"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )
    args = parser.parse_args()

    try:
        from app.config import settings
        start_port = settings.default_port
    except Exception:
        start_port = 8000

    port = find_available_port(start_port)
    if port != start_port:
        print(
            f"Порт {start_port} занят. Используется порт {port}.",
            file=sys.stderr,
        )

    print("")
    print(f"  Сервер запущен. Адрес:            http://127.0.0.1:{port}")
    print(f"  API документация (Swagger):       http://127.0.0.1:{port}/docs")
    print("")
    print("  Если при первом запуске создана демо-игра — выше будет сообщение:")
    print("  «Демо-игра создана! Логин: admin / admin»")
    print("  Перейдите в Игры → Демо-игра Абакус → Играть")
    print("")
    print("  Для остановки нажмите Ctrl+C.")
    print("")

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
