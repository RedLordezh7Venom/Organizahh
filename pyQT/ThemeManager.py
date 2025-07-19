class ThemeManager:
    """Manages application themes (light/dark mode)"""

    # Light Theme Colors
    LIGHT = {
        "bg_primary": "#f8f9fa",
        "bg_secondary": "#ffffff",
        "text_primary": "#2D3748",
        "text_secondary": "#718096",
        "accent": "#6C5CE7",
        "accent_hover": "#5B4BD6",
        "border": "#E2E8F0",
        "success": "#48BB78",
        "warning": "#F6AD55",
        "error": "#ED64A6",
        "card_bg": "#ffffff",
        "disabled": "#CBD5E0",
        "highlight": "#EBF4FF"
    }

    # Dark Theme Colors
    DARK = {
        "bg_primary": "#1A202C",
        "bg_secondary": "#2D3748",
        "text_primary": "#F7FAFC",
        "text_secondary": "#A0AEC0",
        "accent": "#805AD5",
        "accent_hover": "#6B46C1",
        "border": "#4A5568",
        "success": "#38A169",
        "warning": "#DD6B20",
        "error": "#E53E3E",
        "card_bg": "#2D3748",
        "disabled": "#718096",
        "highlight": "#2C5282"
    }

    def __init__(self):
        self.current_theme = "light"  # Default theme
        self.colors = self.LIGHT.copy()

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        if self.current_theme == "light":
            self.current_theme = "dark"
            self.colors = self.DARK.copy()
        else:
            self.current_theme = "light"
            self.colors = self.LIGHT.copy()
        return self.current_theme

    def set_theme(self, theme_name):
        """Set theme by name"""
        if theme_name.lower() == "dark":
            self.current_theme = "dark"
            self.colors = self.DARK.copy()
        else:
            self.current_theme = "light"
            self.colors = self.LIGHT.copy()
        return self.current_theme

    def get_stylesheet(self):
        """Generate QSS stylesheet based on current theme"""
        c = self.colors
        return f"""
        /* Base Styling */
        QWidget {{
            background-color: {c['bg_primary']};
            color: {c['text_primary']};
            font-family: 'Segoe UI', 'Arial', sans-serif;
        }}

        QMainWindow, QDialog {{
            background-color: {c['bg_primary']};
        }}

        /* Text Elements */
        QLabel {{
            color: {c['text_primary']};
            background-color: transparent;
        }}

        QLabel[title="true"] {{
            font-size: 18px;
            font-weight: bold;
        }}

        QLabel[subtitle="true"] {{
            color: {c['text_secondary']};
            font-size: 14px;
        }}

        /* Modern Buttons */
        QPushButton {{
            background-color: {c['accent']};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 13px;
            min-width: 100px;
        }}

        QPushButton:hover {{
            background-color: {c['accent_hover']};
        }}

        QPushButton:pressed {{
            background-color: {c['accent']};
        }}

        QPushButton:disabled {{
            background-color: {c['disabled']};
            color: {c['text_secondary']};
        }}

        QPushButton[secondary="true"] {{
            background-color: transparent;
            color: {c['accent']};
            border: 2px solid {c['accent']};
        }}

        QPushButton[secondary="true"]:hover {{
            background-color: {c['highlight']};
        }}

        /* Cards and Containers */
        QFrame {{
            background-color: {c['bg_secondary']};
            border-radius: 10px;
            border: none;
        }}

        QFrame[card="true"] {{
            background-color: {c['card_bg']};
            border-radius: 12px;
            padding: 20px;
        }}

        /* Tree and List Views */
        QTreeWidget, QListWidget {{
            background-color: {c['bg_secondary']};
            border: none;
            border-radius: 8px;
            padding: 8px;
        }}

        QTreeWidget::item, QListWidget::item {{
            padding: 8px;
            margin: 2px 0px;
            border-radius: 4px;
        }}

        QTreeWidget::item:hover, QListWidget::item:hover {{
            background-color: {c['highlight']};
        }}

        QTreeWidget::item:selected, QListWidget::item:selected {{
            background-color: {c['highlight']};
            color: {c['text_primary']};
        }}

        /* Combo Box */
        QComboBox {{
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 6px 12px;
            background-color: {c['bg_secondary']};
            min-width: 6em;
        }}

        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {c['bg_secondary']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            selection-background-color: {c['highlight']};
        }}

        /* Progress Indicators */
        QProgressBar {{
            border: none;
            border-radius: 4px;
            background-color: {c['border']};
            height: 8px;
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: {c['accent']};
            border-radius: 4px;
        }}

        /* Input Fields */
        QLineEdit {{
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 8px 12px;
            background-color: {c['bg_secondary']};
            selection-background-color: {c['highlight']};
        }}

        QLineEdit:focus {{
            border: 2px solid {c['accent']};
        }}

        /* Checkboxes */
        QCheckBox {{
            spacing: 8px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid {c['border']};
        }}

        QCheckBox::indicator:checked {{
            background-color: {c['accent']};
            border: 1px solid {c['accent']};
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            background: {c['bg_primary']};
            width: 12px;
            margin: 0px;
        }}

        QScrollBar::handle:vertical {{
            background: {c['border']};
            min-height: 20px;
            border-radius: 6px;
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background: {c['bg_primary']};
            height: 12px;
            margin: 0px;
        }}

        QScrollBar::handle:horizontal {{
            background: {c['border']};
            min-width: 20px;
            border-radius: 6px;
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        """
