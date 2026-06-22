# \# Secure Student Records Management System (SRMS)

# 

# A comprehensive database security project implementing advanced security mechanisms including Access Control, Multilevel Security (MLS), Encryption, Flow Control, and Inference Control in an academic records management system.

# 

# ---

# 

# \## Table of Contents

# 

# \- \[Overview](#overview)

# \- \[Security Features](#security-features)

# \- \[Database Schema](#database-schema)

# \- \[User Roles](#user-roles)

# \- \[Security Implementation](#security-implementation)

# \- \[License](#license)

# 

# ---

# 

# \## Overview

# 

# The \*\*Secure Student Records Management System (SRMS)\*\* is an academic project designed to demonstrate advanced database security concepts in a real-world scenario. The system manages highly sensitive academic data including student profiles, grades, attendance records, and staff information with multiple layers of security protection.

# 

# \### Key Objectives

# 

# \-  Design and implement a secure SQL Server database schema

# \-  Develop a role-based GUI desktop application

# \-  Enforce RBAC (Role-Based Access Control)

# \-  Implement Multilevel Security using Bell-LaPadula model

# \-  Apply AES-256 encryption for sensitive data

# \-  Prevent inference attacks through query set size control

# \-  Enforce flow control to prevent data leakage

# \-  Implement secure role upgrade request workflow

# 

# ---

# 

# \##  Security Features

# 

# \### 1. \*\*Access Control (RBAC)\*\*

# \- \*\*SQL Database Roles\*\*: Admin, Instructor, TA, Student, Guest

# \- \*\*Stored Procedures\*\*: All operations executed through secure stored procedures

# \- \*\*Permission Matrix\*\*: Role-based visibility and operations enforcement

# \- \*\*GRANT/REVOKE/DENY\*\*: Fine-grained SQL permission control

# 

# \### 2. \*\*Multilevel Security (MLS)\*\*

# \- \*\*Clearance Levels\*\*: 

# &nbsp; - Level 0: Unclassified

# &nbsp; - Level 1: Confidential

# &nbsp; - Level 2: Secret

# &nbsp; - Level 3: Top Secret

# \- \*\*Bell-LaPadula Implementation\*\*:

# &nbsp; -  No Read Up (NRU): Users cannot access data above their clearance

# &nbsp; -  No Write Down (NWD): Users cannot write to lower classification levels

# \- \*\*Classification Enforcement\*\*: Table-level and row-level classification

# 

# \### 3. \*\*Encryption (AES-256)\*\*

# \- \*\*At-Rest Encryption\*\*: Sensitive data encrypted using SQL Server symmetric keys

# \- \*\*Encrypted Fields\*\*:

# &nbsp; - Student grades

# &nbsp; - National IDs

# &nbsp; - Phone numbers

# &nbsp; - User passwords (SHA-256 hashing)

# \- \*\*Certificate-Based\*\*: Uses SQL Server certificates for key protection

# 

# \### 4. \*\*Flow Control\*\*

# \- \*\*Prevent Down-Flow\*\*: Triggers block writes from higher to lower classifications

# \- \*\*Data Leakage Prevention\*\*:

# &nbsp; - Secret → Confidential/Unclassified (BLOCKED)

# &nbsp; - Top Secret → Secret/Confidential/Unclassified (BLOCKED)

# \- \*\*Audit Trail\*\*: Sensitive access logging

# 

# \### 5. \*\*Inference Control\*\*

# \- \*\*Query Set Size Control\*\*: Minimum group size of 3 for aggregates

# \- \*\*Restricted Views\*\*: Limited data visibility for TAs and Students

# \- \*\*Safe Aggregation\*\*: Protected procedures for statistical queries

# 

# 

# \##  Database Schema

# 

# \### Core Tables

# 

# \#### \*\*Users\*\* (Authentication)

# \- `UserId` (PK)

# \- `Username` (Encrypted)

# \- `PasswordHash` (SHA-256)

# \- `Role` (Admin/Instructor/TA/Student/Guest)

# \- `Clearance` (0-3: MLS Level)

# 

# \#### \*\*Students\*\* (Confidential)

# \- `StudentId` (PK)

# \- `UserId` (FK)

# \- `FullName`

# \- `Email`

# \- `DOB`

# \- `Department`

# \- `ClearanceLevel`

# 

# \#### \*\*Instructors\*\* (Confidential)

# \- `InstructorId` (PK)

# \- `EncryptedNationalId` (AES-256)

# \- `EncryptedPhone` (AES-256)

# \- `FullName`

# \- `Email`

# \- `ClearanceLevel`

# 

# \#### \*\*Courses\*\* (Unclassified)

# \- `CourseId` (PK)

# \- `CourseName`

# \- `Description`

# \- `PublicInfo`

# \- `Classification`

# 

# \#### \*\*Grades\*\* (Secret)

# \- `GradeId` (PK)

# \- `StudentId` (FK)

# \- `CourseId` (FK)

# \- `GradeEncrypted` (AES-256)

# \- `GradeNumeric`

# \- `Classification` (Default: 2 - Secret)

# \- `EnteredBy` (FK to Users)

# 

# \#### \*\*Attendance\*\* (Secret)

# \- `AttendanceId` (PK)

# \- `StudentId` (FK)

# \- `CourseId` (FK)

# \- `Status`

# \- `Classification` (Default: 2 - Secret)

# \- `RecordedBy` (FK to Users)

# 

# \#### \*\*RoleRequests\*\* (Part B)

# \- `RequestId` (PK)

# \- `UserId` (FK)

# \- `RequestedRole`

# \- `Reason`

# \- `Status` (Pending/Approved/Denied)

# \- `ProcessedBy` (FK to Users)

# 

# ---

# 

# \### Default Admin Credentials

# ```

# Username: admin

# Password: AdminPassword!2025

# ```

# 

# \##  User Roles

# 

# \###  Admin

# \- Create and manage users

# \- View all students and instructors

# \- Full access to grades and attendance

# \- Approve/deny role upgrade requests

# \- Manage courses

# \- \*\*Clearance\*\*: Level 3 (Top Secret)

# 

# \###  Instructor

# \- View and edit grades

# \- View and edit attendance

# \- View all students

# \- Add courses

# \- \*\*Clearance\*\*: Level 2 (Secret)

# 

# \###  TA (Teaching Assistant)

# \- View and edit attendance (assigned courses only)

# \- View students (assigned courses only)

# \- \*\*No access\*\* to grades

# \- \*\*Clearance\*\*: Level 1 (Confidential)

# 

# \###  Student

# \- View own profile

# \- View own grades

# \- View own attendance

# \- Request role upgrades

# \- View public courses

# \- \*\*Clearance\*\*: Level 1 (Confidential)

# 

# \###  Guest

# \- View public course information only

# \- \*\*Clearance\*\*: Level 0 (Unclassified)

# 

# ---

# 

# \##  Security Implementation

# 

# \### Access Control Matrix

# 

# | Operation           | Admin | Instructor | TA | Student | Guest |

# |---------------------|-------|------------|-------|---------|-------|

# | View Own Profile    | ✅ | ✅ | ✅ | ✅ | ❌ |

# | Edit Own Profile    | ✅ | ✅ | ✅ | ❌ | ❌ |

# | View Grades         | ✅ | ✅ | ❌ | ✅ (own) | ❌ |

# | Edit Grades         | ✅ | ✅ | ❌ | ❌ | ❌ |

# | View Attendance     | ✅ | ✅ | ✅ | ✅ (own) | ❌ |

# | Edit Attendance     | ✅ | ✅ | ✅ | ❌ | ❌ |

# | Manage Users        | ✅ | ❌ | ❌ | ❌ | ❌ |

# | View Public Courses | ✅ | ✅ | ✅ | ✅ | ✅ |

# 

# \### Key Stored Procedures

# 

# ```sql

# -- Authentication

# usp\_ValidateLogin

# usp\_RegisterUser

# 

# -- Access Control

# usp\_GrantRole

# usp\_RequestRole (Part B)

# usp\_ProcessRoleRequest (Part B)

# 

# -- Data Operations

# usp\_GetGradesForUser (MLS enforced)

# usp\_InsertGrade (Flow control enforced)

# usp\_Student\_GetOwnGrades

# usp\_TA\_GetGrades

# 

# -- Inference Control

# usp\_SafeAvgGradeByCourse (min group size = 3)

# 

# -- Administrative

# usp\_AddCourse

# usp\_AssignTAToCourse

# usp\_CreateStudentProfile

# ```

# 

# \### Security Triggers

# 

# ```sql

# -- Flow Control Triggers

# trg\_PreventWriteDown\_Grades

# trg\_PreventWriteDown\_Attendance

# ```

# 

# 

# \### Project Structure

# ```

# SRMS-Security-Project/

# │

# ├── main.py                      # GUI Application

# ├── SRMS\_Database\_Script.sql     # Complete database setup

# ├── README.md                    # This file

# ├── requirements.txt             # Python dependencies

# ---

# 

# \## 📚 Technologies Used

# 

# \- \*\*Database\*\*: Microsoft SQL Server 2019+

# \- \*\*Programming Language\*\*: Python 3.8+

# \- \*\*GUI Framework\*\*: CustomTkinter

# \- \*\*Database Connector\*\*: pyodbc

# \- \*\*Encryption\*\*: AES-256 (SQL Server Symmetric Keys)

# \- \*\*Hashing\*\*: SHA-256

# 

# \## ⚠️ Important Notes

# 

# 1\. \*\*Security\*\*: This is an academic project. For production use, additional hardening is required.

# 2\. \*\*Master Key\*\*: Change the master key password in the SQL script before deployment.

# 3\. \*\*Connection String\*\*: Update server name in `main.py` to match your SQL Server instance.

# 4\. \*\*Clearance Levels\*\*: Properly assign clearance levels to users based on data sensitivity.

# 

# 

# \*\*Last Updated\*\*: January 2026

# 

# \*\*Project Status\*\*: ✅ Complete

# 

# ---



