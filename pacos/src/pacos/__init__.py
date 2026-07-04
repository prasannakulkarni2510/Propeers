"""PACOS — Personal AI Career Operating System (v1).

A lightweight, human-in-the-loop job-search pipeline:

  Layer 1  Asset Generator  — one Nemotron call per lead -> 4 outreach files
  Layer 2  Inbox Monitor    — read-only Gmail parse of job alerts & replies
  Layer 3  Tracker          — single tracker.csv holding all pipeline state

Nothing auto-sends. Every outreach is copy-pasted by a human after review.
Generation runs on NVIDIA Nemotron via the OpenAI-compatible NIM API.
"""

__version__ = "1.0.0"
