import pytest
import os
import json
from unittest.mock import MagicMock, patch, mock_open
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

import qtinterface
from qtinterface import FileOrganizerApp, AnalysisWorker

@pytest.fixture
def app():
    """Create a QApplication instance for tests."""
    app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def file_organizer():
    """Create a FileOrganizerApp instance for tests."""
    app = FileOrganizerApp()
    yield app

@pytest.mark.usefixtures("app")
class TestAnalysisWorker:
    @patch('os.path.isdir')
    @patch('os.listdir')
    def test_run_invalid_folder(self, mock_listdir, mock_isdir):
        """Test analysis with invalid folder path."""
        mock_isdir.return_value = False
        
        controller = MagicMock()
        controller.folder_path = "/invalid/path"
        
        worker = AnalysisWorker(controller)
        worker.error = MagicMock()
        worker.finished = MagicMock()
        
        worker.run()
        
        worker.error.emit.assert_called_once()
        worker.finished.emit.assert_called_once_with(False, {}, {}, "")
    
    @patch('os.path.isdir')
    @patch('os.listdir')
    def test_run_empty_folder(self, mock_listdir, mock_isdir):
        """Test analysis with empty folder."""
        mock_isdir.return_value = True
        mock_listdir.return_value = []
        
        controller = MagicMock()
        controller.folder_path = "/test/path"
        
        worker = AnalysisWorker(controller)
        worker.error = MagicMock()
        worker.finished = MagicMock()
        worker.progress = MagicMock()
        
        worker.run()
        
        worker.error.emit.assert_called_once()
        worker.finished.emit.assert_called_once_with(False, {}, {}, "")
    
    @patch('os.path.isdir')
    @patch('os.listdir')
    @patch('os.path.normpath')
    def test_run_with_backbone(self, mock_normpath, mock_listdir, mock_isdir):
        """Test analysis using backbone."""
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.txt", "file2.py"]
        mock_normpath.return_value = "/test/path"
        
        controller = MagicMock()
        controller.folder_path = "/test/path"
        controller.backbone = {"/test/path": {"Documents": ["file1.txt"], "Code": ["file2.py"]}}
        controller._analyze_with_backbone.return_value = {
            "Documents": ["file1.txt"],
            "Code": ["file2.py"]
        }
        
        worker = AnalysisWorker(controller)
        worker.error = MagicMock()
        worker.finished = MagicMock()
        worker.progress = MagicMock()
        
        worker.run()
        
        controller._analyze_with_backbone.assert_called_once_with("/test/path")
        worker.finished.emit.assert_called_once()
        assert worker.finished.emit.call_args[0][0] is True  # success flag
    
    @patch('os.path.isdir')
    @patch('os.listdir')
    @patch('os.path.normpath')
    def test_run_without_backbone(self, mock_normpath, mock_listdir, mock_isdir):
        """Test analysis without backbone (extension-based)."""
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.txt", "file2.py"]
        mock_normpath.return_value = "/test/path"
        
        controller = MagicMock()
        controller.folder_path = "/test/path"
        controller.backbone = {}
        controller._analyze_by_extension.return_value = {
            "Text Files": ["file1.txt"],
            "Python Files": ["file2.py"]
        }
        controller.use_llm_analysis = False
        
        worker = AnalysisWorker(controller)
        worker.error = MagicMock()
        worker.finished = MagicMock()
        worker.progress = MagicMock()
        
        worker.run()
        
        controller._analyze_by_extension.assert_called_once()
        worker.finished.emit.assert_called_once()
        assert worker.finished.emit.call_args[0][0] is True  # success flag

@pytest.mark.usefixtures("app")
class TestFileOrganization:
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_organize_files(self, mock_move, mock_makedirs, mock_exists, file_organizer):
        """Test file organization process."""
        mock_exists.return_value = False
        
        file_organizer.folder_path = "/test/path"
        file_organizer.generated_structure = {
            "Documents": ["file1.txt", "file2.doc"],
            "Images": ["img1.jpg", "img2.png"]
        }
        
        # Mock the organize_files method to test its implementation
        with patch.object(file_organizer, '_organize_files') as mock_organize:
            mock_organize.return_value = (4, 0)  # 4 files moved, 0 errors
            
            result = file_organizer.organize_files()
            
            assert result == (True, "Successfully organized 4 files into 2 categories.")
            mock_organize.assert_called_once()
    
    @patch('os.path.join')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_organize_files_implementation(self, mock_move, mock_makedirs, mock_exists, mock_join, file_organizer):
        """Test the actual implementation of _organize_files."""
        # Setup mocks
        mock_exists.return_value = False
        mock_join.side_effect = lambda *args: '/'.join(args)
        
        file_organizer.folder_path = "/test/path"
        file_organizer.generated_structure = {
            "Documents": ["file1.txt"]
        }
        
        # Call the actual implementation
        result = file_organizer._organize_files(file_organizer.generated_structure)
        
        # Verify results
        assert mock_makedirs.called
        assert mock_move.called
        assert isinstance(result, tuple)
        assert len(result) == 2  # (success_count, error_count)