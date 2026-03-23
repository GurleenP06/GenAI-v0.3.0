"""Entry point for running OSKAR via `python -m oskar`."""

import uvicorn


def main():
    uvicorn.run("oskar.api.app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
