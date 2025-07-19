import os
import platform
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton,  QScrollArea,
    QFileDialog, QInputDialog, QProgressDialog, QTreeWidget, QTreeWidgetItem,
    QSizePolicy, QFrame, QSpacerItem, QStyle,QMenu
)
from PyQt5.QtCore import Qt, QThread, QUrl, QTimer
from PyQt5.QtGui import QFont, QDesktopServices

from pyQT.Helpers import show_error_message,show_info_message,show_warning_message,ask_yes_no



from constants.app_constants import APP_NAME

class BasePage(QWidget):
    """Base class for pages."""
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setup_fonts()
        self.setup_ui()

    def setup_fonts(self):
        """Define standard fonts for the application."""
        base_family = "Segoe UI" if platform.system() == "Windows" else "Sans-Serif" # More generic fallback
        self.FONT_TITLE = QFont(base_family, 20, QFont.Bold)
        self.FONT_SUBTITLE = QFont(base_family, 14)
        self.FONT_BODY = QFont(base_family, 10)
        self.FONT_BODY_BOLD = QFont(base_family, 10, QFont.Bold)
        self.FONT_BUTTON = QFont(base_family, 10, QFont.Bold)
        self.FONT_LABEL = QFont(base_family, 9)
        self.FONT_SMALL = QFont(base_family, 8)
        self.FONT_ICON_LARGE = QFont(base_family, 40) # For emoji icons

    def setup_ui(self):
        """Placeholder for UI setup in subclasses."""
        pass

    def on_show(self):
        """Called when the page is shown. Subclasses can override."""
        pass

class StartPage(BasePage):
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignCenter) # Center content vertically

        # --- Header ---
        title = QLabel(APP_NAME)
        title.setFont(self.FONT_TITLE)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Clean up your folders effortlessly")
        subtitle.setFont(self.FONT_SUBTITLE)
        subtitle.setAlignment(Qt.AlignCenter)
        # Add some styling for subtitle color if desired via QSS
        # subtitle.setStyleSheet("color: gray;")
        layout.addWidget(subtitle)

        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Folder Selection Card ---
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel) # Give it a panel look
        # card.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 10px; }") # Example QSS
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card.setMaximumWidth(600) # Limit card width

        # --- Folder Selection Row ---
        folder_select_layout = QHBoxLayout()
        folder_label = QLabel("Select Folder:")
        folder_label.setFont(self.FONT_BODY_BOLD)
        browse_button = QPushButton("Browse...")
        browse_button.setFont(self.FONT_BUTTON)
        browse_button.setFixedWidth(120)
        browse_button.clicked.connect(self.browse_folder)

        folder_select_layout.addWidget(folder_label)
        folder_select_layout.addWidget(browse_button)
        folder_select_layout.addStretch()
        card_layout.addLayout(folder_select_layout)

        # --- Path Display ---
        self.path_display_label = QLabel("No folder selected")
        self.path_display_label.setFont(self.FONT_LABEL)
        self.path_display_label.setWordWrap(True)
        # self.path_display_label.setStyleSheet("color: gray;")
        card_layout.addWidget(self.path_display_label)

        # --- Analyze Button ---
        self.analyze_btn = QPushButton("Analyze Folder")
        self.analyze_btn.setFont(self.FONT_BUTTON)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setFixedHeight(40)
        self.analyze_btn.clicked.connect(self.go_to_analysis)
        # self.analyze_btn.setStyleSheet("padding: 5px;") # Add padding
        card_layout.addWidget(self.analyze_btn, alignment=Qt.AlignCenter)

        layout.addWidget(card, alignment=Qt.AlignCenter) # Center the card horizontally
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setLayout(layout)

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            self.controller.folder_path = path
            max_len = 60
            display_path = path if len(path) <= max_len else "..." + path[-(max_len-3):]
            self.path_display_label.setText(f"Selected: {display_path}")
            # self.path_display_label.setStyleSheet("color: black;") # Reset color
            self.analyze_btn.setEnabled(True)
        # else: No change if cancelled

    def go_to_analysis(self):
        if not self.controller.folder_path:
            show_warning_message("No Folder", "Please select a folder first.")
            return

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing...")

        # Setup Progress Dialog
        self.progress_dialog = QProgressDialog("Analyzing folder...", "Cancel", 0, 0, self) # Indeterminate
        self.progress_dialog.setWindowTitle("Analysis in Progress")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False) # We'll close it manually
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.show()

        # Setup Worker Thread
        self.analysis_thread = QThread()
        #============Import Main Agent================#
        from pyQT.Main import AnalysisWorker
        self.analysis_worker = AnalysisWorker(self.controller)
        self.analysis_worker.moveToThread(self.analysis_thread)

        # Connect signals
        self.analysis_worker.progress.connect(self.update_progress_status)
        self.analysis_worker.finished.connect(self.analysis_complete)
        self.analysis_worker.error.connect(self.analysis_error)
        self.analysis_thread.started.connect(self.analysis_worker.run)
        self.analysis_thread.finished.connect(self.analysis_thread.deleteLater) # Clean up thread
        self.progress_dialog.canceled.connect(self.cancel_analysis) # Allow cancellation

        # Start the thread
        self.analysis_thread.start()

    def update_progress_status(self, message):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            QApplication.processEvents() # Keep dialog responsive

    def analysis_complete(self, success, analysis_result, generated_structure, summary):
        self.progress_dialog.close()
        self.analysis_thread.quit()
        self.analysis_thread.wait()

        self.analyze_btn.setText("Analyze Folder")
        self.analyze_btn.setEnabled(bool(self.controller.folder_path)) # Re-enable if path still valid

        if success:
            self.controller.analysis_result = analysis_result
            self.controller.generated_structure = generated_structure
            self.controller.current_analysis_summary = summary

            if not analysis_result and not generated_structure:
                 show_info_message("Analysis Complete", "The folder is empty or no relevant files were found.")
            else:
                # Populate AnalyzePage *before* showing
                analyze_page = self.controller.pages["AnalyzePage"]
                analyze_page.populate_analysis()
                self.controller.show_page("AnalyzePage")
        # Error messages handled by analysis_error or specific checks in worker

    def analysis_error(self, error_message):
         # This catches errors emitted by the worker specifically
        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.close()
        if self.analysis_thread and self.analysis_thread.isRunning():
            # Note: Forcefully terminating threads is generally discouraged.
            # A better approach would involve the worker checking a flag.
            # For simplicity here, we just quit the thread. The worker might finish.
            self.analysis_thread.quit()
            self.analysis_thread.wait()

        self.analyze_btn.setText("Analyze Folder")
        self.analyze_btn.setEnabled(bool(self.controller.folder_path))
        show_error_message("Analysis Error", error_message)


    def cancel_analysis(self):
        print("Analysis cancelled by user.")
        if self.analysis_thread and self.analysis_thread.isRunning():
            # Note: Forcefully terminating threads is generally discouraged.
            # A better approach would involve the worker checking a flag.
            # For simplicity here, we just quit the thread. The worker might finish.
            self.analysis_thread.quit()
            self.analysis_thread.wait()
        if self.progress_dialog:
             self.progress_dialog.close()
        self.analyze_btn.setText("Analyze Folder")
        self.analyze_btn.setEnabled(bool(self.controller.folder_path))


class AnalyzePage(BasePage):
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)

        # --- Header ---
        header_layout = QVBoxLayout()
        title = QLabel("Analysis Preview")
        title.setFont(self.FONT_TITLE)
        self.subtitle_label = QLabel("Folder: ")
        self.subtitle_label.setFont(self.FONT_LABEL)
        # self.subtitle_label.setStyleSheet("color: gray;")
        header_layout.addWidget(title)
        header_layout.addWidget(self.subtitle_label)
        main_layout.addLayout(header_layout)

        # --- Results Area ---
        self.results_scroll_area = QScrollArea()
        self.results_scroll_area.setWidgetResizable(True)
        self.results_scroll_area.setFrameShape(QFrame.StyledPanel)
        self.results_widget = QWidget() # Content widget for scroll area
        self.results_layout = QVBoxLayout(self.results_widget) # Layout for content
        self.results_layout.setAlignment(Qt.AlignTop) # Add items to the top
        self.results_scroll_area.setWidget(self.results_widget)
        main_layout.addWidget(self.results_scroll_area, 1) # Give scroll area stretch factor

        # --- Summary Label ---
        self.summary_label = QLabel("Analyzing...")
        self.summary_label.setFont(self.FONT_LABEL)
        # self.summary_label.setStyleSheet("color: gray;")
        main_layout.addWidget(self.summary_label)

        # --- Button Bar ---
        btn_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setFont(self.FONT_BUTTON)
        back_btn.setFixedWidth(120)
        back_btn.clicked.connect(lambda: self.controller.show_page("StartPage"))

        self.edit_btn = QPushButton("Edit Structure")
        self.edit_btn.setFont(self.FONT_BUTTON)
        self.edit_btn.setFixedWidth(160)
        self.edit_btn.setFixedHeight(40)
        self.edit_btn.clicked.connect(self.edit_structure)

        self.continue_btn = QPushButton("Continue to Organize")
        self.continue_btn.setFont(self.FONT_BUTTON)
        self.continue_btn.setFixedWidth(180)
        self.continue_btn.setFixedHeight(40)
        self.continue_btn.clicked.connect(self.organize_now)

        self.organize_btn = QPushButton("Organize Now →")
        self.organize_btn.setFont(self.FONT_BUTTON)
        self.organize_btn.setFixedWidth(160)
        self.organize_btn.setFixedHeight(40)
        self.organize_btn.clicked.connect(self.organize_now)

        btn_layout.addWidget(back_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.continue_btn)
        btn_layout.addWidget(self.organize_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def clear_layout(self, layout):
        """Removes all widgets from a layout."""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self.clear_layout(sub_layout)

    def populate_analysis(self):
        """Populate the scrollable area with analysis results."""
        # Clear previous results
        self.clear_layout(self.results_layout)

        # Update path subtitle
        path = self.controller.folder_path
        max_len = 70
        display_path = path if len(path) <= max_len else "..." + path[-(max_len-3):]
        self.subtitle_label.setText(f"Folder: {display_path}")

        # Check if results exist
        has_results = bool(self.controller.analysis_result or self.controller.generated_structure)

        if not has_results:
            no_files_label = QLabel("No files found or analysis failed.")
            no_files_label.setFont(self.FONT_BODY)
            # no_files_label.setStyleSheet("color: gray;")
            self.results_layout.addWidget(no_files_label, alignment=Qt.AlignCenter)
            self.summary_label.setText("No files to organize.")
            self.edit_btn.setEnabled(False)
            self.continue_btn.setEnabled(False)
            self.organize_btn.setEnabled(False)
            return

        # Enable buttons
        self.edit_btn.setEnabled(True)
        self.continue_btn.setEnabled(True)
        self.organize_btn.setEnabled(True)

        # --- Display Generated Structure (if available) ---
        if self.controller.generated_structure:
            structure_label = QLabel("AI-Generated Organization Structure")
            structure_label.setFont(self.FONT_SUBTITLE)
            self.results_layout.addWidget(structure_label)

            def display_structure_recursive(layout, structure, level=0):
                indent = "    " * level
                for item, content in sorted(structure.items()):
                    is_folder = isinstance(content, dict)
                    prefix = "📁 " if is_folder else "📄 "

                    item_label_text = f"{indent}{prefix}{item}"
                    item_label = QLabel(item_label_text)
                    item_label.setFont(self.FONT_BODY)
                    layout.addWidget(item_label)

                    if isinstance(content, dict):
                        display_structure_recursive(layout, content, level + 1)
                    elif isinstance(content, list): # List of files
                         for file_item in sorted(content):
                              file_label = QLabel(f"{indent}    📄 {file_item}")
                              file_label.setFont(self.FONT_BODY)
                              layout.addWidget(file_label)
                    elif isinstance(content, str): # Single file
                         file_label = QLabel(f"{indent}    📄 {content}")
                         file_label.setFont(self.FONT_BODY)
                         layout.addWidget(file_label)


            display_structure_recursive(self.results_layout, self.controller.generated_structure)

            # Add a separator
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            self.results_layout.addWidget(separator)

            current_label = QLabel("Current Files by Type (For Reference)")
            current_label.setFont(self.FONT_SUBTITLE)
            self.results_layout.addWidget(current_label)

        # --- Display Analysis by Extension (Always show for reference or if no LLM) ---
        if self.controller.analysis_result:
            sorted_categories = sorted(self.controller.analysis_result.keys())
            for category in sorted_categories:
                files = self.controller.analysis_result[category]
                if not files: continue

                cat_label = QLabel(f"{category} ({len(files)})")
                cat_label.setFont(self.FONT_BODY_BOLD)
                self.results_layout.addWidget(cat_label)

                for file in sorted(files):
                    file_label = QLabel(f"    {file}") # Indent files
                    file_label.setFont(self.FONT_BODY)
                    self.results_layout.addWidget(file_label)
                self.results_layout.addSpacing(5) # Add space between categories
        elif not self.controller.generated_structure:
             # Only show this if there's no generated structure AND no analysis result (should be caught earlier)
             no_files_label = QLabel("No analysis results available.")
             no_files_label.setFont(self.FONT_BODY)
             self.results_layout.addWidget(no_files_label)


        # Update summary text
        self.summary_label.setText(self.controller.current_analysis_summary)
        self.results_widget.adjustSize() # Adjust content widget size

    def edit_structure(self):
        if not (self.controller.analysis_result or self.controller.generated_structure):
            show_warning_message("Nothing to Organize", "The analysis did not find any files to organize.")
            return
        # Prepare EditStructurePage before showing
        edit_page = self.controller.pages["EditStructurePage"]
        edit_page.load_structure()
        self.controller.show_page("EditStructurePage")

    def organize_now(self):
        if not (self.controller.analysis_result or self.controller.generated_structure):
            show_warning_message("Nothing to Organize", "The analysis did not find any files to organize.")
            return
        # Go directly to confirmation
        self.controller.show_page("ConfirmPage")


class EditStructurePage(BasePage):
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)

        # --- Header ---
        header_layout = QVBoxLayout()
        title = QLabel("Edit Organization Structure")
        title.setFont(self.FONT_TITLE)
        subtitle = QLabel("Customize the structure using the tree view below.")
        subtitle.setFont(self.FONT_LABEL)
        # subtitle.setStyleSheet("color: gray;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # --- Main Content Area (Tree View Only) ---
        # Using QTreeWidget simplifies editing significantly
        content_layout = QVBoxLayout()

        # Header for Tree
        tree_header_layout = QHBoxLayout()
        tree_title = QLabel("Organization Structure")
        tree_title.setFont(self.FONT_BODY_BOLD)
        add_category_btn = QPushButton("+ New Top-Level Category")
        add_category_btn.setFont(self.FONT_SMALL)
        add_category_btn.setFixedHeight(45)
        add_category_btn.clicked.connect(self._add_new_category)

        tree_header_layout.addWidget(tree_title)
        tree_header_layout.addStretch()
        tree_header_layout.addWidget(add_category_btn)
        content_layout.addLayout(tree_header_layout)

        # Add drag and drop hint
        drag_hint = QLabel("Tip: Drag and drop files between folders to reorganize")
        drag_hint.setFont(self.FONT_SMALL)
        content_layout.addWidget(drag_hint)

        # Status message for operations
        self.status_label = QLabel("")
        self.status_label.setFont(self.FONT_SMALL)
        content_layout.addWidget(self.status_label)

        # Tree Widget
        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderLabels(["Category / File"])
        self.structure_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.structure_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.structure_tree.itemChanged.connect(self.handle_item_rename) # Handle renaming via editing

        # Enable drag and drop
        self.structure_tree.setDragEnabled(True)
        self.structure_tree.setAcceptDrops(True)
        self.structure_tree.setDropIndicatorShown(True)
        self.structure_tree.setDragDropMode(QTreeWidget.InternalMove)  # Allow moving items within the tree
        self.structure_tree.setSelectionMode(QTreeWidget.ExtendedSelection)  # Allow selecting multiple items

        # Connect drag and drop signal
        self.structure_tree.model().rowsInserted.connect(self.handle_item_moved)

        content_layout.addWidget(self.structure_tree)

        main_layout.addLayout(content_layout, 1) # Tree gets stretch factor

        # --- Button Bar ---
        btn_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setFont(self.FONT_BUTTON)
        back_btn.setFixedWidth(120)
        back_btn.clicked.connect(lambda: self.controller.show_page("AnalyzePage"))

        self.confirm_btn = QPushButton("Continue to Organize →")
        self.confirm_btn.setFont(self.FONT_BUTTON)
        self.confirm_btn.setFixedHeight(40)
        self.confirm_btn.clicked.connect(self.confirm)

        btn_layout.addWidget(back_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.confirm_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        # Flag to prevent recursive renaming signal
        self._is_renaming = False


    def load_structure(self):
        """Load the structure into the QTreeWidget."""
        self.structure_tree.clear()
        source_structure = self.controller.generated_structure if self.controller.generated_structure else self.controller.analysis_result
        use_llm_structure = bool(self.controller.generated_structure)

        if not source_structure:
             # Should not happen if called correctly, but handle defensively
             self.structure_tree.addTopLevelItem(QTreeWidgetItem(["No structure to display"]))
             return

        def add_items_recursive(parent_item, structure):
            if isinstance(structure, dict):
                for key, value in sorted(structure.items()):
                    # Special handling for _files_ key - don't show it in the UI
                    if key == "_files_":
                        # Add files directly to parent_item without showing "_files_" folder
                        if isinstance(value, list):
                            for filename in sorted(value):
                                file_item = QTreeWidgetItem([filename])
                                file_item.setData(0, Qt.UserRole, {"type": "file", "name": filename})
                                # Enable dragging but disable editing for files
                                file_item.setFlags(file_item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                                file_item.setIcon(0, self.style().standardIcon(getattr(QStyle, "SP_FileIcon", QStyle.SP_CustomBase)))
                                parent_item.addChild(file_item)
                        continue  # Skip creating a folder for _files_

                    # Create folder item for regular folders
                    folder_item = QTreeWidgetItem([key])
                    folder_item.setData(0, Qt.UserRole, {"type": "folder", "path": key}) # Store type and name
                    # Allow renaming, dragging, and dropping
                    folder_item.setFlags(folder_item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                    folder_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon)) # Use folder icon
                    parent_item.addChild(folder_item)
                    # Recursively add children
                    add_items_recursive(folder_item, value)
            elif isinstance(structure, list):
                 # Add files under the current parent folder
                 for filename in sorted(structure):
                      file_item = QTreeWidgetItem([filename])
                      file_item.setData(0, Qt.UserRole, {"type": "file", "name": filename}) # Store type and name
                      # Enable dragging but disable editing for files
                      file_item.setFlags(file_item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                      file_item.setIcon(0, self.style().standardIcon(getattr(QStyle, "SP_FileIcon", QStyle.SP_CustomBase)))
                      parent_item.addChild(file_item)
            elif isinstance(structure, str): # Handle single file string as value
                 file_item = QTreeWidgetItem([structure])
                 file_item.setData(0, Qt.UserRole, {"type": "file", "name": structure})
                 # Enable dragging but disable editing for files
                 file_item.setFlags(file_item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                 file_item.setIcon(0, self.style().standardIcon(getattr(QStyle, "SP_FileIcon", QStyle.SP_CustomBase)))
                 parent_item.addChild(file_item)


        # If using analysis_result (flat structure), create top-level items for categories
        if not use_llm_structure:
             for category, files in sorted(source_structure.items()):
                  category_item = QTreeWidgetItem([category])
                  category_item.setData(0, Qt.UserRole, {"type": "folder", "path": category})
                  # Allow renaming, dragging, and dropping
                  category_item.setFlags(category_item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                  category_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                  self.structure_tree.addTopLevelItem(category_item)
                  add_items_recursive(category_item, files) # Add files under category
        else:
             # If using LLM structure, add items starting from the root
             add_items_recursive(self.structure_tree.invisibleRootItem(), source_structure)

        self.structure_tree.expandAll() # Expand tree initially

    def show_context_menu(self, position):
        """Show context menu for tree items."""
        item = self.structure_tree.itemAt(position)
        if not item:
            return

        menu = QMenu()
        item_data = item.data(0, Qt.UserRole)
        item_type = item_data.get("type") if item_data else None

        if item_type == "folder":
            rename_action = menu.addAction("Rename Category")
            rename_action.triggered.connect(lambda: self.rename_item(item))
            delete_action = menu.addAction("Delete Category")
            delete_action.triggered.connect(lambda: self.delete_item(item))
            add_subfolder_action = menu.addAction("Add Subfolder")
            add_subfolder_action.triggered.connect(lambda: self.add_subfolder(item))
        # Add actions for files if needed (e.g., move to different category)

        menu.exec_(self.structure_tree.viewport().mapToGlobal(position))

    def rename_item(self, item):
        """Initiate renaming of the selected item."""
        self.structure_tree.editItem(item, 0) # Start editing the item text

    def handle_item_rename(self, item, column):
        """Handle the actual renaming after editing is finished."""
        if self._is_renaming: # Prevent recursion from setData
             return
        if column != 0:
             return

        item_data = item.data(0, Qt.UserRole)
        if not item_data or item_data.get("type") != "folder":
             return # Only handle folder renames here

        old_name = item_data.get("path") # Get the original name/path stored
        new_name = item.text(0).strip()

        if not new_name or new_name == old_name:
            # If name is empty or unchanged, revert
            self._is_renaming = True
            item.setText(0, old_name)
            self._is_renaming = False
            return

        print(f"Attempting rename: '{old_name}' -> '{new_name}'")

        # --- Update the underlying data structure ---
        # This is complex because we need to find the item in the nested dict/list
        # and update the key or value. This is a limitation of directly mapping
        # a mutable dict to a tree view without a proper model.
        # For simplicity, we'll rebuild the structure from the tree after rename.
        # A more robust solution uses QAbstractItemModel.

        # Rebuild the internal structure from the tree (Simplified approach)
        self.update_structure_from_tree()

        # Refresh the tree to ensure consistency (might be redundant but safer)
        self.load_structure()

        show_info_message("Renamed", f"Category '{old_name}' renamed to '{new_name}'.")


    def delete_item(self, item):
        """Delete the selected category item."""
        item_data = item.data(0, Qt.UserRole)
        if not item_data or item_data.get("type") != "folder":
            return

        category_name = item.text(0) # Get current display name

        if not ask_yes_no("Confirm Delete", f"Delete category '{category_name}'?\nFiles within will be lost in this view (but not deleted from disk yet)."):
             return

        # Remove item from tree
        parent = item.parent() or self.structure_tree.invisibleRootItem()
        parent.removeChild(item)

        # Update the internal structure based on the modified tree
        self.update_structure_from_tree()

        show_info_message("Deleted", f"Category '{category_name}' removed from structure.")
        # Note: Files are not moved to "Others" in this simplified tree approach.
        # The organization step will handle files based on the *final* structure.

    def add_subfolder(self, parent_item):
         """Adds a new subfolder under the selected item."""
         item_data = parent_item.data(0, Qt.UserRole)
         if not item_data or item_data.get("type") != "folder":
             return # Can only add subfolders to folders

         new_name, ok = QInputDialog.getText(self, "Add Subfolder", f"Enter name for new subfolder under '{parent_item.text(0)}':")
         if ok and new_name.strip():
             new_name = new_name.strip()

             # Check if subfolder with this name already exists
             for i in range(parent_item.childCount()):
                 if parent_item.child(i).text(0) == new_name:
                     show_warning_message("Exists", f"A subfolder named '{new_name}' already exists here.")
                     return

             # Create new tree item
             new_folder_item = QTreeWidgetItem([new_name])
             new_folder_item.setData(0, Qt.UserRole, {"type": "folder", "path": new_name}) # Path relative to parent for now
             # Allow renaming, dragging, and dropping
             new_folder_item.setFlags(new_folder_item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
             new_folder_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
             parent_item.addChild(new_folder_item)
             parent_item.setExpanded(True)

             # Update the internal structure
             self.update_structure_from_tree()
             print(f"Added subfolder: {new_name}")
         else:
             print("Subfolder addition cancelled or empty name.")


    def _add_new_category(self):
        """Add a new top-level category."""
        new_name, ok = QInputDialog.getText(self, "New Category", "Enter name for the new top-level category:")
        if ok and new_name.strip():
            new_name = new_name.strip()

            # Check if top-level category exists
            for i in range(self.structure_tree.topLevelItemCount()):
                 if self.structure_tree.topLevelItem(i).text(0) == new_name:
                      show_warning_message("Exists", f"A top-level category named '{new_name}' already exists.")
                      return

            # Add item to tree
            new_item = QTreeWidgetItem([new_name])
            new_item.setData(0, Qt.UserRole, {"type": "folder", "path": new_name})
            # Allow renaming, dragging, and dropping
            new_item.setFlags(new_item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
            new_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
            new_item.setTextAlignment(0, Qt.AlignVCenter | Qt.AlignLeft)
            self.structure_tree.addTopLevelItem(new_item)
            self.structure_tree.setColumnWidth(0, 250)
            # Update internal structure
            self.update_structure_from_tree()
            show_info_message("Added", f"Category '{new_name}' added.")
        else:
             print("Category addition cancelled or empty name.")


    def update_structure_from_tree(self):
        """Rebuilds the controller's generated_structure from the QTreeWidget."""
        # We'll build the structure directly in the temp_root_dict variable

        def build_dict_recursive(parent_dict, tree_item):
            has_files = False
            files_list = []

            # First pass: collect all files and create subfolders
            for i in range(tree_item.childCount()):
                child_item = tree_item.child(i)
                item_data = child_item.data(0, Qt.UserRole)
                item_name = child_item.text(0)

                # Skip items with no data or invalid names
                if not item_data or not item_name or not item_name.strip():
                    continue

                item_type = item_data.get("type")

                # Only process items with a valid type
                if item_type == "folder":
                    # Create a new dict for the folder and recurse
                    sub_dict = {}
                    parent_dict[item_name] = sub_dict
                    build_dict_recursive(sub_dict, child_item)
                elif item_type == "file":
                    # Only add files with valid names
                    if item_name and item_name.strip():
                        has_files = True
                        files_list.append(item_name)

            # Only add _files_ if there are actual files and this isn't a renamed folder
            if has_files and files_list and len(files_list) > 0:
                parent_dict["_files_"] = files_list


        # Build the structure starting from the invisible root
        root = self.structure_tree.invisibleRootItem()
        temp_root_dict = {}
        build_dict_recursive(temp_root_dict, root)

        # Clean up the temporary structure by removing empty folders and _files_ entries
        def clean_structure(structure):
            if isinstance(structure, dict):
                # Remove empty _files_ lists
                if "_files_" in structure and (not structure["_files_"] or len(structure["_files_"]) == 0):
                    del structure["_files_"]

                # Recursively clean all sub-dictionaries
                for key, value in list(structure.items()):
                    if isinstance(value, dict):
                        clean_structure(value)
                        # If the sub-dictionary became empty after cleaning, remove it
                        if not value:
                            del structure[key]

        # Apply cleaning to remove empty folders and _files_ entries
        clean_structure(temp_root_dict)

        # The final structure is the cleaned version
        final_structure = temp_root_dict

        print("Rebuilt structure from tree:", final_structure)
        self.controller.generated_structure = final_structure
        # Clear analysis result if structure was edited
        self.controller.analysis_result = {}
        # If the original was analysis_result, update that instead/as well? Needs clarification.
        # For now, always update generated_structure, assuming user edits create the desired final form.

    def confirm(self):
        """Update structure from tree and proceed to confirmation."""
        self.update_structure_from_tree() # Save changes from tree before confirming
        if not self.controller.generated_structure and not self.controller.analysis_result:
             show_warning_message("Empty Structure", "There is no organization structure defined.")
             return
        self.controller.show_page("ConfirmPage")

    def handle_item_moved(self, *_):
        """Handle when an item is moved via drag and drop

        Parameters are required by the signal but not used in this implementation.
        We use *_ to indicate unused variable-length arguments.
        """
        # Wait a moment for the UI to update before rebuilding the structure
        QTimer.singleShot(100, self.update_structure_from_tree)

        # Update status label
        self.status_label.setText("Item moved - structure updated")

        # Clear status after a delay
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

        # Log to console
        print("Item moved via drag and drop - structure will be updated")

    def on_show(self):
        """Reload structure when page is shown."""
        self.load_structure()


class ConfirmPage(BasePage):
     def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        # card.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 10px; max-width: 400px; }")
        card.setMaximumWidth(450)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setAlignment(Qt.AlignCenter)

        # --- Icon and Title ---
        icon_label = QLabel("⚠️") # Emoji icon
        icon_label.setFont(self.FONT_ICON_LARGE)
        icon_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_label)

        title = QLabel("Confirm Organization")
        title.setFont(self.FONT_SUBTITLE)
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        # --- Warning Text ---
        warning_text = ("This will move files into new subfolders within the selected directory.\n\n"
                        "This action cannot be automatically undone.")
        warning_details = QLabel(warning_text)
        warning_details.setFont(self.FONT_BODY)
        # warning_details.setStyleSheet("color: gray;")
        warning_details.setAlignment(Qt.AlignCenter)
        warning_details.setWordWrap(True)
        card_layout.addWidget(warning_details)
        card_layout.addSpacing(25)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)

        cancel_btn = QPushButton("Back")
        cancel_btn.setFont(self.FONT_BUTTON)
        cancel_btn.setFixedWidth(120)
        # cancel_btn.setStyleSheet("background-color: gray; color: white;")
        cancel_btn.clicked.connect(lambda: self.controller.show_page("EditStructurePage")) # Or AnalyzePage?

        self.confirm_btn = QPushButton("Yes, Organize Now")
        self.confirm_btn.setFont(self.FONT_BUTTON)
        self.confirm_btn.setFixedWidth(160)
        self.confirm_btn.setFixedHeight(40)
        # self.confirm_btn.setStyleSheet("background-color: #FF9F0A; color: black;") # Orange-like
        self.confirm_btn.clicked.connect(self.organize)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self.confirm_btn)
        card_layout.addLayout(btn_layout)

        layout.addWidget(card) # Add card to the main centered layout

        self.setLayout(layout)

     def organize(self):
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setText("Organizing...")

        # Setup Worker Thread
        self.organize_thread = QThread()
        #============Import Main Agent================#
        from pyQT.Main import OrganizeWorker
        self.organize_worker = OrganizeWorker(self.controller)
        self.organize_worker.moveToThread(self.organize_thread)

        # Connect signals
        self.organize_worker.finished.connect(self.organize_complete)
        self.organize_worker.error.connect(self.organize_error)
        self.organize_thread.started.connect(self.organize_worker.run)
        self.organize_thread.finished.connect(self.organize_thread.deleteLater)

        # Start
        self.organize_thread.start()

     def organize_complete(self, success, summary_message):
        self.organize_thread.quit()
        self.organize_thread.wait()
        self.confirm_btn.setText("Yes, Organize Now")
        self.confirm_btn.setEnabled(True)

        self.controller.organization_summary = summary_message # Store summary

        if success:
            # Update CompletePage message before showing
            complete_page = self.controller.pages["CompletePage"]
            complete_page.update_completion_message()
            self.controller.show_page("CompletePage")
        # Error messages handled by organize_error or specific checks in worker

     def organize_error(self, error_message):
        if self.organize_thread and self.organize_thread.isRunning():
            self.organize_thread.quit()
            self.organize_thread.wait()
        self.confirm_btn.setText("Yes, Organize Now")
        self.confirm_btn.setEnabled(True)
        show_error_message("Organization Error", error_message)
        # Stay on ConfirmPage after error

class CompletePage(BasePage):
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        # card.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 10px; max-width: 400px; }")
        card.setMaximumWidth(450)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setAlignment(Qt.AlignCenter)

        # --- Icon and Title ---
        icon_label = QLabel("✅") # Emoji icon
        icon_label.setFont(self.FONT_ICON_LARGE)
        icon_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_label)

        title = QLabel("Organization Complete!")
        title.setFont(self.FONT_SUBTITLE)
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        # --- Details Text ---
        self.details_label = QLabel("Files have been successfully organized.")
        self.details_label.setFont(self.FONT_BODY)
        # self.details_label.setStyleSheet("color: gray;")
        self.details_label.setAlignment(Qt.AlignCenter)
        self.details_label.setWordWrap(True)
        card_layout.addWidget(self.details_label)
        card_layout.addSpacing(30)

        # --- Buttons (Vertical Layout) ---
        btn_width = 220

        open_btn = QPushButton("📂 Open Folder")
        open_btn.setFont(self.FONT_BUTTON)
        open_btn.setFixedWidth(btn_width)
        open_btn.setFixedHeight(40)
        open_btn.clicked.connect(self.open_folder)
        card_layout.addWidget(open_btn, alignment=Qt.AlignCenter)

        again_btn = QPushButton("Organize Another Folder")
        again_btn.setFont(self.FONT_BUTTON)
        again_btn.setFixedWidth(btn_width)
        again_btn.setFixedHeight(40)
        again_btn.clicked.connect(self.go_to_start)
        card_layout.addWidget(again_btn, alignment=Qt.AlignCenter)

        exit_btn = QPushButton("Exit Application")
        exit_btn.setFont(self.FONT_BUTTON)
        exit_btn.setFixedWidth(btn_width)
        # exit_btn.setStyleSheet("background-color: gray; color: white;")
        exit_btn.clicked.connect(self.controller.close) # Close main window
        card_layout.addWidget(exit_btn, alignment=Qt.AlignCenter)

        layout.addWidget(card)
        self.setLayout(layout)

    def open_folder(self):
        """Open the organized folder in file explorer."""
        path = self.controller.folder_path
        if not path or not os.path.isdir(path):
            show_warning_message("Open Folder", "Cannot open folder. Path is invalid or not set.")
            return
        try:
            # Use QDesktopServices for cross-platform opening
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            show_error_message("Error", f"Could not open folder: {e}")

    def update_completion_message(self):
        """Updates the message shown on the completion screen."""
        folder_name = os.path.basename(self.controller.folder_path) if self.controller.folder_path else "Selected folder"
        summary = getattr(self.controller, 'organization_summary', "Organization process finished.") # Get summary if exists
        self.details_label.setText(f"Organized '{folder_name}'.\n\n{summary}")

    def go_to_start(self):
        """Resets state and returns to the StartPage."""
        self.controller.reset_state()
        self.controller.show_page("StartPage")

    def on_show(self):
        """Ensure the message is updated when shown."""
        self.update_completion_message()

