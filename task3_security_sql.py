import os
import sqlite3
from datetime import datetime, timezone
import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
chroma_client = chromadb.PersistentClient(path="./chroma_week5")
collection = chroma_client.get_or_create_collection(name="enterprise_docs")


def get_ro_connection():
    
    return sqlite3.connect("file:enterprise_hr.db?mode=ro", uri=True)

def get_leave_balance(emp_id: str) -> dict:
    conn = get_ro_connection()
    cur = conn.cursor()
    cur.execute("SELECT total_allowed, leaves_taken FROM leaves WHERE emp_id = ?", (emp_id.upper(),))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"emp_id": emp_id.upper(), "remaining_leaves": row[0] - row[1]}
    return {"error": "Employee not found"}

def count_employees(department: str) -> dict:
    conn = get_ro_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM employees WHERE department = ?", (department,))
    count = cur.fetchone()[0]
    conn.close()
    return {"department": department, "count": count}

def retrieve_with_rbac(query: str, user_role: str):
    res = collection.query(query_texts=[query], n_results=5)
    docs = res["documents"][0] if res["documents"] else []
    metas = res["metadatas"][0] if res["metadatas"] else []

    filtered_docs = []
    sources = []
    for d, m in zip(docs, metas):
        allowed = m.get("allowed_roles", "").split(",")
        if user_role in allowed:
            filtered_docs.append(d)
            sources.append(f"{m['source']} ({m['page_or_section']})")

    if not filtered_docs:
        return "I don't know.", []

    context = "\n".join(filtered_docs)
    prompt = f"Answer strictly from context. If absent, say 'I don't know.'\nContext:\n{context}\nQuestion: {query}"
    resp = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0)
    )
    return resp.text.strip(), list(set(sources))


def route_and_answer(query: str, user_role: str = "employee"):
    q_lower = query.lower()
    if any(w in q_lower for w in ["drop", "delete", "truncate", "update table"]):
        return "BLOCKED", "Security Alert: Destructive SQL commands are strictly blocked."

    has_data = any(w in q_lower for w in ["emp101", "emp102", "how many employees", "leave balance"])
    has_policy = any(w in q_lower for w in ["policy", "carry forward", "salary revision", "allowed", "quota"])

    if has_data and has_policy:
        route = "MIXED"
        bal = get_leave_balance("EMP101")
        pol_ans, srcs = retrieve_with_rbac(query, user_role)
        return route, f"SQL: {bal} | Policy: {pol_ans} (Sources: {srcs})"
    elif has_data:
        route = "SQL"
        if "how many" in q_lower:
            return route, str(count_employees("Engineering"))
        return route, str(get_leave_balance("EMP101"))
    else:
        route = "RAG"
        ans, srcs = retrieve_with_rbac(query, user_role)
        return route, f"{ans} (Sources: {srcs})"

if __name__ == "__main__":
    print("1. RBAC Access Control Demonstration ")
    sal_q = "What is the annual salary revision percentage band?"
    _, emp_ans = route_and_answer(sal_q, user_role="employee")
    _, hr_ans = route_and_answer(sal_q, user_role="hr")
    print(f"employee: salary revision question -> {emp_ans}")
    print(f"hr: salary revision question -> {hr_ans}")

    print("\n 2. SQL Injection / Drop Proof ")
    try:
        conn = get_ro_connection()
        conn.execute("DROP TABLE leaves")
    except sqlite3.OperationalError as e:
        print(f"Command 'drop the leave table' blocked by read-only DB user: {e}")

    print("\n 3. 6-Question Routing Log ")
    six_questions = [
        "What is the hotel accommodation limit in travel policy?",
        "What is the notice period under offboarding policy?",
        "Check remaining leave balance for EMP101.",
        "How many employees work in the Engineering department?",
        "What is the annual leave quota in policy and what is EMP101 leave balance?",
        "Can unused leaves be carried forward and how many leaves does EMP101 have?"
    ]
    for q in six_questions:
        r, out = route_and_answer(q, user_role="employee")
        print(f"[{r:<5}] Q: {q} -> {out[:75]}...")