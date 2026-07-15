FROM python:3.11-slim

WORKDIR /app

# Install the package (and its deps) from the source tree.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8000

# Streamable HTTP MCP server, reachable from outside the container.
# Credentials come from the environment (see .env.example / docker-compose).
CMD ["shiplabel-mcp", "--http", "--host", "0.0.0.0", "--port", "8000"]
