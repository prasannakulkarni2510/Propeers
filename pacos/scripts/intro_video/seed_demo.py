"""Seed a fictional PACOS demo dataset for the intro video.

Usage: python seed_demo.py <demo_dir>
Every person and company here is invented.
"""
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pacos.leads import load_leads  # noqa: E402
from pacos.store import PacosStore  # noqa: E402

demo = Path(sys.argv[1])
demo.mkdir(parents=True, exist_ok=True)
(demo / "out").mkdir(exist_ok=True)

PEOPLE = [
    # name, title, company, city, persona, industry, size, website, stage
    ("Asha Verma", "Engineering Manager, ML Platform", "Northwind Labs", "Bengaluru", "manager", "Software Development", "420", "northwind.example", "pending"),
    ("Rohan Iyer", "Head of Data Science", "Lumen Health", "Pune", "manager", "Hospitals and Health Care", "900", "lumenhealth.example", "pending"),
    ("Meera Pillai", "Founder & CEO", "Fernleaf Robotics", "Bengaluru", "founder", "Robotics", "45", "fernleaf.example", "pending"),
    ("Karan Desai", "Technical Recruiter", "Orbit Pay", "Mumbai", "hr", "Financial Services", "1500", "orbitpay.example", "pending"),
    ("Nikhil Rao", "Director of AI", "Tidewater Analytics", "Hyderabad", "manager", "IT Services", "2600", "tidewater.example", "pending"),
    ("Sana Qureshi", "Staff ML Engineer", "Kestrel Mobility", "Bengaluru", "manager", "Transportation", "300", "kestrel.example", "ready"),
    ("Vikram Shetty", "VP Engineering", "Quill Learning", "Chennai", "cto", "E-Learning", "160", "quill.example", "ready"),
    ("Isha Bansal", "Talent Partner, AI", "Northwind Labs", "Bengaluru", "hr", "Software Development", "420", "northwind.example", "sent"),
    ("Aditya Menon", "Lead Data Scientist", "Saffron Retail", "Gurugram", "manager", "Retail", "5000", "saffron.example", "sent"),
    ("Tara Fernandes", "Head of ML", "Monsoon AI", "Bengaluru", "manager", "Software Development", "80", "monsoon.example", "sent"),
    ("Dev Malhotra", "CTO", "Pebble Insurance", "Mumbai", "cto", "Insurance", "240", "pebble.example", "replied"),
    ("Priya Shah", "Engineering Manager", "Lumen Health", "Pune", "manager", "Hospitals and Health Care", "900", "lumenhealth.example", "interested"),
    ("Arjun Nair", "Principal Scientist", "Fernleaf Robotics", "Bengaluru", "manager", "Robotics", "45", "fernleaf.example", "interview"),
    ("Neha Kulkarni", "Hiring Manager, GenAI", "Orbit Pay", "Mumbai", "manager", "Financial Services", "1500", "orbitpay.example", "rejected"),
]

cols = ["full_name", "job_title", "company_name", "city", "linkedin_url", "persona_tag", "email",
        "company_size", "industry", "company_website", "funding_stage", "predicted_email",
        "email_confidence", "email_status"]
with open(demo / "leads.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for name, title, co, city, persona, ind, size, site, _ in PEOPLE:
        first, last = name.lower().split()[0], name.lower().split()[-1]
        email = f"{first}.{last}@{site}"
        w.writerow([name, title, co, city, f"https://www.linkedin.com/in/{first}-{last}-demo",
                    persona, "", size, ind, f"https://{site}", "",
                    email, "high" if persona != "founder" else "medium", "predicted"])

(demo / "base_cv.txt").write_text(
    "Riya Sen, Data Scientist (demo CV)\n"
    "4 years building ML systems in Python.\n"
    "- Built a demand-forecasting model that cut stock-outs 18% at a retail startup.\n"
    "- Shipped a retrieval-augmented support assistant (LangChain, FastAPI) used by 40 agents.\n"
    "- Owns model monitoring: drift alerts, weekly retraining, Grafana dashboards.\n"
    "Skills: Python, PyTorch, scikit-learn, SQL, LLM apps, MLOps.\n",
    encoding="utf-8",
)

store = PacosStore(demo / "tracker.db")
store.ingest_leads(load_leads(demo / "leads.csv"))
ids = {r["full_name"]: r["lead_id"] for r in store.get_leads()}
today = date.today()

EMAIL = """Subject: Forecasting at {co}

Hi {first},

I saw that {co} is growing its ML team in {city}. I built a demand-forecasting model that cut stock-outs by 18%, and I now run monitoring and weekly retraining for it in production.

If you are hiring for applied ML this quarter, I'd value 15 minutes to hear what the team is working on.

Best,
Riya"""
DM = "Hi {first}, I build production ML (forecasting, a RAG support assistant used by 40 agents). Saw {co} is hiring in {city}; open to a short chat?"

for name, title, co, city, *_rest, stage in PEOPLE:
    lid = ids[name]
    first = name.split()[0]
    if stage == "pending":
        continue
    hook = f"{co}'s ML work in {city} lines up with the forecasting system I run in production."
    store.upsert_from_generation(lid, hook)
    store.save_assets(lid, {
        "cold_email.txt": EMAIL.format(co=co, first=first, city=city),
        "cold_dm.txt": DM.format(co=co, first=first, city=city),
        "cover_letter.txt": f"Dear {first},\n\nI am applying for applied ML roles at {co}...",
        "cv_notes.txt": "Lead with the forecasting result; move MLOps above the RAG project.",
    })
    if stage == "ready":
        continue
    sent = today - timedelta(days={"sent": 6, "replied": 9, "interested": 12, "interview": 16, "rejected": 10}[stage])
    store.mark_sent(lid, channel="email", sent_date=sent)
    if stage == "sent":
        continue
    reply = sent + timedelta(days=3)
    if stage == "replied":
        store.mark_reply(lid, intent="follow-up", reply_date=reply)
    elif stage == "interested":
        store.mark_reply(lid, intent="interested", reply_date=reply)
        store.add_note(lid, "Wants a call Thursday; send portfolio link.", on=reply)
    elif stage == "interview":
        store.mark_reply(lid, intent="interested", reply_date=reply)
        store.mark_status(lid, "interview")
        store.add_note(lid, "Technical round booked for next Tuesday.", on=reply)
    elif stage == "rejected":
        store.mark_reply(lid, intent="rejected", reply_date=reply)

cv = store.create_cv("Data Scientist", (demo / "base_cv.txt").read_text(encoding="utf-8"), "")
store.set_active_cv(cv["cv_id"])
store.export_csv(demo / "tracker.csv")
print("seeded", len(ids), "leads;", store.status_counts())
