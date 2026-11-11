FROM python:3.15.2-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
# Use the base image's Python, so the venv copied to the final stage finds the same interpreter.
ENV UV_PYTHON_DOWNLOADS=0 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
# Dependencies first, so a source edit does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-editable
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.15.2-slim-trixie
RUN useradd --system --no-create-home app
WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY corpus ./corpus
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
CMD ["uvicorn", "pharmag.api:app", "--host", "0.0.0.0", "--port", "8000"]
