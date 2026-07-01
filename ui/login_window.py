import os, sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                               QPushButton, QFrame, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from auth.auth_manager import login, AuthError
from auth.session_manager import session
from ui.styles import APP_TITLE, APP_VERSION


def _resource(name):
    base = sys._MEIPASS if getattr(sys, "frozen", False) else \
           os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "resources", name)


class LoginWindow(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(440, 420)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame(); card.setObjectName("Card"); card.setFixedWidth(380)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(12)

        # ── Logo ──
        logo_lbl = QLabel(); logo_lbl.setAlignment(Qt.AlignCenter)
        pix = QPixmap(_resource("logo.png"))
        if not pix.isNull():
            logo_lbl.setPixmap(pix.scaledToWidth(300, Qt.SmoothTransformation))
        else:
            logo_lbl.setText("Bank Payment\nFile Generator")
            logo_lbl.setObjectName("Title")
            f = QFont(); f.setPointSize(17); f.setBold(True); logo_lbl.setFont(f)
        layout.addWidget(logo_lbl)

        sub = QLabel("Secure & Efficient Payments")
        sub.setStyleSheet("color: #1A5276; font-size: 12px; font-weight: 600;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(6)

        # ── Fields ──
        layout.addWidget(QLabel("Username"))
        self.username = QLineEdit(); self.username.setPlaceholderText("Enter username")
        layout.addWidget(self.username)

        layout.addWidget(QLabel("Password"))
        self.password = QLineEdit(); self.password.setPlaceholderText("Enter password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self._login)
        layout.addWidget(self.password)

        self.error = QLabel("")
        self.error.setStyleSheet("color: #8C1D1D; font-weight: 500;")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)

        btn = QPushButton("Login"); btn.clicked.connect(self._login)
        layout.addWidget(btn)

        layout.addSpacing(4)
        ver = QLabel(f"v{APP_VERSION}  |  TiMoCo Advisors")
        ver.setStyleSheet("color: #999; font-size: 10px;")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)

        outer.addWidget(card, alignment=Qt.AlignCenter)

    def _login(self):
        u, p = self.username.text().strip(), self.password.text()
        if not u or not p:
            self.error.setText("Please enter both username and password.")
            return
        try:
            user = login(u, p)
        except AuthError as e:
            self.error.setText(str(e))
            self.password.clear()
            return
        self.error.setText("")
        session.start_session(user, p)
        self.password.clear()
        self.on_login_success(user)
