from litert_tools.pipeline import pipeline
runner = pipeline.load("Gemma3-1B-IT_seq128_q8_ekv1280.task", repo_id="litert-community/Gemma3-1B-IT")

# Disclaimer: Model performance demonstrated with the Python API in this notebook is not representative of performance on a local device.
prompt = "Generate 20 file names?"
output = runner.generate(prompt)