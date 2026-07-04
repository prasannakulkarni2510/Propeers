"""PACOS backend — FastAPI over the tested `pacos` core package.

The API is a thin, human-in-the-loop layer: it reads leads/assets/tracker and
lets you trigger generation and record approvals. It never sends anything.
"""
