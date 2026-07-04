"""LangGraph generation graph for PACOS (ADR 0002).

Per lead: a Personalization agent produces one shared hook, then four asset agents
(cold_email, cold_dm, cover_letter, cv_notes) run in parallel using it. A
conditional edge skips the cold_email agent when the lead has no email.
"""
