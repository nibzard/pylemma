FROM python:3.12-slim-bookworm
RUN pip install --no-cache-dir uv==0.10.0
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev
RUN useradd --create-home app
USER app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080
CMD ["uvicorn", "pylemma.web.app:hosted", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
