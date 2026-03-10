from fastapi import FastAPI

# Import config early to configure logging according to settings.debug
from app.core.config import settings
from app.api.v1.router import api_router

import logging

app = FastAPI(
    title="Athelix API",
    version="0.1.0",
    description="FastAPI application with SQLAlchemy"
)

app.include_router(api_router)

# Tune uvicorn loggers to match our debug setting (config.py already
# configured basic logging level) so we get consistent verbosity.
if settings.debug:
    logging.getLogger("uvicorn").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)


def main():
    """Run the ASGI app using uvicorn.

    Use the app object directly here instead of the string import path so
    running the file as a script (python app/main.py) still works.
    """
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)


if __name__ == "__main__":
    main()