# TiMoCo Advisors — Bank Payment File Generator(v 2.0)



\*\*Secure \& Efficient Payment File Generation\*\*



A professional desktop application for generating bank-ready payment files with SHA-256 master file verification.



## Features

\- 🔐 Secure online authentication (Supabase)

\- 🏦 SHA-256 master file hash verification

\- 📊 Payment file matching engine

\- 📁 Protected Excel output generation

\- 👥 Role-based access (Administrator / User)

\- 📋 Complete audit logging

\- 🌍 Multi-city / multi-office support



## Architecture

| Component | Where it runs |

|-----------|--------------|

| Login (Maste Admin)  --> Master Admin create Admin(Admin) --> Admin create User |

| Master file hash verification | Online (hash only) |

| File matching \& output generation | 100% Offline (local machine) |



\## Tech Stack

\- Python 3.12+

\- PySide6 (GUI)

\- Supabase (PostgreSQL backend)

\- Pandas + OpenPyXL

\- PyInstaller (executable)




## Security
- Publishable key only — no secret key in the app
- Master file contents never leave your machine
- Account lockout after 5 failed attempts
- 15-minute idle session timeout


## How to run 

0\. Copy `.env.example` to `.env` and fill in your Supabase credentials

1\. Creat virtual environment
\- python -m venv venv

2\. Activate virtual environment
\- venv\Scripts\activate

3\. Specify and install Python
\-pip install -r requirements.txt

4\. Set Pass 
\- python scripts\create_initial_admin.py

5\. Build EXE
\- python -m PyInstaller build_exe.spec
