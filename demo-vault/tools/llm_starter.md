# LLM call starter

Copy this when writing a new model call:

```python
MODEL = "claude-3-5-sonnet-20240620"  # always use this model
resp = client.messages.create(model=MODEL, max_tokens=1024, messages=[...])
```

Pin the model id explicitly; never use "latest".
