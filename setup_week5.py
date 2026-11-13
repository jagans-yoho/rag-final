import os
import sqlite3
import docx
import openpyxl
import fitz  # PyMuPDF
from PIL import Image, ImageDraw

os.makedirs("data", exist_ok=True)

doc1 = fitz.open()
p1 = doc1.new_page()
p1.insert_text((50, 50), "Policy HR-204: Employees get 18 days annual paid leave per year. Carry forward limit is 10 days.")
p2 = doc1.new_page()
p2.insert_text((50, 50), "Travel Policy TRV-901: Metro city daily per diem is INR 2,500. Hotel cap is INR 4,000 per night.")
doc1.save("data/company_policies.pdf")
doc1.close()

doc2 = fitz.open()
p_hr1 = doc2.new_page()
p_hr1.insert_text((50, 50), "HR Confidential Memo: Annual salary revision cycle happens in April with 8% to 15% band hike.")

img = Image.new("RGB", (600, 200), color=(255, 255, 255))
d = ImageDraw.Draw(img)
d.text((20, 50), "Executive Bonus Policy BON-77: VP roles receive 20% annual variable bonus.", fill=(0, 0, 0))
img.save("data/temp_scan.png")

p_hr2 = doc2.new_page()
p_hr2.insert_image(fitz.Rect(50, 50, 550, 250), filename="data/temp_scan.png")
doc2.save("data/hr_confidential.pdf")
doc2.close()
os.remove("data/temp_scan.png")

word_doc = docx.Document()
word_doc.add_heading("Section 1: IT & Security", level=1)
word_doc.add_paragraph("Code ETH-501: Company laptops must never be used for commercial freelancing. MFA is mandatory.")
word_doc.add_heading("Section 2: Offboarding", level=1)
word_doc.add_paragraph("Protocol OFF-109: Standard notice period is 60 days. All IT assets must be returned on last day.")
word_doc.save("data/employee_handbook.docx")

wb = openpyxl.Workbook()
ws1 = wb.active
ws1.title = "Leave_Balances"
ws1.append(["emp_id", "name", "allowed", "taken", "remaining"])
ws1.append(["EMP101", "Aarav Sharma", 18, 6, 12])
ws1.append(["EMP102", "Diya Patel", 18, 5, 13])

ws2 = wb.create_sheet(title="Department_Roster")
ws2.append(["emp_id", "department", "role"])
ws2.append(["EMP101", "Engineering", "Software Engineer"])
ws2.append(["EMP102", "Human Resources", "HR Generalist"])
ws2.append(["EMP103", "Engineering", "Tech Lead"])
wb.save("data/hr_records.xlsx")

conn = sqlite3.connect("enterprise_hr.db")
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS employees")
cur.execute("DROP TABLE IF EXISTS leaves")
cur.execute("CREATE TABLE employees (emp_id TEXT PRIMARY KEY, name TEXT, department TEXT)")
cur.execute("CREATE TABLE leaves (emp_id TEXT PRIMARY KEY, total_allowed INT, leaves_taken INT)")
cur.executemany("INSERT INTO employees VALUES (?, ?, ?)", [
    ("EMP101", "Aarav Sharma", "Engineering"),
    ("EMP102", "Diya Patel", "Human Resources"),
    ("EMP103", "Meera Nair", "Engineering")
])
cur.executemany("INSERT INTO leaves VALUES (?, ?,?)", [
    ("EMP101", 18, 6),
    ("EMP102", 18, 5),
    ("EMP103", 18, 2)
])
conn.commit()
conn.close()
print("Setup complete: 2 PDFs, 1 DOCX, 1 XLSX (2 sheets), and SQLite DB created.")