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
AllowUNCPath=yes
AlwaysShowDirOnReadyPage=yes
AppendDefaultDirName=yes
DirExistsWarning=yes
EnableDirDoesntExistWarning=yes
UsePreviousAppDir=yes
DisableDirPage=no

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
  LocationSelectionPage: TInputOptionWizardPage;

procedure LabelClick(Sender: TObject);
var
  ErrorCode: Integer;
begin
  ShellExec('open', 'https://aistudio.google.com/apikey', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;

procedure InitializeWizard;
begin
  // Create location selection page
  LocationSelectionPage := CreateInputOptionPage(
    wpWelcome,
    'Installation Location',
    'Choose where to install OrganizAhh',
    'Select the location where you would like to install OrganizAhh:',
    True,
    False
  );

  // Add location options
  LocationSelectionPage.Add('Program Files (Recommended)');
  LocationSelectionPage.Add('User Documents Folder');
  LocationSelectionPage.Add('User AppData Folder');
  LocationSelectionPage.Add('Custom Location');

  // Set default selection
  LocationSelectionPage.SelectedValueIndex := 0;

  // Create Gemini API Key page
  GeminiApiKeyPage := CreateInputQueryPage(
    LocationSelectionPage.ID,
    'Gemini API Key',
    'Enter your Gemini API Key',
    'Please enter your Gemini API key below. You can get this from Google AI Studio at:'
  );
  GeminiApiKeyPage.Add('', False);
  GeminiApiKeyPage.Add('Gemini API Key:', False);

  // Add clickable link
  GeminiApiKeyPage.Edits[0].Visible := False;
  GeminiApiKeyPage.Edits[0].Text := 'https://aistudio.google.com/apikey';

  // Create a new label with clickable link
  with TNewStaticText.Create(GeminiApiKeyPage.Surface) do
  begin
    Parent := GeminiApiKeyPage.Surface;
    Caption := 'https://aistudio.google.com/apikey';
    Cursor := crHand;
    OnClick := @LabelClick;
    Top := GeminiApiKeyPage.Edits[0].Top;
    Left := GeminiApiKeyPage.Edits[0].Left;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;

  // Skip the directory page unless custom location is selected
  if (PageID = wpSelectDir) and (LocationSelectionPage <> nil) then
    Result := LocationSelectionPage.SelectedValueIndex <> 3;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  S: String;
begin
  S := '';

  // Add installation location info
  S := S + 'Installation Location:' + NewLine;
  S := S + Space + ExpandConstant('{app}') + NewLine + NewLine;

  // Add the rest of the default information
  if MemoDirInfo <> '' then
    S := S + MemoDirInfo + NewLine;
  if MemoGroupInfo <> '' then
    S := S + MemoGroupInfo + NewLine;
  if MemoTasksInfo <> '' then
    S := S + MemoTasksInfo + NewLine;

  Result := S;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  // Handle location selection
  if CurPageID = LocationSelectionPage.ID then
  begin
    case LocationSelectionPage.SelectedValueIndex of
      0: // Program Files
        WizardForm.DirEdit.Text := ExpandConstant('{pf}\OrganizAhh');
      1: // Documents
        WizardForm.DirEdit.Text := ExpandConstant('{userdocs}\OrganizAhh');
      2: // AppData
        WizardForm.DirEdit.Text := ExpandConstant('{userappdata}\OrganizAhh');
      3: // Custom - show directory selection page
        begin
          // The next page will be the directory selection page
          // We don't need to do anything special here
        end;
    end;
  end;
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
    ApiKey := GeminiApiKeyPage.Values[1]; // Index changed to 1 since we added a hidden field
    if ApiKey <> '' then
    begin
      EnvFile := ExpandConstant('{app}\.env');
      EnvText := 'GOOGLE_API_KEY=' + ApiKey + #13#10;
      SaveStringToFile(EnvFile, EnvText, False);
    end;
  end;
end;