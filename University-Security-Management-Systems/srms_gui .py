import customtkinter as ctk
import pyodbc
import hashlib
import os, sys
import hashlib




def has_access(feature):
    permissions = {
        "view_profile": ["Admin", "Instructor", "TA", "Student"],
        "edit_profile": ["Admin", "Instructor", "TA"],
        "view_grades": ["Admin", "Instructor", "Student"],
        "edit_grades": ["Admin", "Instructor"],
        "view_attendance": ["Admin", "Instructor", "TA", "Student"],
        "edit_attendance": ["Admin", "Instructor", "TA"],
        "manage_users": ["Admin"],
        "view_public_courses": ["Admin", "Instructor", "TA", "Student", "Guest"],
        "add_course": ["Admin", "Instructor"],
    }

    return current_role in permissions.get(feature, [])

def require_access(feature):
    if not has_access(feature):
        clear_window()
        frame = ctk.CTkFrame(app)
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="Access Denied",
            text_color="red",
            font=("Arial", 18)
        ).pack(pady=30)

        ctk.CTkButton(
            frame,
            text="⬅ Back",
            command=lambda: open_dashboard(current_role)
        ).pack()
        raise PermissionError





# ======================================================
# GLOBAL STATE

# ======================================================
current_user = None
current_role = None

# ======================================================
# DATABASE CONNECTION
# ======================================================
def get_connection():
    return pyodbc.connect(
        r"Driver={SQL Server};"
        r"Server=MAHDY-PC206;"
        r"Database=SRMS;"
        r"Trusted_Connection=yes;"
    )

# ======================================================
# CLEAR WINDOW
# ======================================================
def clear_window():
    for widget in app.winfo_children():
        widget.destroy()

# ======================================================
# LOGIN
# ======================================================


def login():
    global current_user, current_role, current_user_id, current_clearance

    username = entry_user.get()
    password = entry_pass.get()

    # Match SQL's HASHBYTES('SHA2_256')
    hashed_password = hashlib.sha256(password.encode()).digest()

    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = "{CALL usp_ValidateLogin (?, ?)}"
        cursor.execute(sql, (username, hashed_password))

        row = cursor.fetchone()
        conn.close()

        if row:
            # Row structure: UserId, Username, Role, Clearance
            current_user_id = row[0]
            current_user = row[1]
            current_role = row[2]
            current_clearance = row[3]

            # ⭐ AUTO-CREATE STUDENT PROFILE
            if current_role == "Student":
                ensure_student_profile()

            lbl_login.configure(text="Login Success", text_color="green")
            open_dashboard(current_role)

        else:
            lbl_login.configure(text="Invalid name or password", text_color="red")

    except Exception as e:
        clear_window()
        frame = ctk.CTkFrame(app)
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text=f"Login Error:\n{e}",
            text_color="red",
            wraplength=400
        ).pack(pady=20)

        ctk.CTkButton(
            frame,
            text="⬅ Back to Login",
            command=restart_login
        ).pack(pady=10)

# ======================================================
# ensure_student_profile
# ======================================================
def ensure_student_profile():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT StudentId FROM Students WHERE UserId = ?",
        (current_user_id,)
    )

    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO Students
            (UserId, FullName, Email, Department, ClearanceLevel, Classification)
            VALUES (?, ?, ?, ?, 1, 1)
        """, (
            current_user_id,
            current_user,
            f"{current_user}@student.com",
            "General"
        ))
        conn.commit()

    conn.close()


# ======================================================
# request_role_upgrade (student)
# ======================================================
def request_role_upgrade():
            # DEBUG PRINT: Check if function is entered
            print("Debug: Request Role Upgrade function called.")

            clear_window()
            frame = ctk.CTkFrame(app)
            frame.pack(fill="both", expand=True, padx=20, pady=20)

            ctk.CTkLabel(frame, text="Request Role Upgrade", font=("Arial", 22)).pack(pady=10)

            if not current_user_id:
                ctk.CTkLabel(frame, text="Error: User ID missing. Please Relogin.", text_color="red").pack()
                ctk.CTkButton(frame, text="Back", command=lambda: open_dashboard("Student")).pack(pady=20)
                return

            # 1. Select Role
            ctk.CTkLabel(frame, text="Select Desired Role:").pack(pady=5)
            role_var = ctk.StringVar(value="TA")
            ctk.CTkOptionMenu(frame, values=["TA", "Instructor", "Admin"], variable=role_var).pack(pady=5)

            # 2. Enter Reason (Required by SQL)
            ctk.CTkLabel(frame, text="Reason for request:").pack(pady=5)
            entry_reason = ctk.CTkEntry(frame, placeholder_text="Ex: Assigned to Course 101", width=300)
            entry_reason.pack(pady=5)

            lbl_status = ctk.CTkLabel(frame, text="")
            lbl_status.pack(pady=10)

            def submit_request():
                requested_role = role_var.get()
                reason_text = entry_reason.get()

                if not reason_text:
                    lbl_status.configure(text="Reason is required!", text_color="red")
                    return

                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    # Execute Stored Procedure: usp_RequestRole
                    sql = "{CALL usp_RequestRole (?, ?, ?)}"
                    cursor.execute(sql, (current_user_id, requested_role, reason_text))

                    conn.commit()
                    conn.close()
                    lbl_status.configure(text="Request sent successfully!", text_color="green")

                except Exception as e:
                    lbl_status.configure(text=f"Error: {e}", text_color="red")

            ctk.CTkButton(frame, text="Submit Request", command=submit_request, fg_color="green").pack(pady=20)
            ctk.CTkButton(frame, text="⬅ Back", command=lambda: open_dashboard("Student")).pack(pady=10)


# ======================================================
# DASHBOARD ROUTER
# ======================================================
def open_dashboard(role):
    clear_window()

    if role == "Admin":
        admin_dashboard()
    elif role == "Instructor":
        instructor_dashboard()
    elif role == "TA":
        ta_dashboard()
    elif role == "Student":
        student_dashboard()
    else:
        guest_dashboard()

# ======================================================
# LOGOUT
# ======================================================
def logout():
    global current_user, current_role, current_user_id, current_clearance

    current_user = None
    current_role = None
    current_user_id = None
    current_clearance = None

    clear_window()

    # Rebuild login UI
    login_frame = ctk.CTkFrame(app)
    login_frame.pack(expand=True)

    ctk.CTkLabel(login_frame, text="SRMS Login", font=("Arial", 24)).pack(pady=15)

    global entry_user, entry_pass, lbl_login
    entry_user = ctk.CTkEntry(login_frame, placeholder_text="Username", width=250)
    entry_user.pack(pady=5)

    entry_pass = ctk.CTkEntry(login_frame, placeholder_text="Password", show="*", width=250)
    entry_pass.pack(pady=5)

    ctk.CTkButton(login_frame, text="Login", command=login, width=200).pack(pady=15)

    lbl_login = ctk.CTkLabel(login_frame, text="")
    lbl_login.pack()

# ======================================================
# ADD COURSE (INSTRUCTOR/ADMIN)
# ======================================================
def add_course():
    require_access("add_course")

    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Add New Course", font=("Arial", 22)).pack(pady=10)

    entry_name = ctk.CTkEntry(frame, placeholder_text="Course Name", width=300)
    entry_desc = ctk.CTkEntry(frame, placeholder_text="Description", width=300)
    entry_public = ctk.CTkEntry(frame, placeholder_text="Public Info", width=300)

    entry_name.pack(pady=5)
    entry_desc.pack(pady=5)
    entry_public.pack(pady=5)

    lbl_status = ctk.CTkLabel(frame, text="")
    lbl_status.pack(pady=10)

    def save_course():
        if not entry_name.get():
            lbl_status.configure(text="Course name is required", text_color="red")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "{CALL dbo.usp_AddCourse (?, ?, ?, ?, ?)}",
                (
                    current_user_id,
                    entry_name.get(),
                    entry_desc.get(),
                    entry_public.get(),
                    0  # Unclassified
                )
            )

            conn.commit()
            conn.close()

            lbl_status.configure(text="Course added successfully ✔", text_color="green")

        except Exception as e:
            lbl_status.configure(text=str(e), text_color="red")

    ctk.CTkButton(frame, text="Save Course", command=save_course, fg_color="green").pack(pady=10)
    ctk.CTkButton(frame, text="⬅ Back", command=lambda: open_dashboard(current_role)).pack(pady=5)

# ======================================================
# VIEW MY PROFILE (STUDENT)
# ======================================================
def view_my_profile():
    clear_window()

    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="My Profile", font=("Arial", 22)).pack(pady=10)

    # ✅ CHECK: is user logged in?
    if not current_user:
        ctk.CTkLabel(frame,text="Error: No user is logged in.",text_color="red").pack(pady=10)
        ctk.CTkButton(frame,text="⬅ Back",command=lambda: open_dashboard(current_role)).pack(pady=20)
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Username, Role FROM USERS WHERE Username = ?",
            (current_user,)
        )
        user = cursor.fetchone()
        conn.close()

        # ✅ CHECK: user exists?
        if not user:
            ctk.CTkLabel(frame,text="Error: User not found in database.",text_color="red").pack(pady=10)
        else:
            ctk.CTkLabel(frame, text=f"Username: {user[0]}").pack(pady=5)
            ctk.CTkLabel(frame, text=f"Role: {user[1]}").pack(pady=5)

    except Exception as e:
        ctk.CTkLabel(
            frame,
            text=f"Database Error:\n{e}",
            text_color="red",
            wraplength=400
        ).pack(pady=10)

    if has_access("edit_profile"):
        ctk.CTkButton(frame, text="Edit Profile", command=edit_my_profile).pack(pady=5)

    ctk.CTkButton(
        frame,
        text="⬅ Back",
        command=lambda: open_dashboard(current_role)
    ).pack(pady=20)

#======================================================
# VIEW MY GRADES (STUDENT)
# ======================================================
def view_my_grades():
    clear_window()

    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="My Grades", font=("Arial", 22)).pack(pady=10)

    if not current_user:
        ctk.CTkLabel(frame, text="Not logged in", text_color="red").pack()
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get current user's UserId
        cursor.execute("SELECT UserId FROM Users WHERE Username = ?", (current_user,))
        result = cursor.fetchone()
        if not result:
            ctk.CTkLabel(frame, text="User not found", text_color="red").pack()
            conn.close()
            return

        user_id = result[0]

        # Call the stored procedure to get grades
        cursor.execute("EXEC dbo.usp_Student_GetOwnGrades @StudentUserId = ?", (user_id,))
        grades = cursor.fetchall()

        if not grades:
            ctk.CTkLabel(frame, text="No grades available yet").pack()
        else:
            # grades columns: GradeId, CourseId, Grade (decrypted), GradeNumeric, DateEntered
            for grade_id, course_id, grade, grade_numeric, date_entered in grades:
                # Convert date_entered safely (it may already be a string)
                date_str = str(date_entered).split(".")[0]  # removes microseconds
                # Get course name
                cursor.execute("SELECT CourseName FROM Courses WHERE CourseId = ?", (course_id,))
                course_name_row = cursor.fetchone()
                course_name = course_name_row[0] if course_name_row else f"Course {course_id}"

                ctk.CTkLabel(frame,text=f"{course_name}: {grade} ({grade_numeric}) on {date_str}").pack(pady=3)
        conn.close()

    except Exception as e:
        ctk.CTkLabel(frame,text=f"Database Error:\n{e}",text_color="red",wraplength=400).pack()

    ctk.CTkButton(frame,text="⬅ Back",command=lambda: open_dashboard(current_role)).pack(pady=20)


# ======================================================
# manage_users (admin)
# ======================================================
def manage_users():
    clear_window()

    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(
        frame,
        text="Manage Users",
        font=("Arial", 22, "bold")
    ).pack(pady=10)

    # Safety check
    if current_role != "Admin":
        ctk.CTkLabel(frame, text="Access Denied", text_color="red").pack()
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT UserId, Username, Role, Clearance
            FROM dbo.Users
            ORDER BY UserId
        """)
        users = cursor.fetchall()
        conn.close()

        if not users:
            ctk.CTkLabel(frame, text="No users found").pack()
            return

        # ===== TABLE HEADER =====
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", pady=5)

        headers = ["ID", "Username", "Role", "Clearance", "Action"]
        widths = [60, 120, 100, 100, 100]

        for h, w in zip(headers, widths):
            ctk.CTkLabel(
                header,
                text=h,
                width=w,
                font=("Arial", 12, "bold")
            ).pack(side="left", padx=2)

        # ===== USER ROWS =====
        for user in users:
            user_id, username, role, clearance = user

            row = ctk.CTkFrame(frame)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=user_id, width=60).pack(side="left")
            ctk.CTkLabel(row, text=username, width=120).pack(side="left")

            role_var = ctk.StringVar(value=role)
            ctk.CTkOptionMenu(
                row,
                values=["Student", "TA", "Instructor", "Admin"],
                variable=role_var,
                width=100
            ).pack(side="left", padx=2)

            clearance_var = ctk.StringVar(value=str(clearance))
            ctk.CTkOptionMenu(
                row,
                values=["0", "1", "2", "3"],
                variable=clearance_var,
                width=100
            ).pack(side="left", padx=2)

            def save_changes(uid=user_id, r=role_var, c=clearance_var):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE dbo.Users
                        SET Role = ?, Clearance = ?
                        WHERE UserId = ?
                    """, (r.get(), int(c.get()), uid))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print("Update Error:", e)

            ctk.CTkButton(
                row,
                text="Save",
                width=80,
                command=save_changes
            ).pack(side="left", padx=2)

    except Exception as e:
        ctk.CTkLabel(
            frame,
            text=f"Database Error:\n{e}",
            text_color="red",
            wraplength=500
        ).pack()

    ctk.CTkButton(
        frame,
        text="⬅ Back",
        command=lambda: open_dashboard(current_role)
    ).pack(pady=20)

# ======================================================
# view_all_students
# ======================================================
def view_all_students():
    clear_window()

    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(
        frame,
        text="All Students",
        font=("Arial", 22, "bold")
    ).pack(pady=10)
    #check if only admin can access
    # # Role check (extra safety)
    # if current_role != "Admin":
    #     ctk.CTkLabel(
    #         frame,
    #         text="Access Denied: Admin only",
    #         text_color="red"
    #     ).pack()
    #     return

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                StudentId,
                FullName,
                Email,
                Department,
                Classification
            FROM dbo.Students
            ORDER BY StudentId
        """)

        students = cursor.fetchall()
        conn.close()

        if not students:
            ctk.CTkLabel(frame, text="No students found").pack()
            return

        # Table header
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", pady=5)

        headers = ["ID", "Name", "Email", "Department", "Class"]
        for h in headers:
            ctk.CTkLabel(
                header,
                text=h,
                width=150,
                font=("Arial", 12, "bold")
            ).pack(side="left", padx=2)

        # Student rows
        for student in students:
            row = ctk.CTkFrame(frame)
            row.pack(fill="x", pady=2)

            for value in student:
                ctk.CTkLabel(
                    row,
                    text=str(value),
                    width=150
                ).pack(side="left", padx=2)

    except Exception as e:
        ctk.CTkLabel(
            frame,
            text=f"Database Error:\n{e}",
            text_color="red",
            wraplength=500
        ).pack()

    ctk.CTkButton(
        frame,
        text="⬅ Back",
        command=lambda: open_dashboard(current_role)
    ).pack(pady=20)




# ======================================================
# manage_users (admin)
# ======================================================
def view_grades():
    require_access("view_grades")

    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    title = "My Grades" if current_role == "Student" else "All Grades"
    ctk.CTkLabel(frame, text=title, font=("Arial", 22)).pack(pady=10)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # =========================
        # STUDENT: own grades only
        # =========================
        if current_role == "Student":
            cursor.execute(
                "EXEC dbo.usp_Student_GetOwnGrades @StudentUserId = ?",
                (current_user_id,)
            )
            rows = cursor.fetchall()

            if not rows:
                ctk.CTkLabel(frame, text="No grades available yet").pack()
            else:
                for grade_id, course_id, grade, grade_numeric, date_entered in rows:
                    cursor.execute(
                        "SELECT CourseName FROM Courses WHERE CourseId = ?",
                        (course_id,)
                    )
                    course = cursor.fetchone()
                    course_name = course[0] if course else f"Course {course_id}"

                    ctk.CTkLabel(
                        frame,
                        text=f"{course_name} | Grade: {grade} ({grade_numeric})"
                    ).pack(anchor="w", pady=3)

        # =========================
        # ADMIN / INSTRUCTOR
        # =========================
        else:
            cursor.execute("""
                SELECT s.FullName, c.CourseName, g.GradeNumeric
                FROM Grades g
                JOIN Students s ON g.StudentId = s.StudentId
                JOIN Courses c ON g.CourseId = c.CourseId
            """)
            rows = cursor.fetchall()

            for r in rows:
                ctk.CTkLabel(
                    frame,
                    text=f"{r[0]} | {r[1]} | Grade: {r[2]}"
                ).pack(anchor="w")

            ctk.CTkButton(
                frame,
                text="Edit Grades",
                command=edit_grades
            ).pack(pady=5)

        conn.close()

    except Exception as e:
        ctk.CTkLabel(frame, text=str(e), text_color="red").pack()

    ctk.CTkButton(
        frame,
        text="⬅ Back",
        command=lambda: open_dashboard(current_role)
    ).pack(pady=20)

# ======================================================
# manage_users (admin)
# ======================================================
def edit_grades():
    require_access("edit_grades")

    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Edit Grades", font=("Arial", 22)).pack(pady=10)

    student_id = ctk.CTkEntry(frame, placeholder_text="Student ID")
    course_id = ctk.CTkEntry(frame, placeholder_text="Course ID")
    grade = ctk.CTkEntry(frame, placeholder_text="New Grade")

    student_id.pack(pady=5)
    course_id.pack(pady=5)
    grade.pack(pady=5)

    def save():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Grades
                SET GradeNumeric = ?
                WHERE StudentId = ? AND CourseId = ?
            """, (grade.get(), student_id.get(), course_id.get()))
            conn.commit()
            conn.close()
        except Exception as e:
            print(e)

    ctk.CTkButton(frame, text="Save", command=save).pack(pady=10)
    ctk.CTkButton(frame, text="⬅ Back", command=lambda: open_dashboard(current_role)).pack(pady=10)

def view_role_requests():
    require_access("manage_users")  # Admin only

    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Role Upgrade Requests", font=("Arial", 22)).pack(pady=10)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                r.RequestId,
                u.Username,
                r.RequestedRole,
                r.Reason,
                r.Status
            FROM RoleRequests r
            JOIN Users u ON r.UserId = u.UserId
            ORDER BY r.RequestedAt DESC
        """)

        requests = cursor.fetchall()
        conn.close()

        if not requests:
            ctk.CTkLabel(frame, text="No role requests found").pack()
            return

        for req in requests:
            request_id, username, role, reason, status = req

            row = ctk.CTkFrame(frame)
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row,
                text=f"{username} → {role} | {status}\nReason: {reason}",
                justify="left",
                wraplength=350
            ).pack(side="left", padx=5)

            if status == "Pending":
                ctk.CTkButton(
                    row,
                    text="Approve",
                    fg_color="green",
                    width=80,
                    command=lambda r=request_id: process_role_request(r, True)
                ).pack(side="left", padx=5)

                ctk.CTkButton(
                    row,
                    text="Deny",
                    fg_color="red",
                    width=80,
                    command=lambda r=request_id: process_role_request(r, False)
                ).pack(side="left", padx=5)

    except Exception as e:
        ctk.CTkLabel(frame, text=f"Error:\n{e}", text_color="red").pack()

    ctk.CTkButton(
        frame,
        text="⬅ Back",
        command=lambda: open_dashboard("Admin")
    ).pack(pady=20)

def process_role_request(request_id, approve):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "{CALL dbo.usp_ProcessRoleRequest (?, ?, ?)}",
            (current_user_id, request_id, 1 if approve else 0)
        )

        conn.commit()
        conn.close()

        view_role_requests()  # refresh screen

    except Exception as e:
        clear_window()
        frame = ctk.CTkFrame(app)
        frame.pack(expand=True)
        ctk.CTkLabel(frame, text=str(e), text_color="red").pack(pady=20)
        ctk.CTkButton(frame, text="⬅ Back", command=view_role_requests).pack()

# ======================================================
# manage_users (admin)
# ======================================================
def view_attendance():
    require_access("view_attendance")

    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Attendance", font=("Arial", 22)).pack(pady=10)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        if current_role == "Student":
            cursor.execute("""
                SELECT DateRecorded, Status
                FROM Attendance
                WHERE StudentId = (
                    SELECT StudentId FROM Students WHERE UserId = ?
                )
            """, (current_user_id,))
        else:
            cursor.execute("""
                SELECT s.FullName, a.DateRecorded, a.Status
                FROM Attendance a
                JOIN Students s ON a.StudentId = s.StudentId
            """)

        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            ctk.CTkLabel(frame, text=" | ".join(map(str, r))).pack(anchor="w")

    except Exception as e:
        ctk.CTkLabel(frame, text=str(e), text_color="red").pack()

    ctk.CTkButton(frame, text="Edit Attendance", command=edit_attendance).pack(pady=5)
    ctk.CTkButton(frame, text="⬅ Back", command=lambda: open_dashboard(current_role)).pack(pady=20)
# ======================================================
# manage_users (admin)
# ======================================================
def edit_attendance():
    require_access("edit_attendance")
    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Edit Attendance", font=("Arial", 22)).pack(pady=10)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.AttendanceId, s.FullName, c.CourseName, a.Status, a.DateRecorded
            FROM Attendance a
            JOIN Students s ON a.StudentId = s.StudentId
            JOIN Courses c ON a.CourseId = c.CourseId
        """)
        rows = cursor.fetchall()

        attendance_widgets = []

        def save_changes():
            try:
                for att_id, status_var in attendance_widgets:
                    cursor.execute(
                        "UPDATE Attendance SET Status = ? WHERE AttendanceId = ?",
                        (status_var.get(), att_id)
                    )
                conn.commit()
                ctk.CTkLabel(frame, text="Changes saved!", text_color="green").pack()
            except Exception as e:
                ctk.CTkLabel(frame, text=str(e), text_color="red").pack()

        for r in rows:
            att_id, full_name, course_name, status, date_recorded = r
            row_frame = ctk.CTkFrame(frame)
            row_frame.pack(fill="x", pady=2)

            ctk.CTkLabel(row_frame, text=f"{full_name} | {course_name} | {date_recorded}").pack(side="left", padx=5)

            status_var = ctk.StringVar(value="Present" if status else "Absent")
            dropdown = ctk.CTkOptionMenu(row_frame, values=["Present", "Absent"], variable=status_var)
            dropdown.pack(side="left", padx=10)

            attendance_widgets.append((att_id, status_var))

        ctk.CTkButton(frame, text="Save Changes", command=save_changes).pack(pady=10)

    except Exception as e:
        ctk.CTkLabel(frame, text=str(e), text_color="red").pack()

    ctk.CTkButton(frame, text="⬅ Back", command=lambda: open_dashboard(current_role)).pack(pady=20)

# ======================================================
# manage_users (admin)
# ======================================================
def view_public_courses():
    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Public Courses", font=("Arial", 22)).pack(pady=10)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT CourseName, Description
            FROM vw_Courses_Public
            """)
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            ctk.CTkLabel(frame, text=f"{r[0]} - {r[1]}").pack(anchor="w")

    except Exception as e:
        ctk.CTkLabel(frame, text=str(e), text_color="red").pack()

    ctk.CTkButton(frame, text="⬅ Back", command=lambda: open_dashboard(current_role)).pack(pady=20)

# ======================================================
# edit my profile
# ======================================================
def edit_my_profile():
    # Anyone logged in can edit their own profile
    if not current_user:
        clear_window()
        frame = ctk.CTkFrame(app)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(frame, text="Error: No user logged in", text_color="red").pack(pady=20)
        ctk.CTkButton(frame, text="⬅ Back", command=lambda: open_dashboard(current_role)).pack(pady=10)
        return

    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Edit Profile", font=("Arial", 22)).pack(pady=10)

    # Fetch current data from DB
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Username, Role, Clearance FROM Users WHERE UserId = ?", (current_user_id,))
        user = cursor.fetchone()
        conn.close()
    except Exception as e:
        ctk.CTkLabel(frame, text=f"Database error:\n{e}", text_color="red").pack(pady=20)
        return

    if not user:
        ctk.CTkLabel(frame, text="User not found", text_color="red").pack(pady=20)
        return

    # Input fields
    entry_username = ctk.CTkEntry(frame, placeholder_text="Username")
    entry_username.pack(pady=5)
    entry_username.insert(0, user[0])

    entry_password = ctk.CTkEntry(frame, placeholder_text="New Password", show="*")
    entry_password.pack(pady=5)

    # Only Admin can change Role/Clearance
    if current_role == "Admin":
        role_var = ctk.StringVar(value=user[1])
        ctk.CTkLabel(frame, text="Role:").pack(pady=2)
        ctk.CTkOptionMenu(frame, values=["Student", "TA", "Instructor", "Admin"], variable=role_var).pack(pady=5)

        clearance_var = ctk.StringVar(value=str(user[2]))
        ctk.CTkLabel(frame, text="Clearance Level:").pack(pady=2)
        ctk.CTkOptionMenu(frame, values=["0", "1", "2", "3"], variable=clearance_var).pack(pady=5)

    lbl_status = ctk.CTkLabel(frame, text="")
    lbl_status.pack(pady=10)

    def save_changes():
        new_username = entry_username.get().strip()
        new_password = entry_password.get().strip()

        if not new_username:
            lbl_status.configure(text="Username cannot be empty", text_color="red")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Update username
            cursor.execute(
                "UPDATE Users SET Username = ? WHERE UserId = ?",
                (new_username, current_user_id)
            )

            # Update password if provided
            if new_password:
                hashed_pw = hashlib.sha256(new_password.encode()).digest()
                cursor.execute(
                    "UPDATE Users SET PasswordHash = ? WHERE UserId = ?",
                    (hashed_pw, current_user_id)
                )

            # Only Admin can update role & clearance
            if current_role == "Admin":
                new_role = role_var.get()
                new_clearance = int(clearance_var.get())

                cursor.execute(
                    "UPDATE Users SET Role = ?, Clearance = ? WHERE UserId = ?",
                    (new_role, new_clearance, current_user_id)
                )

            conn.commit()
            conn.close()

            lbl_status.configure(text="Profile updated successfully ✔", text_color="green")

        except Exception as e:
            lbl_status.configure(text=f"Error: {e}", text_color="red")

    # Save Button
    ctk.CTkButton(
        frame,
        text="💾 Save Changes",
        fg_color="green",
        command=save_changes
    ).pack(pady=5)

    # Back Button
    ctk.CTkButton(
        frame,
        text="⬅ Back to Main Menu",
        command=lambda: open_dashboard(current_role)
    ).pack(pady=5)


    #create new user
def create_new_user():

    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Create New User", font=("Arial", 22, "bold")).pack(pady=10)

    # Input fields
    entry_username = ctk.CTkEntry(frame, placeholder_text="Username", width=250)
    entry_username.pack(pady=5)

    entry_password = ctk.CTkEntry(frame, placeholder_text="Password", show="*", width=250)
    entry_password.pack(pady=5)

    ctk.CTkLabel(frame, text="Role").pack(pady=3)
    role_var = ctk.StringVar(value="Student")
    ctk.CTkOptionMenu(
        frame,
        values=["Admin", "Instructor", "TA", "Student", "Guest"],
        variable=role_var,
        width=200
    ).pack(pady=5)

    ctk.CTkLabel(frame, text="Clearance Level").pack(pady=3)
    clearance_var = ctk.StringVar(value="0")
    ctk.CTkOptionMenu(
        frame,
        values=["0", "1", "2", "3"],
        variable=clearance_var,
        width=200
    ).pack(pady=5)

    lbl_status = ctk.CTkLabel(frame, text="")
    lbl_status.pack(pady=10)

    def save_user():
        username = entry_username.get().strip()
        password = entry_password.get().strip()
        role = role_var.get()
        clearance = int(clearance_var.get())

        if not username or not password:
            lbl_status.configure(text="Username and Password are required", text_color="red")
            return

        try:
            hashed_pw = hashlib.sha256(password.encode()).digest()

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "{CALL dbo.usp_RegisterUser (?, ?, ?, ?)}",
                (username, hashed_pw, role, clearance)
            )

            conn.commit()
            conn.close()

            lbl_status.configure(text="User created successfully!", text_color="green")

            # Clear fields
            entry_username.delete(0, "end")
            entry_password.delete(0, "end")

        except Exception as e:
            lbl_status.configure(text=f"Error: {e}", text_color="red")

    ctk.CTkButton(
        frame,
        text="Create User",
        command=save_user,
        fg_color="green"
    ).pack(pady=10)

    ctk.CTkButton(
        frame,
        text="⬅ Back",
        command=lambda: open_dashboard("Admin")
    ).pack(pady=5)


    # SAVE FUNCTION
    def save_profile():
        new_username = entry_username.get().strip()
        new_password = entry_password.get().strip()

        if not new_username:
            lbl_status.configure(text="Username cannot be empty", text_color="red")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Update password if provided
            if new_password:
                hashed_pw = hashlib.sha256(new_password.encode()).digest()
                cursor.execute("""
                    UPDATE Users
                    SET Username = ?, PasswordHash = ?
                    WHERE UserId = ?
                """, (new_username, hashed_pw, current_user_id))
            else:
                cursor.execute("""
                    UPDATE Users
                    SET Username = ?
                    WHERE UserId = ?
                """, (new_username, current_user_id))

            # Update role/clearance if Admin
            if current_role == "Admin":
                cursor.execute("""
                    UPDATE Users
                    SET Role = ?, Clearance = ?
                    WHERE UserId = ?
                """, (role_var.get(), int(clearance_var.get()), current_user_id))

            conn.commit()
            conn.close()
            lbl_status.configure(text="Profile updated successfully!", text_color="green")

        except Exception as e:
            lbl_status.configure(text=f"Error: {e}", text_color="red")

    ctk.CTkButton(frame, text="Save Changes", command=save_profile, fg_color="green").pack(pady=10)
    ctk.CTkButton(frame, text="⬅ Back", command=lambda: open_dashboard(current_role)).pack(pady=5)

# ======================================================
# ADMIN DASHBOARD
# ======================================================
def admin_dashboard():
    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Admin Dashboard", font=("Arial", 22)).pack(pady=10)

    if has_access("view_profile"):
        ctk.CTkButton(frame, text="View Profile", command=view_my_profile).pack(pady=5)


    ctk.CTkButton(frame, text="View Grades", command=view_grades).pack(pady=5)
    ctk.CTkButton(frame, text="View Attendance", command=view_attendance).pack(pady=5)
    ctk.CTkButton(frame,text="Create New User",command=create_new_user).pack(pady=5)
    ctk.CTkButton(frame,text="View All Students",command=view_all_students).pack(pady=5)
    ctk.CTkButton(frame,text="Manage Users",command=manage_users).pack(pady=5)
    ctk.CTkButton(frame,text="view role requests",command=view_role_requests).pack(pady=5)
    ctk.CTkButton(frame, text="Add Course", command=add_course).pack(pady=5)
    ctk.CTkButton(frame, text="View Public Courses", command=view_public_courses).pack(pady=5)
    ctk.CTkButton(frame,text="Logout",command=logout).pack(pady=20)
# ======================================================
# INSTRUCTOR DASHBOARD
# ======================================================
def instructor_dashboard():
    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Instructor Dashboard", font=("Arial", 22)).pack(pady=10)

    if has_access("view_profile"):
        ctk.CTkButton(frame, text="View Profile", command=view_my_profile).pack(pady=5)

    ctk.CTkButton(frame, text="View Grades", command=view_grades).pack(pady=5)
    ctk.CTkButton(frame, text="View Attendance", command=view_attendance).pack(pady=5)
    ctk.CTkButton(frame,text="View All Students",command=view_all_students).pack(pady=5)
    ctk.CTkButton(frame, text="Add Course", command=add_course).pack(pady=5)
    ctk.CTkButton(frame, text="View Public Courses", command=view_public_courses).pack(pady=5)
    ctk.CTkButton(frame, text="Logout", command=logout).pack(pady=20)


# ======================================================
# TA DASHBOARD
# ======================================================
def ta_dashboard():
    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="TA Dashboard", font=("Arial", 22)).pack(pady=10)

    if has_access("view_profile"):
        ctk.CTkButton(frame, text="View Profile", command=view_my_profile).pack(pady=5)

    ctk.CTkButton(frame, text="View Attendance", command=view_attendance).pack(pady=5)
    ctk.CTkButton(frame, text="View Public Courses", command=view_public_courses).pack(pady=5)
    ctk.CTkButton(frame, text="Logout", command=logout).pack(pady=20)

# ======================================================
# STUDENT DASHBOARD
# ======================================================
def student_dashboard():
    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Student Dashboard", font=("Arial", 22)).pack(pady=10)

    ctk.CTkButton(frame,text="View My Profile",command=view_my_profile).pack(pady=5)

    ctk.CTkButton(frame,text="View My Grades",command=view_my_grades).pack(pady=5)

    ctk.CTkButton(frame,text="Request Role Upgrade",command=request_role_upgrade).pack(pady=5)

    ctk.CTkButton(frame, text="View Public Courses", command=view_public_courses).pack(pady=5)

    ctk.CTkButton(frame, text="Logout", command=logout).pack(pady=20)

# ======================================================
# GUEST DASHBOARD
# ======================================================
def guest_dashboard():
    clear_window()
    frame = ctk.CTkFrame(app)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Guest Dashboard", font=("Arial", 22)).pack(pady=10)
    ctk.CTkButton(frame, text="View Public Courses", command=view_public_courses).pack(pady=5)    
    ctk.CTkButton(frame,text="Logout",command=logout).pack(pady=20)


# ======================================================
# GUI SETUP
# ======================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("500x450")
app.title("SRMS Secure System")

# ---------------- LOGIN UI ----------------
login_frame = ctk.CTkFrame(app)
login_frame.pack(expand=True)

ctk.CTkLabel(login_frame, text="SRMS Login", font=("Arial", 24)).pack(pady=15)

entry_user = ctk.CTkEntry(login_frame, placeholder_text="Username", width=250)
entry_user.pack(pady=5)

entry_pass = ctk.CTkEntry(login_frame, placeholder_text="Password", show="*", width=250)
entry_pass.pack(pady=5)

ctk.CTkButton(login_frame, text="Login", command=login, width=200).pack(pady=15)

lbl_login = ctk.CTkLabel(login_frame, text="")
lbl_login.pack()

app.mainloop()



