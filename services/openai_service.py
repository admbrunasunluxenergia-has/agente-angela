import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def interpret_message(text):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": text}]
    )
    return response.choices[0].message.content
