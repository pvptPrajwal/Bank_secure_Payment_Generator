from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from ui.styles import APP_TITLE, APP_VERSION


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        title = QLabel(APP_TITLE); title.setObjectName("Title"); title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        body = QLabel(
            f"Version {APP_VERSION}\n\n"
            "Secure offline payment file generator.\n\n"
            "What stays ONLINE (Supabase):\n"
            "  • Login & user management\n"
            "  • Master file SHA-256 fingerprint\n"
            "  • Audit logs\n\n"
            "What stays OFFLINE (your machine only):\n"
            "  • Master file contents\n"
            "  • Payment file contents\n"
            "  • Matching engine\n"
            "  • Output file generation\n\n"
            "Account numbers and IFSC codes are NEVER stored or transmitted."
        )
        body.setWordWrap(True); layout.addWidget(body)
