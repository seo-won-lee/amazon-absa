import os
import json
import ast
import pandas as pd
from tqdm.auto import tqdm
import openai

client = openai.OpenAI(api_key = "OPENAI_API_KEY")

input_path = "C:/Users/PC/.../input.csv"
output_path = 'C:/Users/PC/.../output.csv'

df = pd.read_csv(input_path, usecols=['review'])

# Aspects list
aspects = [
    "design", "battery", "weight", "screen",
    "sound", "portability", "durability", "quality",
    "cable", "comfort", "usability", "price", "brand", "issue",
    "vibration", "accessory", "response", "connection",
    "delivery", "packaging", "smell", "compatibility",
    "defective", "size", "safe", "storage", "performance", "service",
    "functionality", "feedback", "temperature",
    "food", "household", "power", "capacity", "clean", "material"
]


# Built the prompt for multi-aspect sentiment analysis
def build_multi_aspect_sentiment_prompt(review_text, aspect_list):
    aspect_str = ', '.join(f'"{a}"' for a in aspect_list)
    return [
        {
            "role": "system",
            "content": (
                "You are an AI assistant that analyzes a product review to check if it mentions each of several given aspects, "
                "and if mentioned, determine the sentiment towards each aspect.\n"
                "Answer in JSON format like this:\n"
                "[{'aspect': 'battery', 'mention': 'Yes', 'sentiment': 'Positive'}, {...}, ...]\n"
                "If the aspect is not mentioned, set 'mention' to 'No' and omit the sentiment field."
            )
        },
        {
            "role": "user",
            "content": f"""Review:
\"{review_text}\"

Aspects to check: {aspect_str}

For each aspect, answer in the JSON format:
[{{'aspect': '...', 'mention': 'Yes' or 'No', 'sentiment': 'Positive'/'Negative'/'Neutral'}}]

Answer:"""
        }
    ]


# Predict sentiment for multiple aspects using GPT
tqdm.pandas()
def predict_multi_aspect_sentiment_gpt(review, aspect_list):
    messages = build_multi_aspect_sentiment_prompt(review, aspect_list)
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,
            max_tokens=600,
            timeout=30
        )
        output_text = response.choices[0].message.content.strip()

        try:
            results = json.loads(output_text.replace("'", '"'))
            filtered = [
                {'aspect': r['aspect'], 'sentiment': r.get('sentiment', 'Neutral')}
                for r in results
                if r.get('mention', '').lower() == 'yes'
            ]
            return filtered
        except Exception as e:
            print(f"JSON parsing failed:\n{output_text}\n▶ {e}")
            return []
    except Exception as e:
        print(f"GPT error (review: {review[:30]}...)\n▶ {e}")
        return []


def safe_eval(x):
    if isinstance(x, str):
        try:
            return ast.literal_eval(x)
        except Exception:
            return None
    else:
        return x


if os.path.exists(output_path):
    df_sample = pd.read_csv(output_path)
    df_sample["predicted_aspects_sentiments"] = df_sample["predicted_aspects_sentiments"].apply(safe_eval)
    start_index = df_sample["predicted_aspects_sentiments"].notnull().sum()
    print(f"Continuing from index {start_index}")
else:
    df_sample = df.copy()
    df_sample["predicted_aspects_sentiments"] = [None] * len(df_sample)
    start_index = 0

for i in tqdm(df_sample.index[start_index:], desc="Processing reviews"):
    row = df_sample.iloc[i]
    review = row["review"]
    try:
        pred = predict_multi_aspect_sentiment_gpt(review, aspects)
        df_sample.at[i, "predicted_aspects_sentiments"] = pred
    except Exception as e:
        print(f"[Prediction failed]: review {i} → {e}")
        df_sample.at[i, "predicted_aspects_sentiments"] = []

    if i % 10 == 0:
        df_sample.to_csv(output_path, index=False)
        print(f"Saved up to index {i}")

df_sample.to_csv(output_path, index=False)
print("Final save completed")
