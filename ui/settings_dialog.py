from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QMessageBox
from auth.session_manager import session
from auth import user_manager


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings — Change Password")
        self.setMinimumWidth(340)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.old_pw  = QLineEdit(); self.old_pw.setEchoMode(QLineEdit.Password)
        self.new_pw  = QLineEdit(); self.new_pw.setEchoMode(QLineEdit.Password)
        self.conf_pw = QLineEdit(); self.conf_pw.setEchoMode(QLineEdit.Password)

        form.addRow("Current Password:", self.old_pw)
        form.addRow("New Password:",     self.new_pw)
        form.addRow("Confirm New:",      self.conf_pw)
        layout.addLayout(form)

        btn = QPushButton("Update Password"); btn.clicked.connect(self._save)
        layout.addWidget(btn)

    def _save(self):
        old, new, conf = self.old_pw.text(), self.new_pw.text(), self.conf_pw.text()
        if new != conf:
            QMessageBox.warning(self, "Mismatch", "New password and confirmation do not match."); return
        try:
            user_manager.change_own_password(session.username(), old, new)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        session.update_password(new)
        QMessageBox.information(self, "Done", "Password updated successfully.")
        self.accept()
