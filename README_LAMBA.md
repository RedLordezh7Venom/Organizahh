# File Organization with LLM

This script uses a local LLM (via Llamafile) to organize files in a directory into a structured JSON format based on their names and types.

## Prerequisites

1. A running Llamafile server (see README_LLAMAFILE.md for setup instructions)
2. Required Python packages:
   ```
   pip install llama-index httpx
   ```

## Usage

Basic usage:

```bash
python lamba.py --directory "path/to/your/directory"
```

### Command Line Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--directory` | `-d` | "D:/Users/prabh/Downloads - Copy" | Directory to organize |
| `--timeout` | `-t` | 300 | Timeout in seconds for LLM request |
| `--url` | `-u` | "http://localhost:8080" | Base URL for Llamafile server |
| `--temperature` | | 0 | Temperature for LLM generation (0-1) |
| `--seed` | | 0 | Seed for LLM generation |
| `--output` | `-o` | None | Output file for JSON result |

### Examples

1. Organize files with a longer timeout:
   ```bash
   python lamba.py --directory "C:/Users/Documents" --timeout 600
   ```

2. Use a custom server URL:
   ```bash
   python lamba.py --url "http://localhost:8000"
   ```

3. Save the result to a file:
   ```bash
   python lamba.py --output "organization.json"
   ```

4. Combine multiple options:
   ```bash
   python lamba.py --directory "D:/Downloads" --timeout 500 --temperature 0.2 --output "result.json"
   ```

## Troubleshooting

### Timeout Errors

If you're getting timeout errors:

1. Increase the timeout value:
   ```bash
   python lamba.py --timeout 600
   ```

2. Reduce the number of files being processed (use a more specific directory)

3. Make sure your Llamafile server is running properly

### Connection Errors

If you can't connect to the server:

1. Make sure the Llamafile server is running
2. Check if the port is correct (default is 8080)
3. Try specifying the URL explicitly:
   ```bash
   python lamba.py --url "http://localhost:8080"
   ```

## Output Format

The script generates a JSON structure that organizes files into topics and subtopics:

```json
{
  "Topic_1": {
    "Subtopic_1": {
      "file1.txt": "document",
      "file2.pdf": "document"
    },
    "Subtopic_2": {
      "file3.zip": "archive"
    }
  },
  "Topic_2": {
    "Subtopic_1": {
      "file4.exe": "installer"
    }
  }
}
```

This structure can be used to automatically organize files into folders or to visualize the organization of your files.
