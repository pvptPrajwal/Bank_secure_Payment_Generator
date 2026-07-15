\# TiMoCo Advisors — Bank Payment File Generator



\*\*Secure \& Efficient Payment File Generation\*\*



A professional desktop application for generating bank-ready payment files with SHA-256 master file verification.



\## Features

\- 🔐 Secure online authentication (Supabase)

\- 🏦 SHA-256 master file hash verification

\- 📊 Payment file matching engine

\- 📁 Protected Excel output generation

\- 👥 Role-based access (Administrator / User)

\- 📋 Complete audit logging

\- 🌍 Multi-city / multi-office support



\## Architecture

| Component | Where it runs |

|-----------|--------------|

| Login \& user management | Online (Supabase) |

| Master file hash verification | Online (hash only) |

| File matching \& output generation | 100% Offline (local machine) |



\## Tech Stack

\- Python 3.12+

\- PySide6 (GUI)

\- Supabase (PostgreSQL backend)

\- Pandas + OpenPyXL

\- PyInstaller (executable)



\## Setup

1\. Copy `.env.example` to `.env` and fill in your Supabase credentials

2\. Run `pip install -r requirements.txt`

3\. Run `python scripts\\create\_initial\_admin.py`

4\. Run `python main.py`

## Security
- Publishable key only — no secret key in the app
- Master file contents never leave your machine
- Account lockout after 5 failed attempts
- 15-minute idle session timeout


\## Build EXE

