; filepath: installer.iss
[Setup]
AppName=OrganizAhh
AppVersion=1.0
DefaultDirName={pf}\OrganizAhh
DefaultGroupName=OrganizAhh
OutputDir=dist
OutputBaseFilename=OrganizAhhSetup
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\app.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
; Add other needed files here

[Icons]
Name: "{group}\OrganizAhh"; Filename: "{app}\app.exe"
Name: "{group}\Uninstall OrganizAhh"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\app.exe"; Description: "Run OrganizAhh"; Flags: nowait postinstall skipifsilent

[Code]
var
  GeminiApiKeyPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  GeminiApiKeyPage := CreateInputQueryPage(
    wpWelcome,
    'Gemini API Key',
    'Enter your Gemini API Key',
    'Please enter your Gemini API key below. You can get this from Google AI Studio.'
  );
  GeminiApiKeyPage.Add('Gemini API Key:', False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvFile: String;
  ApiKey: String;
  EnvText: String;
  EnvFileHandle: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    ApiKey := GeminiApiKeyPage.Values[0];
    if ApiKey <> '' then
    begin
      EnvFile := ExpandConstant('{app}\.env');
      EnvText := 'GOOGLE_API_KEY=' + ApiKey + #13#10;
      SaveStringToFile(EnvFile, EnvText, False);
    end;
  end;
end;