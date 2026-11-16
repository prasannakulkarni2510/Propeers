# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One operator: a job seeker running their own outreach (data science / AI roles, India). They open PACOS between other things to see who to write to, copy a draft, and record what happened. Recruiters and interviewers also visit the hosted demo through the trial login and the About page.

## Product Purpose

PACOS (Personal AI Career Operating System) turns a lead (a hiring manager, recruiter or founder) into personalised outreach drafts grounded in the operator's CV, then tracks each lead from first draft to reply. Success is the operator sending more good, specific messages and never losing track of a follow-up.

## Positioning

PACOS never sends anything. Every draft is copied and sent by hand, every lead and every tracker change proposed by the assistant is confirmed by the operator first.

## Operating Context

- Chat is the home page: ask where a lead stands, report what happened, ask for a draft, paste a JD or a screenshot.
- A lead moves through: needs drafts, ready to send, waiting for a reply, in conversation (replied, interested, interview, offer), closed.
- Sending happens outside PACOS (email client, LinkedIn). The LinkedIn connection note limit is 300 characters.
- Hosted on Render behind a login; also runs locally and as a packaged exe.

## Capabilities and Constraints

- Terms (see ../CONTEXT.md): Lead, Asset (cold email, cold DM, cover letter, CV notes), Operator, Tracker, Lead proposal, Search variant.
- Frontend: React 18, Vite, react-router, zustand. No UI library.
- Interface scope decided 2026-11-16: three pages (Chat, Pipeline, Find people) plus About. Removed from the interface, kept in the backend: intro video autoplay, agent status board, dry-run and review-hooks, job alerts, daily digest, unmatched-replies table, list views, domain and asset filters, Jobs tab, bulk copy emails.
- Predicted emails must always read as likely, never verified.

## Brand Commitments

- Name PACOS, written PAC + OS with the OS in the logo red. Logo at public/pacos-logo.png.
- Plain, direct voice. No hype.

## Evidence on Hand

- Real lead data in the tracker (hundreds of leads). No testimonials, metrics or customer claims exist; none may be invented.
- public/pacos-intro.mp4 (intro video).

## Product Principles

1. The operator decides; PACOS proposes.
2. One obvious next action per lead.
3. Say what is predicted and what is confirmed.
4. Fewer places to look beats more views of the same data.
