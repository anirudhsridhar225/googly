
# backend for the genai google repo

instructions to operate the backend:

```py
1. uv sync
2. uv venv (check if there is already an env)
3. uv run uvicorn main:app --reload
```

# contribution

before contributing please make sure to execute `source .venv/bin/activate` so that your LSP picks up on function and type hints for fastapi etc.
and pls document whatever responses you will be returning :))