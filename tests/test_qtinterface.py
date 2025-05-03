import pytest
import os
import json
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

# Import the module to test
import qtinterface
from qtinterface import (
    ThemeManager, show_error_message, show_warning_message, 
    show_info_message, ask_yes_no, FileOrganizerApp
)

# Fixture for QApplication instance
@pytest.fixture
def app():
    """Create a QApplication instance for tests."""
    app = QApplication([])
    yield app
    app.quit()

# Test ThemeManager
class TestThemeManager:
    def test_init(self):
        """Test ThemeManager initialization."""
        tm = ThemeManager()
        assert tm.current_theme == "light"
        assert tm.colors == tm.LIGHT.copy()
    
    def test_toggle_theme(self):
        """Test theme toggling functionality."""
        tm = ThemeManager()
        # Toggle from light to dark
        result = tm.toggle_theme()
        assert result == "dark"
        assert tm.current_theme == "dark"
        assert tm.colors == tm.DARK.copy()
        
        # Toggle from dark to light
        result = tm.toggle_theme()
        assert result == "light"
        assert tm.current_theme == "light"
        assert tm.colors == tm.LIGHT.copy()
    
    def test_set_theme(self):
        """Test setting theme by name."""
        tm = ThemeManager()
        
        # Set to dark
        result = tm.set_theme("dark")
        assert result == "dark"
        assert tm.current_theme == "dark"
        assert tm.colors == tm.DARK.copy()
        
        # Set to light
        result = tm.set_theme("light")
        assert result == "light"
        assert tm.current_theme == "light"
        assert tm.colors == tm.LIGHT.copy()
        
        # Test with uppercase
        result = tm.set_theme("DARK")
        assert result == "dark"
        
        # Test with invalid name (should default to light)
        result = tm.set_theme("invalid")
        assert result == "light"

# Test message dialog functions
@pytest.mark.usefixtures("app")
class TestMessageDialogs:
    @patch.object(QMessageBox, 'exec_')
    def test_show_error_message(self, mock_exec):
        """Test error message dialog."""
        mock_exec.return_value = QMessageBox.Ok
        show_error_message("Error Title", "Error Message")
        mock_exec.assert_called_once()
    
    @patch.object(QMessageBox, 'exec_')
    def test_show_warning_message(self, mock_exec):
        """Test warning message dialog."""
        mock_exec.return_value = QMessageBox.Ok
        show_warning_message("Warning Title", "Warning Message")
        mock_exec.assert_called_once()
    
    @patch.object(QMessageBox, 'exec_')
    def test_show_info_message(self, mock_exec):
        """Test info message dialog."""
        mock_exec.return_value = QMessageBox.Ok
        show_info_message("Info Title", "Info Message")
        mock_exec.assert_called_once()
    
    @patch.object(QMessageBox, 'exec_')
    def test_ask_yes_no_yes(self, mock_exec):
        """Test yes/no dialog with Yes response."""
        mock_exec.return_value = QMessageBox.Yes
        result = ask_yes_no("Question Title", "Question?")
        assert result is True
        mock_exec.assert_called_once()
    
    @patch.object(QMessageBox, 'exec_')
    def test_ask_yes_no_no(self, mock_exec):
        """Test yes/no dialog with No response."""
        mock_exec.return_value = QMessageBox.No
        result = ask_yes_no("Question Title", "Question?")
        assert result is False
        mock_exec.assert_called_once()

# Test FileOrganizerApp
@pytest.mark.usefixtures("app")
class TestFileOrganizerApp:
    @patch('os.path.exists')
    @patch('json.load')
    def test_load_backbone_success(self, mock_json_load, mock_exists):
        """Test successful backbone loading."""
        mock_exists.return_value = True
        mock_data = {"path1": {"category1": ["file1"]}}
        mock_json_load.return_value = mock_data
        
        app = FileOrganizerApp()
        assert app.backbone == mock_data
    
    @patch('os.path.exists')
    def test_load_backbone_not_found(self, mock_exists):
        """Test backbone file not found."""
        mock_exists.return_value = False
        
        app = FileOrganizerApp()
        assert app.backbone == {}
    
    @patch('os.path.exists')
    @patch('json.load')
    @patch('qtinterface.show_error_message')
    def test_load_backbone_json_error(self, mock_show_error, mock_json_load, mock_exists):
        """Test JSON decode error when loading backbone."""
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Test error", "", 0)
        
        app = FileOrganizerApp()
        assert app.backbone == {}
        mock_show_error.assert_called_once()
    
    def test_show_page(self):
        """Test page navigation."""
        app = FileOrganizerApp()
        
        # Mock the stacked widget and pages
        app.stacked_widget = MagicMock()
        mock_page = MagicMock()
        mock_page.on_show = MagicMock()
        app.pages = {"TestPage": mock_page}
        
        # Test showing a valid page
        app.show_page("TestPage")
        app.stacked_widget.setCurrentWidget.assert_called_once_with(mock_page)
        mock_page.on_show.assert_called_once()
        
        # Test showing an invalid page
        app.stacked_widget.reset_mock()
        app.show_page("NonExistentPage")
        app.stacked_widget.setCurrentWidget.assert_not_called()
    
    @patch('qtinterface.LANGCHAIN_AVAILABLE', True)
    def test_toggle_llm_enabled(self):
        """Test LLM toggle when available."""
        app = FileOrganizerApp()
        app.use_llm_analysis = False
        
        app.toggle_llm(True)
        assert app.use_llm_analysis is True
        
        app.toggle_llm(False)
        assert app.use_llm_analysis is False
    
    def test_reset_state(self):
        """Test state reset functionality."""
        app = FileOrganizerApp()
        
        # Set some state
        app.folder_path = "/test/path"
        app.analysis_result = {"category": ["file1"]}
        app.generated_structure = {"folder": {"subfolder": ["file2"]}}
        
        # Reset state
        app.reset_state()
        
        # Verify reset
        assert app.folder_path == ""
        assert app.analysis_result == {}
        assert app.generated_structure == {}