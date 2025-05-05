import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QStackedWidget, QProgressBar, 
    QTreeWidget, QTreeWidgetItem, QLineEdit, QDialog, QDialogButtonBox,
    QCheckBox, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, Signal, Slot, QTimer
from PySide6.QtGui import QIcon, QColor, QPalette, QFont, QFontDatabase

# Custom styles
STYLESHEET = """
QMainWindow, QDialog {
    background-color: #f5f5f7;
}

QWidget#centralWidget {
    background-color: #f5f5f7;
}

QFrame.card {
    background-color: white;
    border-radius: 12px;
    border: 1px solid #e0e0e5;
}

QPushButton {
    background-color: #007aff;
    color: white;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
    border: none;
}

QPushButton:hover {
    background-color: #0062cc;
}

QPushButton:pressed {
    background-color: #004999;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #f5f5f7;
}

QPushButton.secondary {
    background-color: transparent;
    color: #007aff;
    border: 1px solid #007aff;
}

QPushButton.secondary:hover {
    background-color: rgba(0, 122, 255, 0.1);
}

QPushButton.secondary:pressed {
    background-color: rgba(0, 122, 255, 0.2);
}

QPushButton.danger {
    background-color: #ff3b30;
}

QPushButton.danger:hover {
    background-color: #ff6961;
}

QProgressBar {
    border: none;
    border-radius: 5px;
    background-color: #e0e0e5;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #007aff;
    border-radius: 5px;
}

QLabel {
    color: #333333;
}

QLabel.title {
    font-size: 24px;
    font-weight: bold;
}

QLabel.subtitle {
    font-size: 16px;
    color: #666666;
}

QTreeWidget {
    border: 1px solid #e0e0e5;
    border-radius: 8px;
    background-color: white;
}

QTreeWidget::item {
    padding: 5px;
    border-radius: 4px;
}

QTreeWidget::item:hover {
    background-color: #f0f0f5;
}

QTreeWidget::item:selected {
    background-color: #e6f2ff;
    color: #333333;
}

QLineEdit {
    padding: 8px 12px;
    border: 1px solid #e0e0e5;
    border-radius: 8px;
    background-color: white;
}

QLineEdit:focus {
    border: 1px solid #007aff;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #cccccc;
}

QCheckBox::indicator:checked {
    background-color: #007aff;
    border: 1px solid #007aff;
}
"""

class FadeAnimation(QPropertyAnimation):
    """Custom animation for fading widgets"""
    def __init__(self, target, duration=250):
        super().__init__(target, b"windowOpacity")
        self.setDuration(duration)
        self.setEasingCurve(QEasingCurve.InOutQuad)
        
    def fade_in(self):
        self.setStartValue(0)
        self.setEndValue(1)
        self.start()
        
    def fade_out(self):
        self.setStartValue(1)
        self.setEndValue(0)
        self.start()

class Card(QFrame):
    """Custom styled card widget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setProperty("class", "card")
        
        # Add shadow effect
        self.setStyleSheet("""
            QFrame.card {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e5;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(16)
        self.setLayout(self.layout)

class AddFolderDialog(QDialog):
    """Dialog for adding a new folder"""
    def __init__(self, parent=None, title="Add New Folder"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 150)
        
        layout = QVBoxLayout(self)
        
        # Folder name input
        self.nameEdit = QLineEdit()
        self.nameEdit.setPlaceholderText("Enter folder name")
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(QLabel("Folder Name:"))
        layout.addWidget(self.nameEdit)
        layout.addStretch()
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_folder_name(self):
        return self.nameEdit.text()

class StartPage(QWidget):
    analyze_folder = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(20)
        
        # Title section
        title_layout = QVBoxLayout()
        title = QLabel("Smart File Organizer")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Clean up your folders effortlessly")
        subtitle.setProperty("class", "subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        title_layout.addSpacing(30)
        
        # Card with folder selection
        self.card = Card()
        card_layout = self.card.layout
        
        folder_layout = QHBoxLayout()
        folder_label = QLabel("Select Folder:")
        self.folder_path = QLabel("No folder selected")
        self.folder_path.setProperty("class", "path")
        self.folder_path.setStyleSheet("padding: 10px; background-color: #f5f5f7; border-radius: 8px;")
        browse_button = QPushButton("Browse...")
        browse_button.setFixedWidth(120)
        browse_button.clicked.connect(self.browse_folder)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_path, 1)
        folder_layout.addWidget(browse_button)
        
        # Progress section
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_label = QLabel("Analyzing folder contents...")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        self.progress_container.setVisible(False)
        
        # Option to use AI
        ai_layout = QHBoxLayout()
        self.use_ai = QCheckBox("Use AI for smart categorization")
        self.use_ai.setChecked(True)
        ai_layout.addWidget(self.use_ai)
        ai_layout.addStretch()
        
        # Analyze button
        self.analyze_button = QPushButton("Analyze Folder")
        self.analyze_button.setDisabled(True)
        self.analyze_button.clicked.connect(self.start_analysis)
        
        # Add all to layout
        card_layout.addLayout(folder_layout)
        card_layout.addLayout(ai_layout)
        card_layout.addWidget(self.progress_container)
        card_layout.addWidget(self.analyze_button)
        
        layout.addLayout(title_layout)
        layout.addWidget(self.card, 1)
        layout.addStretch(1)
        
        self.setLayout(layout)
        
        # For simulating progress
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.progress_value = 0
        
    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.folder_path.setText(folder_path)
            self.analyze_button.setDisabled(False)
    
    def start_analysis(self):
        folder_path = self.folder_path.text()
        if folder_path and folder_path != "No folder selected":
            self.analyze_button.setDisabled(True)
            self.progress_container.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_value = 0
            self.timer.start(100)  # Update every 100ms
    
    def update_progress(self):
        self.progress_value += 5
        self.progress_bar.setValue(self.progress_value)
        
        if self.progress_value >= 100:
            self.timer.stop()
            folder_path = self.folder_path.text()
            use_ai = self.use_ai.isChecked()
            self.progress_container.setVisible(False)
            self.analyze_folder.emit(folder_path)

class AnalyzePage(QWidget):
    go_back = Signal()
    go_to_edit = Signal()
    go_to_confirm = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(20)
        
        # Header section
        header_layout = QVBoxLayout()
        title = QLabel("Analysis Preview")
        title.setProperty("class", "title")
        self.folder_label = QLabel("Folder: ")
        self.folder_label.setProperty("class", "subtitle")
        
        header_layout.addWidget(title)
        header_layout.addWidget(self.folder_label)
        header_layout.addSpacing(20)
        
        # Analysis display
        self.card = Card()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # AI Structure Section
        self.ai_structure_title = QLabel("AI-Generated Organization Structure")
        self.ai_structure_title.setProperty("class", "subtitle")
        self.ai_structure_title.setStyleSheet("font-weight: bold;")
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setMinimumHeight(300)
        
        # Current Files Section
        self.current_files_title = QLabel("Current Files by Type (For Reference)")
        self.current_files_title.setProperty("class", "subtitle")
        self.current_files_title.setStyleSheet("font-weight: bold;")
        
        self.file_list = QTreeWidget()
        self.file_list.setHeaderHidden(True)
        self.file_list.setMinimumHeight(200)
        
        scroll_layout.addWidget(self.ai_structure_title)
        scroll_layout.addWidget(self.tree_widget)
        scroll_layout.addWidget(self.current_files_title)
        scroll_layout.addWidget(self.file_list)
        
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        
        self.card.layout.addWidget(scroll_area)
        
        # Summary and buttons
        self.summary_label = QLabel()
        self.summary_label.setProperty("class", "subtitle")
        self.summary_label.setStyleSheet("font-size: 14px; color: #666666;")
        
        buttons_layout = QHBoxLayout()
        back_button = QPushButton("Back")
        back_button.setProperty("class", "secondary")
        back_button.clicked.connect(self.go_back.emit)
        
        edit_button = QPushButton("Edit Structure")
        edit_button.setProperty("class", "secondary")
        edit_button.clicked.connect(self.go_to_edit.emit)
        
        continue_button = QPushButton("Continue to Organize")
        continue_button.clicked.connect(self.go_to_confirm.emit)
        
        buttons_layout.addWidget(back_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(continue_button)
        
        # Add all to layout
        layout.addLayout(header_layout)
        layout.addWidget(self.card, 1)
        layout.addWidget(self.summary_label)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def set_folder_path(self, path):
        self.folder_label.setText(f"Folder: {path}")
    
    def populate_data(self, use_ai=True):
        # Clear existing data
        self.tree_widget.clear()
        self.file_list.clear()
        
        # Mock data - this would be real data in production
        # AI-generated structure
        if use_ai:
            structure = {
                "Personal": {
                    "Photos": ["vacation.jpg", "profile.png"],
                    "Documents": ["contract.docx"]
                },
                "Work": {
                    "Reports": ["report.pdf"],
                    "Notes": ["notes.txt"]
                },
                "Projects": {
                    "Website": ["app.js", "styles.css", "index.html"],
                    "Backups": ["backup.zip", "project.rar"]
                },
                "Screenshots": ["screenshot.png"]
            }
            
            # Build tree view
            for category, content in structure.items():
                category_item = QTreeWidgetItem([category])
                category_item.setIcon(0, QIcon("icons/folder.png"))
                self.tree_widget.addTopLevelItem(category_item)
                
                for subcategory, files in content.items():
                    subcategory_item = QTreeWidgetItem([subcategory])
                    subcategory_item.setIcon(0, QIcon("icons/folder.png"))
                    category_item.addChild(subcategory_item)
                    
                    for file in files:
                        file_item = QTreeWidgetItem([file])
                        file_item.setIcon(0, QIcon("icons/file.png"))
                        subcategory_item.addChild(file_item)
            
            self.tree_widget.expandAll()
            self.ai_structure_title.setVisible(True)
            self.tree_widget.setVisible(True)
            self.summary_label.setText("Found 10 file(s) across 4 categories. (AI Structure Generated)")
            
        else:
            self.ai_structure_title.setVisible(False)
            self.tree_widget.setVisible(False)
            self.summary_label.setText("Found 10 file(s) across 4 categories. (Analyzed by Extension)")
        
        # File types list
        file_types = {
            "Images": ["vacation.jpg", "profile.png", "screenshot.png"],
            "Documents": ["report.pdf", "notes.txt", "contract.docx"],
            "Code": ["app.js", "styles.css", "index.html"],
            "Archives": ["backup.zip", "project.rar"]
        }
        
        for category, files in file_types.items():
            category_item = QTreeWidgetItem([f"{category} ({len(files)})"])
            self.file_list.addTopLevelItem(category_item)
            
            for file in files:
                file_item = QTreeWidgetItem([file])
                file_item.setIcon(0, QIcon("icons/file.png"))
                category_item.addChild(file_item)
        
        self.file_list.expandAll()

class EditStructurePage(QWidget):
    go_back = Signal()
    go_to_confirm = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(20)
        
        # Header section
        header_layout = QVBoxLayout()
        title = QLabel("Edit Organization Structure")
        title.setProperty("class", "title")
        subtitle = QLabel("Customize the structure using the tree view below.")
        subtitle.setProperty("class", "subtitle")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addSpacing(20)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #007aff;")
        
        add_folder_button = QPushButton("Add Top Category")
        add_folder_button.setProperty("class", "secondary")
        add_folder_button.setIcon(QIcon("icons/add-folder.png"))
        add_folder_button.clicked.connect(self.add_top_level_folder)
        
        toolbar_layout.addWidget(add_folder_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.status_label)
        
        # Structure editor
        self.card = Card()
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setMinimumHeight(400)
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        self.card.layout.addWidget(self.tree_widget)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        back_button = QPushButton("Back")
        back_button.setProperty("class", "secondary")
        back_button.clicked.connect(self.go_back.emit)
        
        continue_button = QPushButton("Continue to Organize")
        continue_button.clicked.connect(self.go_to_confirm.emit)
        
        buttons_layout.addWidget(back_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(continue_button)
        
        # Add all to layout
        layout.addLayout(header_layout)
        layout.addLayout(toolbar_layout)
        layout.addWidget(self.card, 1)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # Status message timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.clear_status)
        self.status_timer.setSingleShot(True)
    
    def populate_tree(self, structure=None):
        self.tree_widget.clear()
        
        if not structure:
            # Default structure if none provided
            structure = {
                "Personal": {
                    "Photos": ["vacation.jpg", "profile.png"],
                    "Documents": ["contract.docx"]
                },
                "Work": {
                    "Reports": ["report.pdf"],
                    "Notes": ["notes.txt"]
                },
                "Projects": {
                    "Website": ["app.js", "styles.css", "index.html"],
                    "Backups": ["backup.zip", "project.rar"]
                },
                "Screenshots": ["screenshot.png"]
            }
        
        self._build_tree_items(structure, None)
        self.tree_widget.expandAll()
    
    def _build_tree_items(self, data, parent_item):
        for key, value in data.items():
            if parent_item is None:
                item = QTreeWidgetItem(self.tree_widget, [key])
            else:
                item = QTreeWidgetItem(parent_item, [key])
            
            item.setIcon(0, QIcon("icons/folder.png"))
            
            if isinstance(value, dict):
                self._build_tree_items(value, item)
            elif isinstance(value, list):
                for file in value:
                    file_item = QTreeWidgetItem(item, [file])
                    file_item.setIcon(0, QIcon("icons/file.png"))
    
    def add_top_level_folder(self):
        dialog = AddFolderDialog(self, "Add New Category")
        if dialog.exec():
            name = dialog.get_folder_name()
            if name:
                item = QTreeWidgetItem(self.tree_widget, [name])
                item.setIcon(0, QIcon("icons/folder.png"))
                self.set_status(f"Added new category '{name}'")
    
    def add_subfolder(self, parent_item):
        dialog = AddFolderDialog(self, "Add Subfolder")
        if dialog.exec():
            name = dialog.get_folder_name()
            if name:
                item = QTreeWidgetItem(parent_item, [name])
                item.setIcon(0, QIcon("icons/folder.png"))
                parent_item.setExpanded(True)
                self.set_status(f"Added subfolder '{name}'")
    
    def rename_folder(self, item):
        current_name = item.text(0)
        dialog = AddFolderDialog(self, "Rename Folder")
        dialog.nameEdit.setText(current_name)
        
        if dialog.exec():
            new_name = dialog.get_folder_name()
            if new_name and new_name != current_name:
                item.setText(0, new_name)
                self.set_status(f"Renamed from '{current_name}' to '{new_name}'")
    
    def delete_folder(self, item):
        name = item.text(0)
        parent = item.parent()
        
        if parent:
            index = parent.indexOfChild(item)
            parent.takeChild(index)
        else:
            index = self.tree_widget.indexOfTopLevelItem(item)
            self.tree_widget.takeTopLevelItem(index)
        
        self.set_status(f"Deleted '{name}'")
    
    def show_context_menu(self, position):
        item = self.tree_widget.itemAt(position)
        if item:
            from PySide6.QtWidgets import QMenu
            
            menu = QMenu()
            
            # Check if it's a file or folder (assume it's a file if it has no children)
            is_file = item.childCount() == 0 and item.parent() is not None
            
            if not is_file:
                add_action = menu.addAction("Add Subfolder")
                add_action.triggered.connect(lambda: self.add_subfolder(item))
                
                rename_action = menu.addAction("Rename")
                rename_action.triggered.connect(lambda: self.rename_folder(item))
                
                menu.addSeparator()
                
                delete_action = menu.addAction("Delete")
                delete_action.triggered.connect(lambda: self.delete_folder(item))
            else:
                rename_action = menu.addAction("Rename")
                rename_action.triggered.connect(lambda: self.rename_folder(item))
                
                menu.addSeparator()
                
                delete_action = menu.addAction("Delete")
                delete_action.triggered.connect(lambda: self.delete_folder(item))
            
            menu.exec(self.tree_widget.viewport().mapToGlobal(position))
    
    def set_status(self, message):
        self.status_label.setText(message)
        self.status_timer.start(3000)  # Clear after 3 seconds
    
    def clear_status(self):
        self.status_label.clear()

class ConfirmPage(QWidget):
    go_back = Signal()
    go_to_complete = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setAlignment(Qt.AlignCenter)
        
        # Card layout
        self.card = Card()
        card_layout = self.card.layout
        
        # Warning icon
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setStyleSheet("""
            background-color: #fff3cd;
            border-radius: 32px;
            padding: 16px;
        """)
        # In a real app, you would set an actual icon here
        # icon_label.setPixmap(QPixmap("warning.png").scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Title and description
        title = QLabel("Confirm Organization")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignCenter)
        
        description = QLabel("This will move files into new subfolders within the selected directory.")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        
        warning = QLabel("This action cannot be automatically undone.")
        warning.setAlignment(Qt.AlignCenter)
        warning.setStyleSheet("font-weight: bold; margin-top: 10px;")
        
        # Progress bar (initially hidden)
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        
        self.progress_label = QLabel("Organizing files...")
        self.progress_label.setAlignment(Qt.AlignCenter)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        self.progress_container.setVisible(False)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        back_button = QPushButton("Back")
        back_button.setProperty("class", "secondary")
        back_button.clicked.connect(self.go_back.emit)
        
        self.organize_button = QPushButton("Yes, Organize Now")
        self.organize_button.setStyleSheet("background-color: #ff9500;")
        self.organize_button.clicked.connect(self.start_organization)
        
        buttons_layout.addWidget(back_button)
        buttons_layout.addWidget(self.organize_button)
        
        # Add all widgets to the card
        card_layout.addWidget(icon_label, 0, Qt.AlignCenter)
        card_layout.addWidget(title, 0, Qt.AlignCenter)
        card_layout.addWidget(description, 0, Qt.AlignCenter)
        card_layout.addWidget(warning, 0, Qt.AlignCenter)
        card_layout.addWidget(self.progress_container)
        card_layout.addLayout(buttons_layout)
        
        # Fixed width for the card
        self.card.setFixedWidth(450)
        
        # Add card to main layout
        layout.addWidget(self.card, 0, Qt.AlignCenter)
        
        self.setLayout(layout)
        
        # For simulating progress
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.progress_value = 0
    
    def start_organization(self):
        self.organize_button.setDisabled(True)
        self.progress_container.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.timer.start(50)  # Update every 50ms
    
    def update_progress(self):
        self.progress_value += 2
        self.progress_bar.setValue(self.progress_value)
        self.progress_label.setText(f"Organizing files... {self.progress_value}%")
        
        if self.progress_value >= 100:
            self.timer.stop()
            # Generate organization summary
            summary = "Successfully organized 10 files into 4 categories."
            self.go_to_complete.emit(summary)

class CompletePage(QWidget):
    go_to_start = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setAlignment(Qt.AlignCenter)
        
        # Card layout
        self.card = Card()
        card_layout = self.card.layout
        
        # Success icon
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setStyleSheet("""
        background-color: #e1f7e1;
        border-radius: 32px;
        padding: 16px;
        """)
        # In a real app, you would set an actual icon here
        # icon_label.setPixmap(QPixmap("success.png").scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Title and description
        title = QLabel("Organization Complete!")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignCenter)
        
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignCenter)
        
        # Buttons
        open_button = QPushButton("Open Folder")
        open_button.clicked.connect(self.open_folder)
        
        new_button = QPushButton("Organize Another Folder")
        new_button.setProperty("class", "secondary")
        new_button.clicked.connect(self.go_to_start.emit)
        
        exit_button = QPushButton("Exit Application")
        exit_button.setProperty("class", "secondary")
        exit_button.clicked.connect(QApplication.quit)
        
        # Add all widgets to the card
        card_layout.addWidget(icon_label, 0, Qt.AlignCenter)
        card_layout.addWidget(title, 0, Qt.AlignCenter)
        card_layout.addWidget(self.summary_label, 0, Qt.AlignCenter)
        card_layout.addWidget(open_button)
        card_layout.addWidget(new_button)
        card_layout.addWidget(exit_button)
        
        # Fixed width for the card
        self.card.setFixedWidth(450)
        
        # Add card to main layout
        layout.addWidget(self.card, 0, Qt.AlignCenter)
        
        self.setLayout(layout)
        
        self.folder_path = ""
    
    def set_folder_path(self, path):
        self.folder_path = path
    
    def set_summary(self, summary):
        self.summary_label.setText(summary)
    
    def open_folder(self):
        import subprocess
        import os
        import platform
        
        if self.folder_path:
            if platform.system() == "Windows":
                os.startfile(self.folder_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", self.folder_path])
            else:  # Linux
                subprocess.call(["xdg-open", self.folder_path])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart File Organizer")
        self.setMinimumSize(800, 650)
        
        # Set central widget
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create header with theme toggle
        header = QWidget()
        header.setStyleSheet("background-color: white; border-bottom: 1px solid #e0e0e5;")
        header.setFixedHeight(60)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        logo_label = QLabel("Smart File Organizer")
        logo_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #007aff;")
        
        self.theme_button = QPushButton()
        self.theme_button.setFixedSize(40, 40)
        self.theme_button.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f7;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #e5e5e7;
            }
        """)
        # In a real app, you would set an actual icon here
        # self.theme_button.setIcon(QIcon("icons/theme.png"))
        self.theme_button.clicked.connect(self.toggle_theme)
        
        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        header_layout.addWidget(self.theme_button)
        
        # Create stacked widget for pages
        self.stacked_widget = QStackedWidget()
        
        # Create pages
        self.start_page = StartPage()
        self.analyze_page = AnalyzePage()
        self.edit_page = EditStructurePage()
        self.confirm_page = ConfirmPage()
        self.complete_page = CompletePage()
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.start_page)
        self.stacked_widget.addWidget(self.analyze_page)
        self.stacked_widget.addWidget(self.edit_page)
        self.stacked_widget.addWidget(self.confirm_page)
        self.stacked_widget.addWidget(self.complete_page)
        
        # Connect signals
        self.start_page.analyze_folder.connect(self.on_analyze_folder)
        
        self.analyze_page.go_back.connect(lambda: self.stacked_widget.setCurrentWidget(self.start_page))
        self.analyze_page.go_to_edit.connect(lambda: self.stacked_widget.setCurrentWidget(self.edit_page))
        self.analyze_page.go_to_confirm.connect(lambda: self.stacked_widget.setCurrentWidget(self.confirm_page))
        
        self.edit_page.go_back.connect(lambda: self.stacked_widget.setCurrentWidget(self.analyze_page))
        self.edit_page.go_to_confirm.connect(lambda: self.stacked_widget.setCurrentWidget(self.confirm_page))
        
        self.confirm_page.go_back.connect(lambda: self.stacked_widget.setCurrentWidget(self.edit_page))
        self.confirm_page.go_to_complete.connect(self.on_organization_complete)
        
        self.complete_page.go_to_start.connect(self.reset_app)
        
        # Add widgets to main layout
        main_layout.addWidget(header)
        main_layout.addWidget(self.stacked_widget, 1)
        
        # Set initial page
        self.stacked_widget.setCurrentWidget(self.start_page)
        
        # State
        self.folder_path = ""
        self.use_ai = True
        
        # Set application style
        self.setStyleSheet(STYLESHEET)
    
    def on_analyze_folder(self, folder_path):
        self.folder_path = folder_path
        self.use_ai = self.start_page.use_ai.isChecked()
        
        # Update analyze page
        self.analyze_page.set_folder_path(folder_path)
        self.analyze_page.populate_data(self.use_ai)
        
        # Update edit page
        self.edit_page.populate_tree()
        
        # Switch to analyze page
        self.stacked_widget.setCurrentWidget(self.analyze_page)
    
    def on_organization_complete(self, summary):
        self.complete_page.set_folder_path(self.folder_path)
        self.complete_page.set_summary(summary)
        self.stacked_widget.setCurrentWidget(self.complete_page)
    
    def reset_app(self):
        self.folder_path = ""
        self.stacked_widget.setCurrentWidget(self.start_page)
        self.start_page.folder_path.setText("No folder selected")
        self.start_page.analyze_button.setDisabled(True)
    
    def toggle_theme(self):
        # This is a placeholder for theme switching
        # In a real app, you would implement dark/light mode switching
        pass

if __name__ == "__main__":
    # Create resource directories if they don't exist
    icons_dir = Path("icons")
    icons_dir.mkdir(exist_ok=True)
    
    # Create dummy icons (would use real icons in production)
    for icon_name in ["folder.png", "file.png", "add-folder.png"]:
        icon_path = icons_dir / icon_name
        if not icon_path.exists():
            # Create a simple colored rectangle as a placeholder
            from PIL import Image, ImageDraw
            img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            if "folder" in icon_name:
                color = (0, 122, 255, 255)  # Blue for folders
            else:
                color = (100, 100, 100, 255)  # Gray for files
                
            draw.rectangle([8, 8, 56, 56], fill=color)
            img.save(icon_path)
    
    app = QApplication(sys.argv)
    
    # Load fonts (for a real app, you would bundle your fonts)
    # QFontDatabase.addApplicationFont("fonts/Inter-Regular.ttf")
    # QFontDatabase.addApplicationFont("fonts/Inter-Medium.ttf")
    # QFontDatabase.addApplicationFont("fonts/Inter-SemiBold.ttf")
    # QFontDatabase.addApplicationFont("fonts/Inter-Bold.ttf")
    
    # app.setFont(QFont("Inter", 10))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
