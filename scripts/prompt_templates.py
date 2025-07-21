prompt_template_gemini = r"""
                        You are an expert file organizer. Given a list of filenames from a directory, generate a JSON structure proposing a logical organization into folders and subfolders, intelligently and intuitively based.
                        {format_instructions}
                        Group similar files together. Use descriptive names for topics and subtopics. The structure should resemble this example:

                        {{
                          "Topic_1": {{
                            "Subtopic_1": [ "file1.txt", "file2.pdf" ],
                            "Subtopic_2": [ "imageA.jpg" ]
                          }},
                          "Topic_2": [ "archive.zip", "installer.exe" ]
                        }}

                        Here is the list of files to organize:
                        {files_chunk}
                        """

prompt_template_local = r"""
                        You are an expert file organizer. Given a list of filenames from a directory, generate a JSON structure proposing a logical organization into folders and subfolders, intelligently and intuitively based.
                        {format_instructions}
                        Group similar files together. Use descriptive names for topics and subtopics. The structure should resemble this example:
 
                        Example 1:
                        Files: ["budget_2024.xlsx", "project_plan.docx", "team_photo.jpg"]
                        Output:
                        {{
                        "Documents": {{
                            "Finance": ["budget_2024.xlsx"],
                            "Planning": ["project_plan.docx"]
                        }},
                        "Media": ["team_photo.jpg"]
                        }}

                        Example 2:
                        Files: ["main.py", "utils.py", "readme.md", "requirements.txt"]
                        Output:
                        {{
                        "Code": {{
                            "Python": ["main.py", "utils.py"],
                            "Documentation": ["readme.md", "requirements.txt"]
                        }}
                        }}
                        
                        Here is the list of files to organize:
                        {files_chunk}
                        """