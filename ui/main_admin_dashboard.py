"""
ui/main_admin_dashboard.py
----------------------------
Dashboard for the MainAdmin (software company owner).
Tabs: Companies | Company Admins | Audit Logs (all companies)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QMessageBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QHeaderView, QLineEdit, QComboBox, QFormLayout, QInputDialog
)
from auth.session_manager import session
from auth.auth_manager import logout
from auth import user_manager
from ui.styles import APP_TITLE


class MainAdminDashboard(QWidget):
    def __init__(self, on_logout):
        super().__init__()
        self.on_logout = on_logout
        self.setWindowTitle(f"{APP_TITLE} — Main Admin")
        self.setMinimumSize(1000, 680)
        self._build()
        self._refresh_companies()
        self._refresh_admins()
        self._refresh_audit()

    def _build(self):
        root = QVBoxLayout(self)
        root.addWidget(self._header())
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_companies(),  "Companies")
        self.tabs.addTab(self._tab_admins(),     "Company Admins")
        self.tabs.addTab(self._tab_audit(),      "Audit Logs (All)")
        self.tabs.currentChanged.connect(self._tab_changed)
        root.addWidget(self.tabs)

    def _header(self):
        bar = QFrame(); bar.setObjectName("Card")
        row = QHBoxLayout(bar)
        lbl = QLabel(f"Welcome, {session.username()}  (Main Admin — Software Owner)")
        lbl.setObjectName("Section"); row.addWidget(lbl); row.addStretch()
        for text, slot in [("Settings", self._settings), ("About", self._about), ("Logout", self._logout)]:
            b = QPushButton(text); b.setObjectName("Gray"); b.clicked.connect(slot); row.addWidget(b)
        return bar

    # ── Companies tab ────────────────────────────────────────────────────────

    def _tab_companies(self):
        tab = QWidget(); layout = QVBoxLayout(tab)

        # New-company form
        card = QFrame(); card.setObjectName("Card"); card.setMaximumWidth(480)
        form = QFormLayout(card)
        self.c_name  = QLineEdit(); self.c_name.setPlaceholderText("e.g. ABC Traders Pvt Ltd")
        self.c_admin = QLineEdit(); self.c_admin.setPlaceholderText("Company admin username")
        self.c_pw    = QLineEdit(); self.c_pw.setEchoMode(QLineEdit.Password)
        form.addRow("Company Name:",   self.c_name)
        form.addRow("Admin Username:", self.c_admin)
        form.addRow("Admin Password:", self.c_pw)
        btn = QPushButton("Create Company + Admin"); btn.clicked.connect(self._create_company)
        form.addRow(btn)
        layout.addWidget(card)

        layout.addWidget(QLabel("All Companies:"))
        self.companies_table = QTableWidget()
        layout.addWidget(self.companies_table)

        row = QHBoxLayout()
        for text, slot, name in [("Deactivate Company", self._deactivate_company, "Danger"),
                                  ("Activate Company",   self._activate_company,   ""),
                                  ("Refresh",            self._refresh_companies,  "Gray")]:
            b = QPushButton(text)
            if name: b.setObjectName(name)
            b.clicked.connect(slot); row.addWidget(b)
        row.addStretch(); layout.addLayout(row)
        return tab

    def _create_company(self):
        name, admin, pw = self.c_name.text().strip(), self.c_admin.text().strip(), self.c_pw.text()
        try:
            user_manager.create_company(session.username(), session.password(), name, admin, pw)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Done",
            f"Company '{name}' created with admin '{admin}'.\n"
            "Share the admin credentials with the company owner securely.")
        self.c_name.clear(); self.c_admin.clear(); self.c_pw.clear()
        self._refresh_companies(); self._refresh_admins()

    def _refresh_companies(self):
        try:
            companies = user_manager.list_companies(session.username(), session.password())
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        cols = ["ID", "Company Name", "Active", "Admins", "Users", "Created"]
        self.companies_table.setColumnCount(len(cols))
        self.companies_table.setHorizontalHeaderLabels(cols)
        self.companies_table.setRowCount(len(companies))
        for r, c in enumerate(companies):
            for i, v in enumerate([c["id"], c["name"], "Yes" if c["is_active"] else "No",
                                    c["admins"] or "-", c["user_count"], c["created_at"]]):
                self.companies_table.setItem(r, i, QTableWidgetItem(str(v)))
        self.companies_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.companies_table.setSelectionBehavior(QTableWidget.SelectRows)

    def _selected_company_id(self):
        row = self.companies_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a company first."); return None
        return int(self.companies_table.item(row, 0).text())

    def _deactivate_company(self):
        cid = self._selected_company_id()
        if cid is None: return
        name = self.companies_table.item(self.companies_table.currentRow(), 1).text()
        confirm = QMessageBox.question(self, "Confirm",
            f"Deactivate company '{name}'?\n\nALL its admins and users will be blocked from logging in.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm != QMessageBox.Yes: return
        try:
            user_manager.set_company_active(session.username(), session.password(), cid, False)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        self._refresh_companies()

    def _activate_company(self):
        cid = self._selected_company_id()
        if cid is None: return
        try:
            user_manager.set_company_active(session.username(), session.password(), cid, True)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        self._refresh_companies()

    # ── Company Admins tab ───────────────────────────────────────────────────

    def _tab_admins(self):
        tab = QWidget(); layout = QVBoxLayout(tab)

        card = QFrame(); card.setObjectName("Card"); card.setMaximumWidth(480)
        form = QFormLayout(card)
        self.a_company = QComboBox()
        self.a_user = QLineEdit(); self.a_pw = QLineEdit(); self.a_pw.setEchoMode(QLineEdit.Password)
        form.addRow("Company:",  self.a_company)
        form.addRow("Username:", self.a_user)
        form.addRow("Password:", self.a_pw)
        btn = QPushButton("Add Admin to Company"); btn.clicked.connect(self._create_admin)
        form.addRow(btn)
        layout.addWidget(card)

        layout.addWidget(QLabel("All Company Admins:"))
        self.admins_table = QTableWidget()
        layout.addWidget(self.admins_table)

        row = QHBoxLayout()
        for text, slot, name in [("Disable",         lambda: self._admin_action("disable"), "Danger"),
                                  ("Enable",          lambda: self._admin_action("enable"),  ""),
                                  ("Reset Password",  self._admin_reset_pw,                   "Gray"),
                                  ("Delete Admin",    self._admin_delete,                     "Danger"),
                                  ("Refresh",         self._refresh_admins,                   "Gray")]:
            b = QPushButton(text)
            if name: b.setObjectName(name)
            b.clicked.connect(slot); row.addWidget(b)
        row.addStretch(); layout.addLayout(row)
        return tab

    def _create_admin(self):
        if self.a_company.count() == 0:
            QMessageBox.warning(self, "No Companies", "Create a company first."); return
        cid = self.a_company.currentData()
        u, p = self.a_user.text().strip(), self.a_pw.text()
        try:
            user_manager.create_company_admin(session.username(), session.password(), cid, u, p)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Done", f"Admin '{u}' added.")
        self.a_user.clear(); self.a_pw.clear()
        self._refresh_admins()

    def _refresh_admins(self):
        try:
            admins = user_manager.list_admins(session.username(), session.password())
            companies = user_manager.list_companies(session.username(), session.password())
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return

        # Populate company dropdown
        self.a_company.clear()
        for c in companies:
            self.a_company.addItem(f"{c['name']} (id {c['id']})", c["id"])

        cols = ["Username", "Company", "Active", "Failed Attempts", "Created", "Last Login"]
        self.admins_table.setColumnCount(len(cols))
        self.admins_table.setHorizontalHeaderLabels(cols)
        self.admins_table.setRowCount(len(admins))
        for r, a in enumerate(admins):
            for i, v in enumerate([a["username"], a["company_name"],
                                    "Yes" if a["is_active"] else "No",
                                    a["failed_attempts"], a["created_at"], a["last_login"] or "-"]):
                self.admins_table.setItem(r, i, QTableWidgetItem(str(v)))
        self.admins_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.admins_table.setSelectionBehavior(QTableWidget.SelectRows)

    def _selected_admin(self):
        row = self.admins_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select an admin first."); return None
        return self.admins_table.item(row, 0).text()

    def _admin_action(self, action):
        u = self._selected_admin()
        if not u: return
        try:
            user_manager.manage_admin(session.username(), session.password(), u, action)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        self._refresh_admins()

    def _admin_reset_pw(self):
        u = self._selected_admin()
        if not u: return
        pw, ok = QInputDialog.getText(self, "Reset Password", f"New password for '{u}':", QLineEdit.Password)
        if not ok or not pw: return
        try:
            user_manager.manage_admin(session.username(), session.password(), u, "reset_password", pw)
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Done", f"Password reset for '{u}'.")
        self._refresh_admins()

    def _admin_delete(self):
        u = self._selected_admin()
        if not u: return
        confirm = QMessageBox.warning(self, "Confirm Delete",
            f"PERMANENTLY delete company admin '{u}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if confirm != QMessageBox.Yes: return
        try:
            user_manager.manage_admin(session.username(), session.password(), u, "delete")
        except user_manager.UserManagerError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        self._refresh_admins()

    # ── Audit tab ────────────────────────────────────────────────────────────

    def _tab_audit(self):
        tab = QWidget(); layout = QVBoxLayout(tab)

        # Filter row
        from PySide6.QtWidgets import QDateEdit, QComboBox
        from PySide6.QtCore import QDate
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("From:"))
        self.audit_from = QDateEdit()
        self.audit_from.setCalendarPopup(True)
        self.audit_from.setDisplayFormat("yyyy-MM-dd")
        self.audit_from.setDate(QDate.currentDate().addDays(-7))
        filter_row.addWidget(self.audit_from)

        filter_row.addWidget(QLabel("To:"))
        self.audit_to = QDateEdit()
        self.audit_to.setCalendarPopup(True)
        self.audit_to.setDisplayFormat("yyyy-MM-dd")
        self.audit_to.setDate(QDate.currentDate())
        filter_row.addWidget(self.audit_to)

        filter_row.addWidget(QLabel("Company:"))
        self.audit_company = QComboBox()
        self.audit_company.addItem("All Companies", None)
        filter_row.addWidget(self.audit_company)

        apply_btn = QPushButton("Apply Filters"); apply_btn.clicked.connect(self._refresh_audit)
        filter_row.addWidget(apply_btn)

        reset_btn = QPushButton("Reset"); reset_btn.setObjectName("Gray")
        reset_btn.clicked.connect(self._reset_audit_filters)
        filter_row.addWidget(reset_btn)

        filter_row.addStretch()

        purge_btn = QPushButton("Purge Old Logs..."); purge_btn.setObjectName("Danger")
        purge_btn.clicked.connect(self._purge_logs)
        filter_row.addWidget(purge_btn)

        layout.addLayout(filter_row)

        self.audit_status = QLabel("")
        self.audit_status.setStyleSheet("color: #555; font-size: 11px; padding: 2px 0;")
        layout.addWidget(self.audit_status)

        self.audit_table = QTableWidget(); layout.addWidget(self.audit_table)
        return tab

    def _reset_audit_filters(self):
        from PySide6.QtCore import QDate
        self.audit_from.setDate(QDate.currentDate().addDays(-7))
        self.audit_to.setDate(QDate.currentDate())
        self.audit_company.setCurrentIndex(0)
        self._refresh_audit()

    def _purge_logs(self):
        from PySide6.QtWidgets import QInputDialog
        days, ok = QInputDialog.getInt(
            self, "Purge Old Logs",
            "Delete audit logs older than how many days?\n"
            "(Recommended: 90. This cannot be undone.)",
            90, 1, 3650, 1
        )
        if not ok:
            return
        confirm = QMessageBox.warning(
            self, "Confirm Purge",
            f"Permanently delete ALL audit logs older than {days} days?\n\n"
            "This cannot be undone.",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel
        )
        if confirm != QMessageBox.Yes:
            return
        from database import api_client
        try:
            n = api_client.main_purge_old_logs(session.username(), session.password(), days)
        except api_client.ApiError as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Done", f"Deleted {n} log entries older than {days} days.")
        self._refresh_audit()

    def _refresh_audit(self):
        from database import api_client
        # Refresh company filter dropdown from current company list
        current_selection = self.audit_company.currentData() if hasattr(self, "audit_company") else None
        try:
            companies = user_manager.list_companies(session.username(), session.password())
        except user_manager.UserManagerError:
            companies = []
        self.audit_company.blockSignals(True)
        self.audit_company.clear()
        self.audit_company.addItem("All Companies", None)
        for c in companies:
            self.audit_company.addItem(c["name"], c["id"])
        # restore previous selection if still present
        idx = self.audit_company.findData(current_selection)
        if idx >= 0:
            self.audit_company.setCurrentIndex(idx)
        self.audit_company.blockSignals(False)

        from_str = self.audit_from.date().toString("yyyy-MM-dd")
        to_str = self.audit_to.date().toString("yyyy-MM-dd")
        cid = self.audit_company.currentData()

        try:
            logs = api_client.main_list_audit_logs(
                session.username(), session.password(),
                from_date=from_str, to_date=to_str, company_id=cid, limit=500
            )
        except api_client.ApiError as e:
            QMessageBox.critical(self, "Error", str(e)); return

        filter_note = f"From {from_str} to {to_str}"
        if cid is not None:
            filter_note += f" | Company: {self.audit_company.currentText()}"
        self.audit_status.setText(f"{filter_note}  |  {len(logs)} log(s) shown")

        cols = ["ID", "Company", "Username", "Action", "Description", "Timestamp", "Machine"]
        self.audit_table.setColumnCount(len(cols))
        self.audit_table.setHorizontalHeaderLabels(cols)
        self.audit_table.setRowCount(len(logs))
        for r, l in enumerate(logs):
            for i, v in enumerate([l["id"], l["company_name"] or "SYSTEM", l["username"],
                                    l["action"], l["description"], l["timestamp"], l["machine_name"]]):
                self.audit_table.setItem(r, i, QTableWidgetItem(str(v)))
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _tab_changed(self, idx):
        name = self.tabs.tabText(idx)
        if name == "Companies": self._refresh_companies()
        elif name == "Company Admins": self._refresh_admins()
        elif name.startswith("Audit"): self._refresh_audit()

    def _settings(self):
        from ui.settings_dialog import SettingsDialog
        SettingsDialog(self).exec()

    def _about(self):
        from ui.about_dialog import AboutDialog
        AboutDialog(self).exec()

    def _logout(self):
        logout(session.username()); session.end_session(); self.on_logout()
