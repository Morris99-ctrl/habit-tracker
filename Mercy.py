from openai import OpenAI

client = OpenAI()

question = input("You: ")

response = client.response.create(
    model = "gpt-5",
    input = question
)

print("AI:", response.output_text)

