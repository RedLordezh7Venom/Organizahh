# OrganizAhh

OrganizAhh is a smart file organizer for Windows, powered by AI (Google Gemini) and a modern PyQt5 interface. It helps you analyze, categorize, and organize files in your folders with ease. You can use it with or without AI features.

Star this repo  ; ) to show your support and help me improve the project.
Also will be open later for open source contributions 

## Features
- Organize files by type or with AI-powered suggestions
- Clean, modern PyQt5 GUI
- Customizable organization structure (supports drag and drop)
- Save and reuse organization templates (backbone)
- Supports light/dark themes
- One-click folder opening
- Windows installer and portable modes

## Requirements
- Windows 10/11 (beta release, more coming up : ) )
- [Google Gemini API key](https://aistudio.google.com/apikey) 
- If running from source: Python 3.11+

## How to Run

### 1. Using the Windows Executable
1. Download and run the latest `OrganizAhhSetup.exe` from the [Releases](https://github.com/yourusername/OrganizAhh/releases) page.
2. During installation, you will be prompted to enter your Gemini API key (get it from [Google AI Studio](https://aistudio.google.com/apikey)).
3. Complete the installation and launch OrganizAhh from the Start Menu or desktop shortcut.
4. Use the GUI to select a folder, analyze, and organize your files!

### 2. Running from Source (app.py)
1. Install Python 3.9 or newer.
2. Clone or download this repository.
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the project directory with your Gemini API key:
   ```env
   GOOGLE_API_KEY=your-gemini-api-key-here
   ```
5. Run the app:
   ```sh
   python app.py
   ```

## Notes
- The app uses `logo.ico`, `logo_blue.ico`, and `logo_green.ico` for branding and status indication.
- AI features require a valid Gemini API key. You can use the app without AI, but advanced organization will be disabled.
- Offline AI mode is still in development (no Gemini mode). For now, you can use the app without an internet connection as well, but AI features won't work (basic organization).
- For best results, use the installer for a seamless experience.

## License
 Apache 2.0 + Commons Clause

For questions or support, open an issue on GitHub.
