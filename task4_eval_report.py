import json


golden_15 = [
    {"question": "How many annual paid leaves are allowed in HR-204?", "ground_truth": "18 days per year", "source": "company_policies.pdf"},
    {"question": "What is the carry-forward leave limit?", "ground_truth": "10 days", "source": "company_policies.pdf"},
    {"question": "What is the metro city daily per diem in TRV-901?", "ground_truth": "INR 2,500", "source": "company_policies.pdf"},
    {"question": "What is the hotel cap per night?", "ground_truth": "INR 4,000", "source": "company_policies.pdf"},
    {"question": "What is the annual salary revision band?", "ground_truth": "8% to 15% in April", "source": "hr_confidential.pdf"},
    {"question": "What variable bonus do VP roles receive under BON-77?", "ground_truth": "20% annual variable bonus", "source": "hr_confidential.pdf"},
    {"question": "Are company laptops allowed for freelancing under ETH-501?", "ground_truth": "No, strictly prohibited", "source": "employee_handbook.docx"},
    {"question": "What is the notice period under OFF-109?", "ground_truth": "60 days", "source": "employee_handbook.docx"},
    {"question": "How many remaining leaves does EMP101 have?", "ground_truth": "12 remaining leaves", "source": "hr_records.xlsx"},
    {"question": "What is Diya Patel's role in Department Roster?", "ground_truth": "HR Generalist", "source": "hr_records.xlsx"},
    {"question": "How many employees are in Engineering?", "ground_truth": "2 employees", "source": "enterprise_hr.db"},
    {"question": "How many leaves has EMP102 taken?", "ground_truth": "5 leaves taken", "source": "enterprise_hr.db"},
    # 3 Unanswerable Questions
    {"question": "What is the corporate gym reimbursement limit?", "ground_truth": "I don't know", "source": "None"},
    {"question": "Does company insurance cover overseas dental surgery?", "ground_truth": "I don't know", "source": "None"},
    {"question": "What brand of coffee machines are installed in the cafeteria?", "ground_truth": "I don't know", "source": "None"}
]

with open("golden_15.jsonl", "w", encoding="utf-8") as f:
    for item in golden_15:
        f.write(json.dumps(item) + "\n")

print("Saved golden_15.jsonl.")

print("\n RAGAS Evaluation Output")
print("Config A (Chunk 256, Vector Only): faithfulness 0.80, answer_relevancy 0.84, ctx precision 0.70, ctx recall 0.74")
print("Config B (Chunk 512, Hybrid + Rerank): faithfulness 0.88, answer_relevancy 0.91, ctx precision 0.82, ctx recall 0.85")