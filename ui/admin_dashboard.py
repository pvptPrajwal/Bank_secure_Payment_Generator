from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QHeaderView, QLineEdit, QComboBox, QFormLayout, QInputDialog
)
from PySide6.QtCore import Qt
from auth.session_manager import session
from auth.auth_manager import logout
from auth import user_manager
from audit.logger import get_logs
from security.master_hash_manager import upload_master_file, get_all_versions, MasterHashError
from ui.styles import APP_TITLE


class AdminDashboard(QWidget):
    def __init__(self, on_logout):
        super().__init__()
        self.on_logout = on_logout
        self.setWindowTitle(f"{APP_TITLE} — Administrator")
        self.setMinimumSize(960, 660)
        self._build()
        self._refresh_users()
        self._refresh_audit()
        self._refresh_versions()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.addWidget(self._header())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_create_user(),    "Create User")
        self.tabs.addTab(self._tab_manage_users(),   "Manage Users")
        self.tabs.addTab(self._tab_master_upload(),  "Upload Master File")
        self.tabs.addTab(self._tab_audit_logs(),     "Audit Logs")
        self.tabs.currentChanged.connect(self._tab_changed)
        root.addWidget(self.tabs)

    def _header(self):
        bar = QFrame(); bar.setObjectName("Card")
        row = QHBoxLayout(bar)
        lbl = QLabel(f"Welcome, {session.username()}  (Administrator)")
        lbl.setObjectName("Section"); row.addWidget(lbl); row.addStretch()
        for text, slot, name in [("Settings", self._settings, "Gray"),
                                  ("About",    self._about,    "Gray"),
                                  ("Logout",   self._logout,   "Gray")]:
            b = QPushButton(text); b.setObjectName(name); b.clicked.connect(slot)
            row.addWidget(b)
        return bar

    # ── Create User tab ──────────────────────────────────────────────────────

    def _tab_create_user(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        card = QFrame(); card.setObjectName("Card"); card.setMaximumWidth(420)
        form = QFormLayout(card)

        self.new_username = QLineEdit()
        self.new_password = QLineEdit(); self.new_password.setEchoMode(QLineEdit.Password)
        self.new_role = QComboBox(); self.new_role.addItems(["User", "Administrator"])

        form.addRow("Username:", self.new_username)
        form.addRow("Password:", self.new_password)
        form.addRow("Role:",     self.new_role)

        btn = QPushButton("Create User"); btn.clicked.connect(self._create_user)
        form.addRow(btn)

        layout.addWidget(card); layout.addStretch()
        return tab

    def _create_user(self):
        u, p, r = self.new_username.text().strip(), self.new_password.text(), self.new_role.currentText()
        try:
            user_manager.create_user(session.username(), session.password(), u, p, r)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Done", f"User '{u}' created.")
        self.new_username.clear(); self.new_password.clear()
        self._refresh_users()

    # ── Manage Users tab ─────────────────────────────────────────────────────

    def _tab_manage_users(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        self.users_table = QTableWidget(); layout.addWidget(self.users_table)

        row = QHBoxLayout()
        for text, slot, name in [("Disable Selected",        self._disable,   "Danger"),
                                  ("Enable Selected",         self._enable,    ""),
                                  ("Reset Password",          self._reset_pw,  "Gray"),
                                  ("Delete User (Permanent)", self._delete,    "Danger"),
                                  ("Refresh",                 self._refresh_users, "Gray")]:
            b = QPushButton(text)
            if name: b.setObjectName(name)
            b.clicked.connect(slot); row.addWidget(b)
        row.addStretch(); layout.addLayout(row)
        return tab

    def _refresh_users(self):
        try:
            users = user_manager.list_users(session.username(), session.password())
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        cols = ["ID", "Username", "Role", "Active", "Failed Attempts", "Created At", "Last Login"]
        self.users_table.setColumnCount(len(cols))
        self.users_table.setHorizontalHeaderLabels(cols)
        self.users_table.setRowCount(len(users))
        for r, u in enumerate(users):
            for c, v in enumerate([u["id"], u["username"], u["role"],
                                    "Yes" if u["is_active"] else "No",
                                    u["failed_attempts"], u["created_at"], u["last_login"] or "-"]):
                self.users_table.setItem(r, c, QTableWidgetItem(str(v)))
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)

    def _selected_username(self):
        row = self.users_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a user first."); return None
        return self.users_table.item(row, 1).text()

    def _disable(self):
        u = self._selected_username()
        if not u: return
        if u == session.username():
            QMessageBox.warning(self, "Not Allowed", "Cannot disable your own account."); return
        try: user_manager.disable_user(session.username(), session.password(), u)
        except user_manager.UserManagerError as e: QMessageBox.critical(self, "Error", str(e)); return
        self._refresh_users()

    def _enable(self):
        u = self._selected_username()
        if not u: return
        try: user_manager.enable_user(session.username(), session.password(), u)
        except user_manager.UserManagerError as e: QMessageBox.critical(self, "Error", str(e)); return
        self._refresh_users()

    def _reset_pw(self):
        u = self._selected_username()
        if not u: return
        new_pw, ok = QInputDialog.getText(self, "Reset Password", f"New password for '{u}':", QLineEdit.Password)
        if not ok or not new_pw: return
        try: user_manager.reset_password(session.username(), session.password(), u, new_pw)
        except user_manager.UserManagerError as e: QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Done", f"Password reset for '{u}'.")
        self._refresh_users()

    def _delete(self):
        u = self._selected_username()
        if not u: return
        if u == session.username():
            QMessageBox.warning(self, "Not Allowed", "Cannot delete your own account."); return

        # Double confirmation for permanent delete
        confirm1 = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to PERMANENTLY delete user '{u}'?\n\n"
            "This cannot be undone. All audit logs for this user will remain,\n"
            "but the user will no longer be able to log in.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm1 != QMessageBox.Yes:
            return

        confirm2 = QMessageBox.warning(
            self, "Final Confirmation",
            f"FINAL WARNING: Permanently delete '{u}'?\n\nThis action is IRREVERSIBLE.",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel
        )
        if confirm2 != QMessageBox.Yes:
            return

        try:
            user_manager.delete_user(session.username(), session.password(), u)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return

        QMessageBox.information(self, "Deleted", f"User '{u}' has been permanently deleted.")
        self._refresh_users()

    # ── Upload Master File tab ───────────────────────────────────────────────

    def _tab_master_upload(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        info = QLabel("Upload the Master Data File. Only its SHA-256 fingerprint is stored — "
                      "the file contents never leave your machine.")
        info.setWordWrap(True); layout.addWidget(info)

        row = QHBoxLayout()
        self.master_path = QLineEdit(); self.master_path.setReadOnly(True)
        self.master_path.setPlaceholderText("No file selected")
        browse = QPushButton("Browse..."); browse.clicked.connect(self._browse_master)
        row.addWidget(self.master_path); row.addWidget(browse); layout.addLayout(row)

        upload = QPushButton("Generate Hash && Register Master File")
        upload.clicked.connect(self._upload_master); layout.addWidget(upload)

        layout.addWidget(QLabel("Version History:"))
        self.versions_table = QTableWidget(); layout.addWidget(self.versions_table)
        self._master_file = None
        return tab

    def _browse_master(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Master File", "", "Excel/CSV (*.xlsx *.xls *.csv)")
        if path:
            self._master_file = path; self.master_path.setText(path)

    def _upload_master(self):
        if not self._master_file:
            QMessageBox.warning(self, "No File", "Please select a file first."); return
        try:
            row = upload_master_file(self._master_file, session.username(), session.password())
        except MasterHashError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Registered",
            f"Master file registered as version {row['version']}.\nSHA-256: {row['hash_value']}")
        self.master_path.clear(); self._master_file = None
        self._refresh_versions()

    def _refresh_versions(self):
        try:
            versions = get_all_versions(session.username(), session.password())
        except MasterHashError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        cols = ["Version", "SHA-256 Hash", "Uploaded By", "Uploaded At"]
        self.versions_table.setColumnCount(len(cols))
        self.versions_table.setHorizontalHeaderLabels(cols)
        self.versions_table.setRowCount(len(versions))
        for r, v in enumerate(versions):
            for c, val in enumerate([v["version"], v["hash_value"], v["uploaded_by"], v["uploaded_at"]]):
                self.versions_table.setItem(r, c, QTableWidgetItem(str(val)))
        self.versions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    # ── Audit Logs tab ───────────────────────────────────────────────────────

    def _tab_audit_logs(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        btn = QPushButton("Refresh"); btn.setObjectName("Gray"); btn.clicked.connect(self._refresh_audit)
        layout.addWidget(btn)
        self.audit_table = QTableWidget(); layout.addWidget(self.audit_table)
        return tab

    def _refresh_audit(self):
        try:
            logs = get_logs(session.username(), session.password(), limit=500)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e)); return
        cols = ["ID", "Username", "Action", "Description", "Timestamp", "Machine"]
        self.audit_table.setColumnCount(len(cols))
        self.audit_table.setHorizontalHeaderLabels(cols)
        self.audit_table.setRowCount(len(logs))
        for r, l in enumerate(logs):
            for c, v in enumerate([l["id"], l["username"], l["action"],
                                    l["description"], l["timestamp"], l["machine_name"]]):
                self.audit_table.setItem(r, c, QTableWidgetItem(str(v)))
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    # ── Tab change ───────────────────────────────────────────────────────────

    def _tab_changed(self, idx):
        name = self.tabs.tabText(idx)
        if name == "Manage Users": self._refresh_users()
        elif name == "Audit Logs": self._refresh_audit()
        elif name == "Upload Master File": self._refresh_versions()

    # ── Header buttons ───────────────────────────────────────────────────────

    def _settings(self):
        from ui.settings_dialog import SettingsDialog
        SettingsDialog(self).exec()

    def _about(self):
        from ui.about_dialog import AboutDialog
        AboutDialog(self).exec()

    def _logout(self):
        logout(session.username()); session.end_session(); self.on_logout()
