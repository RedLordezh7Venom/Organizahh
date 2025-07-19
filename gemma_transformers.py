import os

# Set the HF_HOME environment variable to your desired cache directory
# This must be done BEFORE importing transformers

# Load model directly
from transformers import AutoProcessor, AutoModelForImageTextToText

processor = AutoProcessor.from_pretrained("google/gemma-3n-E4B")
model = AutoModelForImageTextToText.from_pretrained("google/gemma-3n-E4B")

# Generate a paragraph about mayonnaise
prompt = "Write a paragraph about mayonnaise."
# For ImageTextToText models, you typically need an image input.
# Since the request is for text generation, we'll try to use the processor for text only.
# If this model requires an image, the script might fail or produce unexpected results.
inputs = processor(text=prompt, return_tensors="pt")

outputs = model.generate(**inputs, max_new_tokens=100)
generated_text = processor.decode(outputs[0], skip_special_tokens=True)

print(generated_text)
