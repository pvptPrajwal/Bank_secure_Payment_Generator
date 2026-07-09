"""
ui/admin_dashboard.py — Company Admin dashboard.
Manages ONLY the users of the admin's own company (isolation is
enforced server-side). Also uploads the company's master file hash.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QHeaderView, QLineEdit, QFormLayout, QInputDialog
)
from auth.session_manager import session
from auth.auth_manager import logout
from auth import user_manager
from security.master_hash_manager import upload_master_file, get_all_versions, MasterHashError
from ui.styles import APP_TITLE


class AdminDashboard(QWidget):
    def __init__(self, on_logout):
        super().__init__()
        self.on_logout = on_logout
        company = session.company_name()
        self.setWindowTitle(f"{APP_TITLE} — {company} Admin")
        self.setMinimumSize(960, 660)
        self._build()
        self._refresh_users()
        self._refresh_audit()
        self._refresh_versions()

    def _build(self):
        root = QVBoxLayout(self)
        root.addWidget(self._header())
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_create_user(),   "Create User")
        self.tabs.addTab(self._tab_manage_users(),  "Manage Users")
        self.tabs.addTab(self._tab_master(),        "Upload Master File")
        self.tabs.addTab(self._tab_audit(),         "Audit Logs")
        self.tabs.currentChanged.connect(self._tab_changed)
        root.addWidget(self.tabs)

    def _header(self):
        bar = QFrame(); bar.setObjectName("Card")
        row = QHBoxLayout(bar)
        lbl = QLabel(f"Welcome, {session.username()}  — Admin, {session.company_name()}")
        lbl.setObjectName("Section"); row.addWidget(lbl); row.addStretch()
        for text, slot in [("Settings", self._settings), ("About", self._about), ("Logout", self._logout)]:
            b = QPushButton(text); b.setObjectName("Gray"); b.clicked.connect(slot); row.addWidget(b)
        return bar

    # ── Create User ──────────────────────────────────────────────────────────

    def _tab_create_user(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        info = QLabel(f"New users will be created inside your company: {session.company_name()}")
        layout.addWidget(info)
        card = QFrame(); card.setObjectName("Card"); card.setMaximumWidth(420)
        form = QFormLayout(card)
        self.new_username = QLineEdit()
        self.new_password = QLineEdit(); self.new_password.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", self.new_username)
        form.addRow("Password:", self.new_password)
        btn = QPushButton("Create User"); btn.clicked.connect(self._create_user)
        form.addRow(btn)
        layout.addWidget(card); layout.addStretch()
        return tab

    def _create_user(self):
        u, p = self.new_username.text().strip(), self.new_password.text()
        try:
            user_manager.create_user(session.username(), session.password(), u, p)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Done", f"User '{u}' created.")
        self.new_username.clear(); self.new_password.clear()
        self._refresh_users()

    # ── Manage Users ─────────────────────────────────────────────────────────

    def _tab_manage_users(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        self.users_table = QTableWidget(); layout.addWidget(self.users_table)
        row = QHBoxLayout()
        for text, slot, name in [("Disable",              lambda: self._user_action("disable"), "Danger"),
                                  ("Enable",               lambda: self._user_action("enable"),  ""),
                                  ("Reset Password",       self._reset_pw,                        "Gray"),
                                  ("Delete User (Permanent)", self._delete_user,                  "Danger"),
                                  ("Refresh",              self._refresh_users,                   "Gray")]:
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
        cols = ["ID", "Username", "Active", "Failed Attempts", "Created", "Last Login"]
        self.users_table.setColumnCount(len(cols))
        self.users_table.setHorizontalHeaderLabels(cols)
        self.users_table.setRowCount(len(users))
        for r, u in enumerate(users):
            for c, v in enumerate([u["id"], u["username"], "Yes" if u["is_active"] else "No",
                                    u["failed_attempts"], u["created_at"], u["last_login"] or "-"]):
                self.users_table.setItem(r, c, QTableWidgetItem(str(v)))
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)

    def _selected_user(self):
        row = self.users_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a user first."); return None
        return self.users_table.item(row, 1).text()

    def _user_action(self, action):
        u = self._selected_user()
        if not u: return
        try:
            user_manager.manage_user(session.username(), session.password(), u, action)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        self._refresh_users()

    def _reset_pw(self):
        u = self._selected_user()
        if not u: return
        pw, ok = QInputDialog.getText(self, "Reset Password", f"New password for '{u}':", QLineEdit.Password)
        if not ok or not pw: return
        try:
            user_manager.manage_user(session.username(), session.password(), u, "reset_password", pw)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Done", f"Password reset for '{u}'.")
        self._refresh_users()

    def _delete_user(self):
        u = self._selected_user()
        if not u: return
        c1 = QMessageBox.question(self, "Confirm Delete",
            f"PERMANENTLY delete user '{u}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if c1 != QMessageBox.Yes: return
        c2 = QMessageBox.warning(self, "Final Confirmation",
            f"FINAL WARNING: delete '{u}' forever?",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if c2 != QMessageBox.Yes: return
        try:
            user_manager.manage_user(session.username(), session.password(), u, "delete")
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Deleted", f"User '{u}' permanently deleted.")
        self._refresh_users()

    # ── Master File ──────────────────────────────────────────────────────────

    def _tab_master(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        info = QLabel(
            f"Upload the Master Data File for {session.company_name()}.\n"
            "Only its SHA-256 fingerprint is stored — file contents never leave your machine."
        )
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
            QMessageBox.warning(self, "No File", "Select a file first."); return
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

    # ── Audit ────────────────────────────────────────────────────────────────

    def _tab_audit(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        btn = QPushButton("Refresh"); btn.setObjectName("Gray"); btn.clicked.connect(self._refresh_audit)
        layout.addWidget(btn)
        self.audit_table = QTableWidget(); layout.addWidget(self.audit_table)
        return tab

    def _refresh_audit(self):
        from database import api_client
        try:
            logs = api_client.admin_list_audit_logs(session.username(), session.password(), 500)
        except api_client.ApiError as e:
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

    def _tab_changed(self, idx):
        name = self.tabs.tabText(idx)
        if name == "Manage Users": self._refresh_users()
        elif name == "Audit Logs": self._refresh_audit()
        elif name == "Upload Master File": self._refresh_versions()

    def _settings(self):
        from ui.settings_dialog import SettingsDialog
        SettingsDialog(self).exec()

    def _about(self):
        from ui.about_dialog import AboutDialog
        AboutDialog(self).exec()

    def _logout(self):
        logout(session.username()); session.end_session(); self.on_logout()
