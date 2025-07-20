import os
from transformers import AutoTokenizer, AutoModelForCausalLM
from optimum.onnxruntime import ORTModelForCausalLM
from onnxruntime_genai import Model, Tokenizer

# Set the HF_HOME environment variable to your desired cache directory
# This must be done BEFORE importing transformers

# Define the model name and ONNX export path
model_name = "HuggingFaceTB/SmolLM-135M"
onnx_model_path = "./onnx_model"

# Load tokenizer and model
tokenizer_hf = AutoTokenizer.from_pretrained(model_name)

# Export the model to ONNX format if not already exported
if not os.path.exists(onnx_model_path):
    print(f"Exporting {model_name} to ONNX at {onnx_model_path}...")
    ort_model = ORTModelForCausalLM.from_pretrained(model_name, export=True, local_dir=onnx_model_path)
    print("Model exported successfully.")
else:
    print(f"ONNX model already exists at {onnx_model_path}. Skipping export.")

# Load the ONNX model and tokenizer using onnxruntime-genai
print(f"Loading ONNX model from {onnx_model_path}...")
onnx_model = Model(onnx_model_path)
tokenizer_ort = Tokenizer(onnx_model)
print("ONNX model loaded successfully.")

# Generate a paragraph about mayonnaise
prompt = "Write a paragraph about mayonnaise."

# Encode the prompt using the onnxruntime-genai tokenizer
input_ids = tokenizer_ort.encode(prompt)

# Generate text using the onnxruntime-genai model
print("Generating text with ONNX Runtime GenAI...")
params = onnx_model.create_generate_parameters(input_ids)
params.max_length = 100
params.do_sample = True
params.temperature = 0.7
params.top_p = 0.9

output_ids = onnx_model.generate(params)
generated_text = tokenizer_ort.decode(output_ids)

print("\nGenerated Text:")
print(generated_text)
