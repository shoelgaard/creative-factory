# gemini-image pricing (estimate fallback)

Google does not return cost in image-generation responses. Public pricing for
the image preview models is roughly:

| Model | $ per image | Notes |
|---|---:|---|
| gemini-3.1-flash-image-preview | ~$0.039 | 2K image with up to 3 ref images |

Replace with historic median from `logs/gemini-image.jsonl` once we have runs.
