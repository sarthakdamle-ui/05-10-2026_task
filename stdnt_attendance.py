import csv
import sqlite3
from datetime import date, datetime
from pathlib import Path

DB_FILE = Path(__file__).with_name("attendance.db")


class AttendanceERP:
    """Simple SQLite-backed student attendance manager."""

    def __init__(self, database=DB_FILE):
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    roll_no TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    section TEXT NOT NULL DEFAULT ''
                )
            """)
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    attendance_date TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
                    UNIQUE(student_id, attendance_date),
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                )
            """)

    def add_student(self, roll_no, name, class_name, section=''):
        with self.connection:
            self.connection.execute(
                "INSERT INTO students (roll_no, name, class_name, section) VALUES (?, ?, ?, ?)",
                (roll_no.strip(), name.strip(), class_name.strip(), section.strip())
            )

    def students(self):
        return self.connection.execute(
            "SELECT * FROM students ORDER BY class_name, section, roll_no"
        ).fetchall()

    def mark_attendance(self, roll_no, attendance_date, status):
        student = self.connection.execute(
            "SELECT student_id FROM students WHERE roll_no = ?", (roll_no.strip(),)
        ).fetchone()
        if not student:
            raise ValueError(f"No student found with roll number {roll_no!r}.")
        with self.connection:
            self.connection.execute("""
                INSERT INTO attendance (student_id, attendance_date, status)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id, attendance_date)
                DO UPDATE SET status = excluded.status
            """, (student['student_id'], attendance_date, status))

    def daily_report(self, attendance_date):
        return self.connection.execute("""
            SELECT s.roll_no, s.name, s.class_name, s.section, a.status
            FROM students s
            LEFT JOIN attendance a
              ON a.student_id = s.student_id AND a.attendance_date = ?
            ORDER BY s.class_name, s.section, s.roll_no
        """, (attendance_date,)).fetchall()

    def student_summary(self, roll_no):
        student = self.connection.execute(
            "SELECT * FROM students WHERE roll_no = ?", (roll_no.strip(),)
        ).fetchone()
        if not student:
            raise ValueError(f"No student found with roll number {roll_no!r}.")
        counts = self.connection.execute("""
            SELECT status, COUNT(*) AS total FROM attendance
            WHERE student_id = ? GROUP BY status
        """, (student['student_id'],)).fetchall()
        result = {row['status']: row['total'] for row in counts}
        return student, result

    def export_daily_csv(self, attendance_date, filename):
        rows = self.daily_report(attendance_date)
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['Date', 'Roll No', 'Student Name', 'Class', 'Section', 'Status'])
            for row in rows:
                writer.writerow([attendance_date, row['roll_no'], row['name'],
                                 row['class_name'], row['section'], row['status'] or 'Not marked'])
        return len(rows)

    def close(self):
        self.connection.close()


def ask_date(prompt):
    value = input(f"{prompt} [YYYY-MM-DD, default {date.today()}]: ").strip()
    if not value:
        return date.today().isoformat()
    try:
        return datetime.strptime(value, '%Y-%m-%d').date().isoformat()
    except ValueError as exc:
        raise ValueError('Please enter the date in YYYY-MM-DD format.') from exc


def show_daily_report(app, attendance_date):
    rows = app.daily_report(attendance_date)
    print(f"\nAttendance report for {attendance_date}")
    print('-' * 82)
    print(f"{'Roll':<12}{'Name':<25}{'Class':<15}{'Section':<12}{'Status'}")
    print('-' * 82)
    totals = {'Present': 0, 'Absent': 0, 'Late': 0, 'Not marked': 0}
    for row in rows:
        status = row['status'] or 'Not marked'
        totals[status] = totals.get(status, 0) + 1
        print(f"{row['roll_no']:<12}{row['name']:<25}{row['class_name']:<15}"
              f"{row['section']:<12}{status}")
    print('-' * 82)
    print(' | '.join(f'{key}: {value}' for key, value in totals.items()))
    if not rows:
        print('No students have been added yet.')


def main():
    app = AttendanceERP()
    print('STUDENT ATTENDANCE ERP')
    print(f'Database: {DB_FILE}')
    try:
        while True:
            print("""
1. Add student
2. View student list
3. Mark or update attendance
4. Daily attendance report
5. Student attendance summary
6. Export daily report to CSV
0. Exit
""")
            choice = input('Choose an option: ').strip()
            try:
                if choice == '1':
                    roll = input('Roll number: ').strip()
                    name = input('Student name: ').strip()
                    class_name = input('Class/grade: ').strip()
                    section = input('Section (optional): ').strip()
                    if not all([roll, name, class_name]):
                        print('Roll number, name, and class are required.')
                        continue
                    app.add_student(roll, name, class_name, section)
                    print(f'Student {name} added.')
                elif choice == '2':
                    rows = app.students()
                    print('\nStudents')
                    print('-' * 70)
                    for row in rows:
                        print(f"{row['roll_no']:<12} {row['name']:<25} "
                              f"Class {row['class_name']}  Section {row['section']}")
                    print(f'Total students: {len(rows)}')
                elif choice == '3':
                    attendance_date = ask_date('Attendance date')
                    roll = input('Roll number: ').strip()
                    status = input('Status (P=Present, A=Absent, L=Late): ').strip().upper()
                    statuses = {'P': 'Present', 'A': 'Absent', 'L': 'Late'}
                    if status not in statuses:
                        print('Choose P, A, or L.')
                        continue
                    app.mark_attendance(roll, attendance_date, statuses[status])
                    print(f"{roll}: {statuses[status]} on {attendance_date} (saved).")
                elif choice == '4':
                    show_daily_report(app, ask_date('Report date'))
                elif choice == '5':
                    roll = input('Roll number: ').strip()
                    student, counts = app.student_summary(roll)
                    total = sum(counts.values())
                    present_equivalent = counts.get('Present', 0) + counts.get('Late', 0)
                    percent = (present_equivalent / total * 100) if total else 0
                    print(f"\n{student['name']} ({student['roll_no']}) — "
                          f"Class {student['class_name']} {student['section']}")
                    print(f"Present: {counts.get('Present', 0)} | Absent: {counts.get('Absent', 0)} | "
                          f"Late: {counts.get('Late', 0)} | Marked days: {total}")
                    print(f'Attendance rate (Present + Late): {percent:.1f}%')
                elif choice == '6':
                    attendance_date = ask_date('Export date')
                    filename = input('CSV filename [attendance-report.csv]: ').strip()
                    if not filename:
                        filename = 'attendance-report.csv'
                    if not filename.lower().endswith('.csv'):
                        filename += '.csv'
                    count = app.export_daily_csv(attendance_date, filename)
                    print(f'Exported {count} student rows to {Path(filename).resolve()}')
                elif choice == '0':
                    print('Goodbye!')
                    break
                else:
                    print('Please choose one of the listed options.')
            except (ValueError, sqlite3.IntegrityError) as error:
                print(f'Could not complete that action: {error}')
    finally:
        app.close()


if __name__ == '__main__':
    main()
