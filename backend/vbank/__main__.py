import uvicorn

from vbank.shared.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run("vbank.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()

