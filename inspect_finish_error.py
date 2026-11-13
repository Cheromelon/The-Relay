
import json

path = "data/real_raw.jsonl"

with open(path, encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)

        if record.get("scenario") == "real_finish_check":
            print("\nRequest ID:", record.get("request_id"))
            print("Status:", record.get("status"))
            print("Error:", record.get("error"))
            print("First token:", record.get("first_token_ms"))
            print("Total time:", record.get("total_ms"))
            print("Input tokens:", record.get("tokens_in"))
            print("Output tokens:", record.get("tokens_out"))
