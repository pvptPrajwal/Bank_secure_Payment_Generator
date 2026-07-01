import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QHeaderView, QLineEdit
)
from auth.session_manager import session
from auth.auth_manager import logout
from audit.logger import log_action
from security.master_hash_manager import verify_against_latest, MasterHashError
from excel.master_validator import load_master_file, MasterFileError
from excel.payment_loader import load_payment_file, PaymentFileError
from excel.matching_engine import match_payments
from excel.output_generator import generate_output_file, suggested_output_path
from ui.styles import APP_TITLE


class UserDashboard(QWidget):
    def __init__(self, on_logout):
        super().__init__()
        self.on_logout = on_logout
        self.setWindowTitle(f"{APP_TITLE} — User")
        self.setMinimumSize(900, 620)
        self.master_file = None
        self.master_df   = None
        self.verified    = False
        self.payment_df  = None
        self.valid_rows  = []
        self.invalid_rows = []
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.addWidget(self._header())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_verify(),   "1. Verify Master File")
        self.tabs.addTab(self._tab_payment(),  "2. Upload Payment File")
        self.tabs.addTab(self._tab_output(),   "3. Generate Output")
        root.addWidget(self.tabs)

    def _header(self):
        bar = QFrame(); bar.setObjectName("Card")
        row = QHBoxLayout(bar)
        lbl = QLabel(f"Welcome, {session.username()}  (User)")
        lbl.setObjectName("Section"); row.addWidget(lbl); row.addStretch()
        for text, slot in [("Settings", self._settings), ("About", self._about), ("Logout", self._logout)]:
            b = QPushButton(text); b.setObjectName("Gray"); b.clicked.connect(slot); row.addWidget(b)
        return bar

    # ── Tab 1: Verify Master File ────────────────────────────────────────────

    def _tab_verify(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        info = QLabel(
            "Select your local copy of the Master Data File.\n"
            "Its SHA-256 hash will be compared with the fingerprint\n"
            "registered by the Administrator. The file contents never leave your machine."
        )
        info.setWordWrap(True); layout.addWidget(info)

        row = QHBoxLayout()
        self.master_path_lbl = QLineEdit(); self.master_path_lbl.setReadOnly(True)
        self.master_path_lbl.setPlaceholderText("No file selected")
        browse = QPushButton("Browse..."); browse.clicked.connect(self._browse_master)
        row.addWidget(self.master_path_lbl); row.addWidget(browse); layout.addLayout(row)

        btn = QPushButton("Verify Master File"); btn.clicked.connect(self._verify)
        layout.addWidget(btn)

        self.verify_status = QLabel("Status: Not verified")
        self.verify_status.setStyleSheet("font-weight: 600; padding-top: 10px;")
        layout.addWidget(self.verify_status)
        layout.addStretch()
        return tab

    def _browse_master(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Master File", "", "Excel/CSV (*.xlsx *.xls *.csv)")
        if path:
            self.master_file = path
            self.master_path_lbl.setText(path)
            self.verified = False
            self.verify_status.setText("Status: Not verified")
            self.verify_status.setStyleSheet("font-weight: 600; color: #555;")

    def _verify(self):
        if not self.master_file:
            QMessageBox.warning(self, "No File", "Please select a master file first."); return
        try:
            is_match, _ = verify_against_latest(self.master_file, session.username(), session.password())
        except MasterHashError as e:
            QMessageBox.critical(self, "Error", str(e)); return

        if not is_match:
            self.verified = False
            self.verify_status.setText("Status: ❌ ACCESS DENIED — Hash does not match")
            self.verify_status.setStyleSheet("font-weight: 600; color: #8C1D1D;")
            log_action(session.username(), "MASTER_VERIFICATION_FAILED",
                       f"Hash mismatch: {os.path.basename(self.master_file)}")
            QMessageBox.critical(self, "Access Denied",
                "This file does not match the registered master data fingerprint.\n"
                "It cannot be used for payment generation.")
            return

        try:
            self.master_df = load_master_file(self.master_file)
        except MasterFileError as e:
            QMessageBox.critical(self, "File Error", str(e)); return

        self.verified = True
        self.verify_status.setText("Status: ✅ VERIFIED — Hash matches registered master file")
        self.verify_status.setStyleSheet("font-weight: 600; color: #1F6F43;")
        log_action(session.username(), "MASTER_VERIFIED", f"File: {os.path.basename(self.master_file)}")
        QMessageBox.information(self, "Verified", "Master file verified. You may proceed.")
        self.tabs.setCurrentIndex(1)

    # ── Tab 2: Upload Payment File ───────────────────────────────────────────

    def _tab_payment(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        info = QLabel("After verifying the master file, upload the Payment Party File\n"
                      "(Party-Code, Party-Name, Amount).")
        info.setWordWrap(True); layout.addWidget(info)

        row = QHBoxLayout()
        self.payment_path_lbl = QLineEdit(); self.payment_path_lbl.setReadOnly(True)
        self.payment_path_lbl.setPlaceholderText("No file selected")
        browse = QPushButton("Browse..."); browse.clicked.connect(self._browse_payment)
        row.addWidget(self.payment_path_lbl); row.addWidget(browse); layout.addLayout(row)

        self.payment_status = QLabel("Status: No payment file loaded")
        self.payment_status.setStyleSheet("font-weight: 600; padding-top: 8px;")
        layout.addWidget(self.payment_status)

        self.payment_preview = QTableWidget(); layout.addWidget(self.payment_preview)
        return tab

    def _browse_payment(self):
        if not self.verified:
            QMessageBox.warning(self, "Not Verified", "Please verify the master file first."); return
        path, _ = QFileDialog.getOpenFileName(self, "Select Payment File", "", "Excel/CSV (*.xlsx *.xls *.csv)")
        if not path: return
        try:
            df = load_payment_file(path)
        except PaymentFileError as e:
            QMessageBox.critical(self, "File Error", str(e)); return
        self.payment_df = df
        self.payment_path_lbl.setText(path)
        self.payment_status.setText(f"Status: Loaded {len(df)} record(s)")
        self.payment_status.setStyleSheet("font-weight: 600; color: #1F6F43;")
        self._fill_table(self.payment_preview,
                         ["Party-Code", "Party-Name", "Amount"],
                         df[["Party-Code", "Party-Name", "Amount"]].to_dict("records"))

    # ── Tab 3: Generate Output ───────────────────────────────────────────────

    def _tab_output(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        btn = QPushButton("Run Matching Engine && Generate Output File")
        btn.clicked.connect(self._generate); layout.addWidget(btn)

        self.summary_lbl = QLabel("No output generated yet.")
        self.summary_lbl.setStyleSheet("font-weight: 600; padding: 8px 0;")
        layout.addWidget(self.summary_lbl)

        self.result_table = QTableWidget(); layout.addWidget(self.result_table)
        return tab

    def _generate(self):
        if not self.verified or self.master_df is None:
            QMessageBox.warning(self, "Not Verified", "Please verify the master file first.")
            self.tabs.setCurrentIndex(0); return
        if self.payment_df is None:
            QMessageBox.warning(self, "No Payment File", "Please upload a payment file first.")
            self.tabs.setCurrentIndex(1); return

        self.valid_rows, self.invalid_rows = match_payments(self.master_df, self.payment_df)

        # Ask user WHERE to save the output file
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Output File As", suggested_output_path(), "Excel Files (*.xlsx)"
        )
        if not out_path:
            return   # user cancelled — no problem
        if not out_path.lower().endswith(".xlsx"):
            out_path += ".xlsx"

        try:
            generate_output_file(self.valid_rows, self.invalid_rows, out_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate output file: {e}"); return

        log_action(session.username(), "OUTPUT_GENERATED",
                   f"Valid={len(self.valid_rows)}, Invalid={len(self.invalid_rows)}, File={os.path.basename(out_path)}")

        self.summary_lbl.setText(
            f"✅ Output saved: {len(self.valid_rows)} valid, {len(self.invalid_rows)} invalid\n{out_path}"
        )

        combined = [dict(r, Status="VALID") for r in self.valid_rows] + \
                   [dict(r, Status="INVALID") for r in self.invalid_rows]
        self._fill_table(self.result_table,
                         ["Status", "Party-Name", "Party-Code", "Bank-Account-No", "IFSC-Code", "Amount", "Reason"],
                         combined)

        QMessageBox.information(self, "Done", f"Output file saved:\n{out_path}")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _fill_table(self, table: QTableWidget, cols, rows):
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, col in enumerate(cols):
                v = row.get(col, "")
                table.setItem(r, c, QTableWidgetItem("" if v is None else str(v)))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _settings(self):
        from ui.settings_dialog import SettingsDialog
        SettingsDialog(self).exec()

    def _about(self):
        from ui.about_dialog import AboutDialog
        AboutDialog(self).exec()

    def _logout(self):
        logout(session.username()); session.end_session(); self.on_logout()
