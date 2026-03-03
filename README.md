# FURIGANA-API

furigana api

## install

To install the required dependencies, run the following command:

```bash
uv sync
```

## Development

To run the development server, use the following command:

```bash
uv run uvicorn main:app --reload --port 8000
```

This will start the server on `http://127.0.0.1:8000` with hot-reloading enabled.

## API Test

You can test the API using the following `curl` command:

```bash
curl -X POST "http://127.0.0.1:8000/furigana" -H "Content-Type: application/json" -d '{"text": "食事をする"}'
```
