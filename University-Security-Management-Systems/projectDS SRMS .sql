/* ---------------------------------------------------------------------------
   SRMS - Full SQL Script
   - Implements: Schema, AES encryption, RBAC (SQL roles), MLS (Bell-LaPadula),
     Inference control (query set size), Flow control (No Write Down),
     Stored procedures, Views, Triggers, Role Requests workflow (Part B).
   - Run in SQL Server Management Studio (SSMS).
   - Note: adjust passwords/connection settings & master key password for prod.
   --------------------------------------------------------------------------- */

-- =========================
-- 0. Create database
-- =========================
IF DB_ID('SRMS') IS NULL
    CREATE DATABASE SRMS;
GO
USE SRMS;
GO

-- =========================
-- 1. Crypto setup (AES)
-- =========================
-- Master key (change password to strong secret)
IF NOT EXISTS (SELECT * FROM sys.symmetric_keys WHERE name = '##MS_DatabaseMasterKey##')
BEGIN
    CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'StrongMasterKeyPassword_!2025';
END
GO

IF NOT EXISTS (SELECT * FROM sys.certificates WHERE name='SRMS_Cert')
BEGIN
    CREATE CERTIFICATE SRMS_Cert WITH SUBJECT = 'SRMS encryption cert';
END
GO

IF NOT EXISTS (SELECT * FROM sys.symmetric_keys WHERE name = 'SRMS_SYM_AES')
BEGIN
    CREATE SYMMETRIC KEY SRMS_SYM_AES WITH ALGORITHM = AES_256 ENCRYPTION BY CERTIFICATE SRMS_Cert;
END
GO

-- =========================
-- 2. Core tables (schema per spec)
-- =========================

-- USERS (authentication)
IF OBJECT_ID('dbo.Users') IS NOT NULL DROP TABLE dbo.Users;
GO
CREATE TABLE dbo.Users (
    UserId INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(100) NOT NULL,        -- application may store encrypted username in app or here if desired
    PasswordHash VARBINARY(8000) NOT NULL,  -- store result of HASHBYTES('SHA2_256', password) from app
    Role NVARCHAR(20) NOT NULL,             -- Admin/Instructor/TA/Student/Guest
    Clearance INT NOT NULL DEFAULT 0,        -- MLS clearance level (0=Unclassified,1=Confidential,2=Secret,3=TopSecret)
    CreatedAt DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

-- RoleRequests (Part B)
IF OBJECT_ID('dbo.RoleRequests') IS NOT NULL DROP TABLE dbo.RoleRequests;
GO
CREATE TABLE dbo.RoleRequests (
    RequestId INT IDENTITY(1,1) PRIMARY KEY,
    UserId INT NOT NULL REFERENCES dbo.Users(UserId),
    RequestedRole NVARCHAR(50) NOT NULL,
    Reason NVARCHAR(4000) NULL,
    Status NVARCHAR(20) DEFAULT 'Pending', -- Pending/Approved/Denied
    RequestedAt DATETIME2 DEFAULT SYSUTCDATETIME(),
    ProcessedBy INT NULL REFERENCES dbo.Users(UserId),
    ProcessedAt DATETIME2 NULL
);
GO

-- Courses (Unclassified)
IF OBJECT_ID('dbo.Courses') IS NOT NULL DROP TABLE dbo.Courses;
GO
CREATE TABLE dbo.Courses (
    CourseId INT IDENTITY(1,1) PRIMARY KEY,
    CourseName NVARCHAR(200) NOT NULL,
    Description NVARCHAR(MAX) NULL,
    PublicInfo NVARCHAR(MAX) NULL,
    Classification INT DEFAULT 0    -- 0 = Unclassified
);
GO
IF OBJECT_ID('dbo.Students') IS NOT NULL DROP TABLE dbo.Students;
GO
CREATE TABLE dbo.Students (
    StudentId INT IDENTITY PRIMARY KEY,
    UserId INT NOT NULL UNIQUE REFERENCES dbo.Users(UserId),
    FullName NVARCHAR(200) NOT NULL,
    Email NVARCHAR(200),
    DOB DATE,
    Department NVARCHAR(50),
    ClearanceLevel INT DEFAULT 1,
    Classification INT DEFAULT 1
);
GO


-- Instructors (Confidential)
IF OBJECT_ID('dbo.Instructors') IS NOT NULL DROP TABLE dbo.Instructors;
GO
CREATE TABLE dbo.Instructors (
    InstructorId INT IDENTITY(1,1) PRIMARY KEY,
    EncryptedNationalId VARBINARY(MAX) NULL,
    EncryptedPhone VARBINARY(MAX) NULL,
    FullName NVARCHAR(200) NOT NULL,
    Email NVARCHAR(200) NOT NULL UNIQUE,
    ClearanceLevel INT DEFAULT 2,
    Classification INT DEFAULT 1,
    CreatedAt DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

-- TA course assignments (to implement TA limited view)
IF OBJECT_ID('dbo.TACourseAssignments') IS NOT NULL DROP TABLE dbo.TACourseAssignments;
GO
CREATE TABLE dbo.TACourseAssignments (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    TAUserId INT NOT NULL REFERENCES dbo.Users(UserId),
    CourseId INT NOT NULL REFERENCES dbo.Courses(CourseId)
);
GO

-- Grades (Secret)
IF OBJECT_ID('dbo.Grades') IS NOT NULL DROP TABLE dbo.Grades;
GO
CREATE TABLE dbo.Grades (
    GradeId INT IDENTITY(1,1) PRIMARY KEY,
    StudentId INT NOT NULL REFERENCES dbo.Students(StudentId),
    CourseId INT NOT NULL REFERENCES dbo.Courses(CourseId),
    GradeEncrypted VARBINARY(MAX) NOT NULL, -- EncryptByKey
    GradeNumeric FLOAT NULL,                 -- optional: store numeric value encrypted OR as numeric for aggregates (see notes)
    Classification INT DEFAULT 2,            -- 2 = Secret
    DateEntered DATETIME2 DEFAULT SYSUTCDATETIME(),
    EnteredBy INT NOT NULL REFERENCES dbo.Users(UserId)
);
GO

-- Attendance (Secret)
IF OBJECT_ID('dbo.Attendance') IS NOT NULL DROP TABLE dbo.Attendance;
GO
CREATE TABLE dbo.Attendance (
    AttendanceId INT IDENTITY(1,1) PRIMARY KEY,
    StudentId INT NOT NULL REFERENCES dbo.Students(StudentId),
    CourseId INT NOT NULL REFERENCES dbo.Courses(CourseId),
    Status BIT NULL,
    DateRecorded DATETIME2 DEFAULT SYSUTCDATETIME(),
    Classification INT DEFAULT 2,
    RecordedBy INT NOT NULL REFERENCES dbo.Users(UserId)
);
GO

-- TableClassification meta
IF OBJECT_ID('dbo.TableClassification') IS NOT NULL DROP TABLE dbo.TableClassification;
GO
CREATE TABLE dbo.TableClassification (
    TableName NVARCHAR(200) PRIMARY KEY,
    Classification INT NOT NULL
);
GO

INSERT INTO dbo.TableClassification (TableName, Classification) VALUES
('Courses',0),('Students',1),('Instructors',1),('Grades',2),('Attendance',2);
GO

-- =========================
-- 3. Utility procs for encryption helpers
-- =========================

-- Open key helper (optional but helpful)
CREATE OR ALTER PROCEDURE dbo.usp_OpenSymKey
AS
BEGIN
    SET NOCOUNT ON;
    OPEN SYMMETRIC KEY SRMS_SYM_AES DECRYPTION BY CERTIFICATE SRMS_Cert;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_CloseSymKey
AS
BEGIN
    SET NOCOUNT ON;
    CLOSE SYMMETRIC KEY SRMS_SYM_AES;
END;
GO

-- =========================
-- 4. Views for restricted access (Inference control & MLS)
-- =========================

-- Public course view (visible to Guest)
CREATE OR ALTER VIEW dbo.vw_Courses_Public
AS
SELECT CourseId, CourseName, Description, PublicInfo
FROM dbo.Courses
WHERE Classification = 0;
GO

-- Student self view (students can see only own profile; application passes @RequestingUserId)
CREATE OR ALTER VIEW dbo.vw_Student_Self -- use with stored procedure that filters by user id mapping
AS
SELECT StudentId, FullName, Email, DOB, Department, ClearanceLevel
FROM dbo.Students;
GO

-- TA restricted view: TA can only see students in courses assigned to TA (Confidential)
-- Implemented via stored proc to enforce TA identity; view left generic
CREATE OR ALTER VIEW dbo.vw_Grades_All
AS
SELECT GradeId, StudentId, CourseId, GradeEncrypted, GradeNumeric, Classification, DateEntered, EnteredBy
FROM dbo.Grades;
GO

-- =========================
-- 5. Stored Procedures - Authentication & User management
-- =========================

-- Register user (app should send hashed password using HASHBYTES('SHA2_256', password))
CREATE OR ALTER PROCEDURE dbo.usp_RegisterUser
    @Username      NVARCHAR(200),
    @PasswordHash  VARBINARY(8000),
    @Role          NVARCHAR(20),
    @Clearance     INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Prevent duplicate username
    IF EXISTS (SELECT 1 FROM dbo.Users WHERE Username = @Username)
    BEGIN
        RAISERROR('Username already exists.', 16, 1);
        RETURN;
    END;

    INSERT INTO dbo.Users (Username, PasswordHash, Role, Clearance)
    VALUES (@Username, @PasswordHash, @Role, @Clearance);
END;
GO


-- Validate login (returns user record if password hash matches)
CREATE OR ALTER PROCEDURE dbo.usp_ValidateLogin
    @Username NVARCHAR(100),
    @PasswordHash VARBINARY(8000)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT UserId, Username, Role, Clearance
    FROM dbo.Users
    WHERE Username = @Username AND PasswordHash = @PasswordHash;
END;
GO

-- GrantRole (Admin only)
CREATE OR ALTER PROCEDURE dbo.usp_GrantRole
    @AdminId INT,
    @TargetUserId INT,
    @NewRole NVARCHAR(50),
    @NewClearance INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @adminRole NVARCHAR(50);
    SELECT @adminRole = Role FROM dbo.Users WHERE UserId = @AdminId;
    IF @adminRole <> 'Admin'
        THROW 51000, 'Only Admin can change roles', 1;

    UPDATE dbo.Users SET Role = @NewRole, Clearance = @NewClearance WHERE UserId = @TargetUserId;
END;
GO

-- Request role (Part B)
CREATE OR ALTER PROCEDURE dbo.usp_RequestRole
    @UserId INT,
    @RequestedRole NVARCHAR(50),
    @Reason NVARCHAR(4000)
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.RoleRequests (UserId, RequestedRole, Reason) VALUES (@UserId, @RequestedRole, @Reason);
END;
GO

-- Process role request (Admin)
CREATE OR ALTER PROCEDURE dbo.usp_ProcessRoleRequest
    @AdminId INT,
    @RequestId INT,
    @Approve BIT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @adminRole NVARCHAR(50);
    SELECT @adminRole = Role FROM dbo.Users WHERE UserId = @AdminId;
    IF @adminRole <> 'Admin'
        THROW 51001, 'Only Admin can process requests', 1;

    DECLARE @reqUser INT, @reqRole NVARCHAR(50);
    SELECT @reqUser = UserId, @reqRole = RequestedRole FROM dbo.RoleRequests WHERE RequestId = @RequestId;

    IF @Approve = 1
    BEGIN
        DECLARE @newClearance INT = CASE @reqRole WHEN 'TA' THEN 1 WHEN 'Instructor' THEN 2 WHEN 'Admin' THEN 3 ELSE 0 END;
        UPDATE dbo.Users SET Role = @reqRole, Clearance = @newClearance WHERE UserId = @reqUser;
        UPDATE dbo.RoleRequests SET Status='Approved', ProcessedBy=@AdminId, ProcessedAt=SYSUTCDATETIME() WHERE RequestId = @RequestId;
    END
    ELSE
    BEGIN
        UPDATE dbo.RoleRequests SET Status='Denied', ProcessedBy=@AdminId, ProcessedAt=SYSUTCDATETIME() WHERE RequestId = @RequestId;
    END
END;
GO

-- =========================
-- 6. Grades: read procedure with No Read Up (NRU) & decryption
-- =========================

CREATE OR ALTER PROCEDURE usp_GetGradesForUser
    @RequestingUserId INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @UserClear INT;
    DECLARE @UserRole NVARCHAR(50);

    SELECT 
        @UserClear = Clearance,
        @UserRole = Role
    FROM Users
    WHERE UserId = @RequestingUserId;

    -- Open AES Key
    OPEN SYMMETRIC KEY SRMS_SYM_AES
        DECRYPTION BY CERTIFICATE SRMS_Cert;

    -- Main Secure Select (NO READ UP)
    SELECT 
        g.GradeId,
        g.StudentId,
        g.CourseId,
        CONVERT(NVARCHAR(100), DecryptByKey(g.GradeEncrypted)) AS DecryptedGrade,
        g.Classification,
        g.DateEntered,
        g.EnteredBy
    FROM vw_Grades_All g
    WHERE g.Classification <= @UserClear;   -- MLS rule

    -- Close AES Key
    CLOSE SYMMETRIC KEY SRMS_SYM_AES;
END;
GO


-- =========================
-- 7. Insert grade (No Write Down + RBAC check)
-- =========================

CREATE OR ALTER PROCEDURE dbo.usp_InsertGrade
    @RequestingUserId INT,
    @StudentId INT,
    @CourseId INT,
    @Grade NVARCHAR(100),    -- textual numeric or letter
    @GradeNumeric FLOAT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @role NVARCHAR(50), @clear INT;
    SELECT @role = Role, @clear = Clearance FROM dbo.Users WHERE UserId = @RequestingUserId;

    IF @role NOT IN ('Instructor','Admin')
        THROW 52000, 'Only Instructor or Admin can insert grades', 1;

    -- Table classification for Grades
    DECLARE @tableClass INT = (SELECT Classification FROM dbo.TableClassification WHERE TableName='Grades');
    IF @tableClass IS NULL SET @tableClass = 2;
	

    OPEN SYMMETRIC KEY SRMS_SYM_AES DECRYPTION BY CERTIFICATE SRMS_Cert;
    DECLARE @enc VARBINARY(MAX) = EncryptByKey(Key_GUID('SRMS_SYM_AES'), @Grade);
    INSERT INTO dbo.Grades (StudentId, CourseId, GradeEncrypted, GradeNumeric, Classification, EnteredBy, DateEntered)
    VALUES (@StudentId, @CourseId, @enc, @GradeNumeric, @tableClass, @RequestingUserId, SYSUTCDATETIME());
    CLOSE SYMMETRIC KEY SRMS_SYM_AES;
END;
GO




-- =========================
-- 8. Inference control: safe aggregate (group size >= 3)
-- =========================

CREATE OR ALTER PROCEDURE dbo.usp_SafeAvgGradeByCourse
    @RequestingUserId INT,
    @CourseId INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Check clearance
    DECLARE @userClear INT;
    SELECT @userClear = Clearance FROM dbo.Users WHERE UserId = @RequestingUserId;

    DECLARE @tableClass INT = (SELECT Classification FROM dbo.TableClassification WHERE TableName='Grades');
    IF @tableClass > @userClear
        THROW 53000, 'No Read Up', 1;

    -- Group size control
    DECLARE @cnt INT;
    SELECT @cnt = COUNT(DISTINCT StudentId) FROM dbo.Grades WHERE CourseId = @CourseId;
    IF @cnt < 3
        THROW 53001, 'Inference control: group too small to release aggregates (min group size = 3)', 1;

    -- compute average (decrypt)
    OPEN SYMMETRIC KEY SRMS_SYM_AES DECRYPTION BY CERTIFICATE SRMS_Cert;
    SELECT AVG(g.GradeNumeric) AS AvgGradeNumeric,
           COUNT(DISTINCT g.StudentId) AS StudentCount
    FROM dbo.Grades g
    WHERE g.CourseId = @CourseId;
    CLOSE SYMMETRIC KEY SRMS_SYM_AES;
END;
GO

-- =========================
-- 9. Triggers / Flow Control (prevent down-flow)
--    - trg_PreventWriteDown_Grades: prevents writes to Grades if user clearance > table class
-- =========================

CREATE OR ALTER TRIGGER dbo.trg_PreventWriteDown_Grades
ON dbo.Grades
INSTEAD OF INSERT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @userId INT = (SELECT TOP 1 EnteredBy FROM inserted);
    IF @userId IS NULL
    BEGIN
        RAISERROR('EnteredBy required',16,1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    DECLARE @userClear INT;
    SELECT @userClear = Clearance FROM dbo.Users WHERE UserId = @userId;

    DECLARE @tableClass INT = (SELECT Classification FROM dbo.TableClassification WHERE TableName='Grades');

    IF @userClear > @tableClass
    BEGIN
        RAISERROR('Flow Control: No Write Down allowed (Grades).',16,1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    -- proceed with insert (assume app sends GradeEncrypted already encrypted OR inserted contains GradeEncrypted)
    INSERT INTO dbo.Grades (StudentId, CourseId, GradeEncrypted, GradeNumeric, Classification, DateEntered, EnteredBy)
    SELECT StudentId, CourseId, GradeEncrypted, GradeNumeric, Classification, DateEntered, EnteredBy
    FROM inserted;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_PreventWriteDown_Attendance
ON dbo.Attendance
INSTEAD OF INSERT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @userId INT = (SELECT TOP 1 RecordedBy FROM inserted);
    IF @userId IS NULL
    BEGIN
        RAISERROR('RecordedBy required',16,1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    DECLARE @userClear INT;
    SELECT @userClear = Clearance FROM dbo.Users WHERE UserId = @userId;

    DECLARE @tableClass INT = (SELECT Classification FROM dbo.TableClassification WHERE TableName='Attendance');

    IF @userClear > @tableClass
    BEGIN
        RAISERROR('Flow Control: No Write Down allowed (Attendance).',16,1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    INSERT INTO dbo.Attendance (StudentId, CourseId, Status, DateRecorded, Classification, RecordedBy)
    SELECT StudentId, CourseId, Status, DateRecorded, Classification, RecordedBy FROM inserted;
END;
GO

-- =========================
-- 10. Restricted views & procedures for TA and Student (enforce least privilege)
-- =========================

-- TA: view grades for courses assigned to TA (decrypted)
CREATE OR ALTER PROCEDURE dbo.usp_TA_GetGrades
    @TAUserId INT
AS
BEGIN
    SET NOCOUNT ON;

    -- ensure TA role
    DECLARE @role NVARCHAR(50);
    SELECT @role = Role FROM dbo.Users WHERE UserId = @TAUserId;
    IF @role <> 'TA'
        THROW 54000, 'Only TA can call this proc', 1;

    OPEN SYMMETRIC KEY SRMS_SYM_AES DECRYPTION BY CERTIFICATE SRMS_Cert;

    SELECT g.GradeId,
           g.StudentId,
           g.CourseId,
           CONVERT(NVARCHAR(100), DecryptByKey(g.GradeEncrypted)) AS Grade,
           g.GradeNumeric,
           g.Classification,
           g.DateEntered,
           g.EnteredBy
    FROM dbo.Grades g
    INNER JOIN dbo.TACourseAssignments t ON g.CourseId = t.CourseId
    WHERE t.TAUserId = @TAUserId
      AND g.Classification <= (SELECT Clearance FROM dbo.Users WHERE UserId = @TAUserId);

    CLOSE SYMMETRIC KEY SRMS_SYM_AES;
END;
GO

-- Student: get own grades (app must pass requesting user and their StudentId)
CREATE OR ALTER PROCEDURE dbo.usp_Student_GetOwnGrades
    @StudentUserId INT  -- the logged-in user's UserId
AS
BEGIN
    SET NOCOUNT ON;

    -- 1. Check that the user exists and has role Student
    DECLARE @role NVARCHAR(50), @clearance INT;
    SELECT @role = Role, @clearance = Clearance
    FROM dbo.Users
    WHERE UserId = @StudentUserId;

    IF @role IS NULL OR @role <> 'Student'
        THROW 54001, 'Access denied: Student role required.', 1;

    -- 2. Get the student's profile
    DECLARE @StudentId INT;
    SELECT @StudentId = StudentId
    FROM dbo.Students
    WHERE UserId = @StudentUserId;

    IF @StudentId IS NULL
        THROW 54002, 'Student profile not found.', 1;

    -- Handle NULL clearance (treat as 0 - no access)
    IF @clearance IS NULL
        SET @clearance = 0;

    -- 3. Open encryption key with error handling
    BEGIN TRY
        OPEN SYMMETRIC KEY SRMS_SYM_AES
            DECRYPTION BY CERTIFICATE SRMS_Cert;

        -- 4. Select only the student's grades, respecting clearance
        SELECT
            g.GradeId,
            g.CourseId,
            CONVERT(NVARCHAR(100), DecryptByKey(g.GradeEncrypted)) AS Grade,
            g.GradeNumeric,
            g.DateEntered
        FROM dbo.Grades g
        WHERE g.StudentId = @StudentId
          AND g.Classification <= @clearance
        ORDER BY g.DateEntered;

        -- 5. Close key
        CLOSE SYMMETRIC KEY SRMS_SYM_AES;
    END TRY
    BEGIN CATCH
        -- Ensure key is closed even if error occurs
        IF EXISTS (SELECT 1 FROM sys.openkeys WHERE key_name = 'SRMS_SYM_AES')
            CLOSE SYMMETRIC KEY SRMS_SYM_AES;
        THROW;  -- Re-throw the original error
    END CATCH
END;
GO





-- =========================
-- 11. Grants, DB roles & permissions (RBAC)
--    Create DB roles: AdminRole, InstructorRole, TARole, StudentRole, GuestRole
--    Grant only EXECUTE on stored procedures; deny direct SELECT on secret tables to roles except Admin/Instructor where needed.
-- =========================

-- Create database roles
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'AdminRole')
    EXEC sp_addrole 'AdminRole';
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'InstructorRole')
    EXEC sp_addrole 'InstructorRole';
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'TARole')
    EXEC sp_addrole 'TARole';
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'StudentRole')
    EXEC sp_addrole 'StudentRole';
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'GuestRole')
    EXEC sp_addrole 'GuestRole';
GO

-- Revoke wide permissions (defense in depth)
DENY SELECT ON dbo.Grades TO PUBLIC;
DENY SELECT ON dbo.Attendance TO PUBLIC;
DENY SELECT ON dbo.Students TO PUBLIC;
GO

-- Grant execute on procedures to roles
GRANT EXECUTE ON dbo.usp_ValidateLogin TO GuestRole, StudentRole, TARole, InstructorRole, AdminRole;
GRANT EXECUTE ON dbo.usp_GetGradesForUser TO StudentRole, TARole, InstructorRole, AdminRole;
GRANT EXECUTE ON dbo.usp_Student_GetOwnGrades TO StudentRole;
GRANT EXECUTE ON dbo.usp_TA_GetGrades TO TARole;
GRANT EXECUTE ON dbo.usp_InsertGrade TO InstructorRole, AdminRole;
GRANT EXECUTE ON dbo.usp_SafeAvgGradeByCourse TO InstructorRole, AdminRole;
GRANT EXECUTE ON dbo.usp_RegisterUser TO AdminRole;
GRANT EXECUTE ON dbo.usp_GrantRole TO AdminRole;
GRANT EXECUTE ON dbo.usp_RequestRole TO StudentRole, TARole, InstructorRole, GuestRole;
GRANT EXECUTE ON dbo.usp_ProcessRoleRequest TO AdminRole;
GO

-- Admin role can select on everything
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.Users TO AdminRole;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.Grades TO AdminRole;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.Attendance TO AdminRole;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.Students TO AdminRole;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.Courses TO AdminRole;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.Instructors TO AdminRole;
GO

-- Instructor role: select on students (confidential) and execute procedures
GRANT SELECT ON dbo.Students TO InstructorRole;
GRANT SELECT ON dbo.Courses TO InstructorRole;
GRANT SELECT ON dbo.Instructors TO InstructorRole;
GRANT SELECT ON dbo.Grades TO InstructorRole; -- assume instructors can read grades (policy)
GO

-- TA permissions: limited (we will rely on stored procs)
DENY SELECT ON dbo.Grades TO TARole; -- force usage of usp_TA_GetGrades
GRANT SELECT ON dbo.Courses TO TARole;
GO

-- Student permissions
DENY SELECT ON dbo.Grades TO StudentRole; -- must use usp_Student_GetOwnGrades
GRANT SELECT ON dbo.Courses TO StudentRole;
GO

-- Guest
GRANT SELECT ON dbo.vw_Courses_Public TO GuestRole;
GO

-- NOTE: Application must map authenticated DB user to DB role using sp_addrolemember or use application-level enforcement.

-- =========================
-- 12. Utility: map app users to db roles (example inserts and role memberships)
-- =========================

-- Insert sample admin user (password hash example)
-- App should hash password using HASHBYTES('SHA2_256', 'password123')
IF NOT EXISTS (SELECT * FROM dbo.Users WHERE Username='admin')
BEGIN
    INSERT INTO dbo.Users (Username, PasswordHash, Role, Clearance)
    VALUES ('admin', HASHBYTES('SHA2_256','AdminPassword!2025'), 'Admin', 3);
END
GO

-- Add this database user to DB role (if using contained DB users or Windows/SQL logins you map accordingly)
-- Example for SQL user: skip if your app maintains roles in Users table and uses app-level RBAC.
-- EXEC sp_addrolemember 'AdminRole', 'your_db_username';

-- =========================
-- 13. Additional helpers: assign TA to course (app or admin UI uses these)
-- =========================

CREATE OR ALTER PROCEDURE dbo.usp_AssignTAToCourse
    @AdminUserId INT,
    @TAUserId INT,
    @CourseId INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @adminRole NVARCHAR(50);
    SELECT @adminRole = Role FROM dbo.Users WHERE UserId = @AdminUserId;
    IF @adminRole <> 'Admin' THROW 56000, 'Only Admin can assign TAs', 1;

    INSERT INTO dbo.TACourseAssignments (TAUserId, CourseId) VALUES (@TAUserId, @CourseId);
END;
GO

-- =========================
-- 14. Safety: Prevent direct exports of secret data (Flow Control - example)
-- Note: True prevention of copying/printing/exporting is largely GUI responsibility.
-- Here we provide DB-side denials and audit trail stubs.
-- =========================

-- Audit table for sensitive reads (optional)
IF OBJECT_ID('dbo.AuditSensitiveAccess') IS NOT NULL DROP TABLE dbo.AuditSensitiveAccess;
GO
CREATE TABLE dbo.AuditSensitiveAccess (
    AuditId INT IDENTITY(1,1) PRIMARY KEY,
    UserId INT,
    Action NVARCHAR(200),
    ObjectName NVARCHAR(200),
    AccessedAt DATETIME2 DEFAULT SYSUTCDATETIME(),
    Notes NVARCHAR(1000)
);
GO

-- Example: log when usp_GetGradesForUser is called
CREATE OR ALTER PROCEDURE dbo.usp_GetGradesForUser_WithAudit
    @RequestingUserId INT
AS
BEGIN
    INSERT INTO dbo.AuditSensitiveAccess (UserId, Action, ObjectName)
    VALUES (@RequestingUserId, 'Call usp_GetGradesForUser', 'Grades');
    EXEC dbo.usp_GetGradesForUser @RequestingUserId;
END;
GO

-- =========================
-- 15. Final notes & recommended app behavior (not code)
-- - Application MUST:
--   * Hash passwords with SHA2_256 before sending to DB (or use secure auth).
--   * Use stored procedures for all operations; do NOT perform ad-hoc SELECT/INSERT on secret tables.
--   * Enforce GUI flow control (disable copy/paste, export for secret views) at client side.
--   * Map authenticated app users to DB roles or enforce RBAC at app level in combination with DB checks.
-- - For encryption: app may encrypt certain PII before sending OR rely on DB EncryptByKey in procs.
-- =========================

-- End of script
GO



CREATE OR ALTER PROCEDURE dbo.usp_AddCourse
    @RequestingUserId INT,
    @CourseName NVARCHAR(200),
    @Description NVARCHAR(MAX),
    @PublicInfo NVARCHAR(MAX),
    @Classification INT = 0
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @role NVARCHAR(50);
    SELECT @role = Role FROM dbo.Users WHERE UserId = @RequestingUserId;

    -- RBAC check
    IF @role NOT IN ('Admin', 'Instructor')
        THROW 57000, 'Only Admin or Instructor can add courses', 1;

    INSERT INTO dbo.Courses (CourseName, Description, PublicInfo, Classification)
    VALUES (@CourseName, @Description, @PublicInfo, @Classification);
END;
GO

GRANT EXECUTE ON dbo.usp_AddCourse TO AdminRole, InstructorRole;
GO

CREATE OR ALTER PROCEDURE dbo.usp_CreateStudentProfile
    @UserId INT,
    @FullName NVARCHAR(200),
    @Email NVARCHAR(200),
    @Department NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (SELECT 1 FROM dbo.Students WHERE UserId = @UserId)
        THROW 55000, 'Student profile already exists', 1;

    INSERT INTO dbo.Students
    (UserId, FullName, Email, Department, ClearanceLevel, Classification)
    VALUES
    (@UserId, @FullName, @Email, @Department, 1, 1);
END;
GO
