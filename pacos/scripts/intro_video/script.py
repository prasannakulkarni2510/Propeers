"""Scenes for the PACOS intro video: kind, on-screen caption, narration.

Kind is "title" / "end" for the cards, "app" for a captured scene. The order
must match the scenes capture_demo.py records.
"""
SCENES = [
    ("title", "", "This is PACOS, a personal AI career operating system. It drafts your job-search outreach and keeps track of every person you write to. It never sends anything. You do."),
    # chat
    ("app", "Start in the chat", "Everything starts in the chat. Tell it what happened, ask where things stand with someone, or paste a job description."),
    ("app", "Who to chase this week", "Ask who to follow up with this week, and it lists the people whose follow-up is due: when you wrote, how, and what to do next."),
    ("app", "Drafts from your real CV", "Ask for a draft and it writes one from your CV, using only experience you actually have. You read it, copy it, and send it yourself."),
    ("app", "Nothing saved until you apply", "When someone replies, just say so. PACOS proposes the update, here an interview, and nothing is saved until you click Apply."),
    # my people
    ("app", "My people: one board", "My people is your whole search on one board. Every person sits in exactly one column: to write, ready to send, waiting for a reply, replied, and finished."),
    ("app", "Write messages in batches", "People in To write have no messages yet. One click writes them for the next ten: a cold email, a LinkedIn note, a cover letter and CV notes for each, all from the CV in use."),
    ("app", "Ready to send", "Open someone who is ready and every message is there, one tab each. The email is marked likely, because it is predicted, never verified. Copy a message, send it yourself, then say how you sent it. That starts the follow-up clock."),
    ("app", "Waiting, and follow-ups", "Waiting for a reply shows who owes you an answer. When the clock runs out, the card says follow-up due. Heard back? Mark them interested, asked to follow up, or rejected, or put a reminder in your calendar."),
    ("app", "Search, and check the inbox", "Search finds anyone by name or company. Check inbox reads replies from Gmail, read-only, and moves those people along the board for you."),
    # find people
    ("app", "Find people at a company", "Find people starts from a company. Give it a name, and if you like a role, a city and a tech stack, and it builds the searches that surface the people behind the job."),
    ("app", "One search per kind of person", "You get one search for each kind of person: hiring managers, engineering leads, directors, technical recruiters, talent acquisition and HR partners. Open it on LinkedIn, run it as a Google search, or copy the query. It is a template, not a model call, so it is instant and repeatable."),
    ("app", "Import them in one step", "Find and import goes one step further. It collects the LinkedIn profiles the search finds and adds each person to My people with a likely work email, guessed from the company's pattern. If Google blocks it, paste the results page instead."),
    # cv
    ("app", "A CV for each kind of role", "My CV keeps a version for each kind of role. Every draft is written from the one in use."),
    ("end", "", "PACOS. It drafts. You decide. You send."),
]
