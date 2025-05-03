import os
import sys
import subprocess
import platform
import time
import glob

def find_llamafile():
    """Find llamafile executable in the current directory"""
    # Look for files with .llamafile extension
    llamafiles = glob.glob("*.llamafile")
    
    if llamafiles:
        return llamafiles[0]
    
    # Also look for common model names that might be llamafiles without the extension
    potential_files = glob.glob("*mistral*") + glob.glob("*llama*") + glob.glob("*phi*")
    for file in potential_files:
        # Check if the file is executable
        if os.path.isfile(file) and os.access(file, os.X_OK):
            return file
    
    return None

def main():
    print("🦙 Llamafile Server Starter 🦙")
    print("------------------------------")
    
    # Find llamafile executable
    llamafile_path = find_llamafile()
    
    if not llamafile_path:
        print("❌ No llamafile executable found in the current directory.")
        print("Please download a llamafile from https://github.com/Mozilla-Ocho/llamafile/releases")
        print("and place it in the same directory as this script.")
        return
    
    print(f"✅ Found llamafile: {llamafile_path}")
    
    # Determine the command to run based on the platform
    if platform.system() == "Windows":
        cmd = [llamafile_path, "--server"]
    else:
        cmd = [f"./{llamafile_path}", "--server"]
    
    # Add optional port if provided
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
            cmd.extend(["--port", str(port)])
            print(f"🔌 Using custom port: {port}")
        except ValueError:
            print(f"⚠️ Invalid port number: {sys.argv[1]}. Using default port 8080.")
    
    print("\n📋 Starting Llamafile server with command:")
    print(" ".join(cmd))
    print("\n⏳ Server starting... (this may take a minute)")
    print("Press Ctrl+C to stop the server")
    
    try:
        # Start the server process
        process = subprocess.Popen(cmd)
        
        # Give the server some time to start
        time.sleep(5)
        
        print("\n✅ Server should be running now!")
        print("You can now run your lamba.py script in another terminal.")
        
        # Keep the server running until user interrupts
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        process.terminate()
        print("Server stopped.")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
