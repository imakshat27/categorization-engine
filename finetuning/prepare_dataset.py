import json

input_file = "training_reviews.jsonl"
output_file = "train.jsonl"

formatted = []

with open(input_file, "r") as f:
    for line in f:
        row = json.loads(line)

        prompt = f"""Bank: {row['bank']}
Direction: {row['direction']}
Narration: {row['narration']}
Predicted Category: {row['predicted_category']}
Confidence: {row['confidence']}

What should be the correct category?"""

        formatted.append({
            "prompt": prompt,
            "completion": row["correct_category"]
        })

with open(output_file, "w") as f:
    for item in formatted:
        f.write(json.dumps(item) + "\n")

print("Dataset prepared.")