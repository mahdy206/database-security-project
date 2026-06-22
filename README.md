#  Secure Student Records Management System (SRMS)

A comprehensive **database security** project implementing advanced security mechanisms including Access Control (RBAC), Multilevel Security (MLS), AES-256 Encryption, Flow Control, and Inference Control in an academic records management system.

---

##  Security Features

### 1.  Access Control (RBAC)
- SQL Database Roles: Admin, Instructor, TA, Student, Guest
- All operations executed through **stored procedures**
- Fine-grained GRANT / REVOKE / DENY permission control

### 2.  Multilevel Security (MLS)
- **Bell-LaPadula Model** implementation
- 4 clearance levels: Unclassified → Confidential → Secret → Top Secret
- No Read Up (NRU) + No Write Down (NWD) enforced

### 3.  Encryption (AES-256)
- Sensitive fields encrypted at rest: grades, national IDs, phone numbers
- Passwords hashed with SHA-256
- Certificate-based symmetric key management

### 4.  Flow Control
- Triggers block writes from higher to lower classification levels
- Prevents data leakage across security boundaries
- Full audit trail for sensitive access

### 5.  Inference Control
- Query set size minimum of 3 for aggregate queries
- Restricted views for TAs and Students
- Safe stored procedures for statistical queries

---

##  User Roles

| Role | Clearance | Key Permissions |
|------|-----------|----------------|
| Admin | Top Secret (3) | Full access, manage users, approve requests |
| Instructor | Secret (2) | View/edit grades and attendance |
| TA | Confidential (1) | Attendance only (assigned courses) |
| Student | Confidential (1) | Own profile, own grades, own attendance |
| Guest | Unclassified (0) | Public course info only |

---

##  Database Schema

| Table | Classification | Encrypted Fields |
|-------|---------------|-----------------|
| Users | — | PasswordHash (SHA-256) |
| Students | Confidential | — |
| Instructors | Confidential | NationalId, Phone (AES-256) |
| Grades | Secret | GradeEncrypted (AES-256) |
| Attendance | Secret | — |
| RoleRequests | — | — |

---

##  Tech Stack

| Category | Technology |
|----------|-----------|
| Database | Microsoft SQL Server 2019+ |
| Language | Python 3.8+ |
| GUI | CustomTkinter |
| Connector | pyodbc |
| Encryption | AES-256 (SQL Server Symmetric Keys) |
| Hashing | SHA-256 |

---

##  Project Structure

```
database-security-project/
├── main.py                    ← Python GUI Application
├── SRMS_Database_Script.sql   ← Full database setup script
└── README.md
```

---

##  Getting Started

### Prerequisites
- Microsoft SQL Server 2019+
- Python 3.8+
- ODBC Driver 17 for SQL Server

### Setup

```bash
pip install customtkinter pyodbc
```

1. Run `SRMS_Database_Script.sql` on your SQL Server instance
2. Update the connection string in `main.py`
3. Run the application:

```bash
python main.py
```

> **Default Admin:** username: `admin` | password: `AdminPassword!2025`

---

##  Key Stored Procedures

| Procedure | Purpose |
|-----------|---------|
| `usp_ValidateLogin` | Authentication |
| `usp_GetGradesForUser` | MLS-enforced grade retrieval |
| `usp_InsertGrade` | Flow control enforced insert |
| `usp_SafeAvgGradeByCourse` | Inference-safe aggregation |
| `usp_ProcessRoleRequest` | Role upgrade workflow |

---
