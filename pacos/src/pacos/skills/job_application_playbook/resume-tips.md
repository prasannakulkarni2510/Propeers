# Resume Tips: Build a Role-Specific Hiring Document

## The principle

A resume is a compact argument for an interview. It is not a complete record of everything you have studied. The strongest resume is not the one with the most technologies; it is the one that makes the required capabilities easy to verify.

The hiring manager usually wants to know:

- What can this candidate do that this role needs?
- What evidence exists beyond self-description?
- What did the candidate personally own or contribute?
- At what level of complexity have they operated?
- What questions should the interview explore?

## Resume versus CV

For most industry roles, use a concise, targeted resume. In markets where “CV” means the normal job-application document, the same evidence-first principles apply. Academic CVs can be longer when they need to document research, publications, teaching, and service. Always follow the employer’s instructions.

## Length and layout

- **Early-career candidates:** One page is an effective default when it can represent the strongest evidence clearly; two pages can be justified by directly relevant experience or projects.
- **Experienced candidates:** Two pages may be appropriate when the evidence warrants it.
- **Research/academic roles:** Follow the expected CV format, which may be longer.
- **Global hiring:** Do not include age, date of birth, marital status, photograph, or other personal details unless local law or the application specifically requires them. In many markets, these details are unnecessary and can introduce bias.

Use a clean single-column layout, readable type, consistent spacing, normal headings, and working links. The resume must still make sense when converted to plain text.

## Build a tailored version for each role family

Do not use one identical resume for every application. Maintain a verified master document, then create a version for each meaningful role type.

| Target role | Put near the top | Project / experience proof to emphasize |
|---|---|---|
| Applied AI / GenAI Engineer | Python, applied AI systems, data and API integration, evaluation | RAG/agent workflow, retrieval choices, output evaluation, integration, limitations |
| Backend Engineer | Python, APIs, SQL/databases, testing, reliability | Service boundary, request/response contracts, validation, exception handling, tests, deployment if true |
| Data Engineer | Python, SQL, ETL/ELT, data quality, orchestration if used | Pipeline stages, data validation, transformation logic, reruns, monitoring, downstream usage |
| Data Analyst | SQL, analytics, dashboards, metrics, communication | Business question, metric definition, analysis, dashboard, decision or workflow supported |
| ML Engineer | Python, ML foundations, data preparation, model evaluation, deployment | Baseline, split strategy, metrics, error analysis, reproducibility, serving/inference where true |
| Product / Founding Engineer | End-to-end implementation, product judgement, user feedback | A working product, trade-offs, iteration, integration, delivery and user outcomes |
| AEC / Engineering AI | Domain context, Python/data/AI tools, geometry or engineering workflows | Translation of domain constraints into software and measurable workflow value |

The label on the resume must be supported by evidence. If most evidence is in data pipelines and prototypes, a precise “Python / Applied AI Engineer” headline may be more credible than claiming senior production ML engineering experience.

## The bullet formula

Use:

**Strong verb + what you built/improved + how/under what constraint + result or verification.**

Four useful kinds of bullets:

1. **Delivery:** What was implemented?
2. **Quality:** How were correctness, reliability, or maintainability improved?
3. **Impact:** What changed for a user, team, or business?
4. **Judgment:** What trade-off or constraint did you handle?

### Before and after

**Weak:** “Responsible for Python, SQL and data pipelines.”

**Better, only if accurate:** “Developed Python/SQL data pipelines to prepare [source data] for [downstream workflow], adding [validation or logging] to identify [specific issue] earlier.”

**Weak:** “Worked on GenAI and RAG.”

**Better, only if accurate:** “Built a RAG prototype for [use case], connecting [document source] to [retrieval/index] and assessing responses against [evaluation method or test set].”

**Weak:** “Made a dashboard.”

**Better, only if accurate:** “Created an internal dashboard for [team/workflow] that consolidated [signals] and helped testers [specific task].”

Notice that the stronger bullets use concrete objects and verification, not adjectives. Add a quantified result only when it has a real baseline and measurement.

## Use numbers responsibly

Good metrics answer at least one of these questions: how much, how often, how fast, how accurate, how many, or what changed?

A defensible metric includes:

- A clear unit (seconds, records, defects, users, cost, precision/recall, etc.).
- A baseline or comparison where useful.
- A measurement window or method when necessary.
- A result you can reproduce or substantiate.

Do not manufacture percentages to make bullets sound stronger. When impact was not measured, describe scope and verification honestly: test cases added, services integrated, workflows supported, data types processed, or failure modes handled.

## Projects: make them interviewable

For each selected project, include:

- **Problem and user:** What need does it address?
- **Your contribution:** What did you implement personally?
- **Architecture:** The important components and data flow.
- **Evaluation:** How did you test whether it worked?
- **Trade-offs and limits:** What does it not handle well?
- **Artifact:** Repository, demo, short technical write-up, or diagram, if presentable.

Do not give a project half the page simply because it uses many tools. A small, tested system with a clear design and honest limitations can signal more skill than a large unfinished stack.

For an LLM project, prepare to discuss input data, chunking, embeddings, retrieval, prompt construction, model calls, evaluation, hallucination/failure cases, privacy, latency, and cost where relevant. Do not imply that using a vector database automatically makes a system robust.

## Skills section: keep it defensible

Group skills by function. Example categories:

- Languages: Python, SQL
- Backend: FastAPI, REST APIs, testing tools actually used
- AI/ML: RAG, embeddings, evaluation methods, model integration actually implemented
- Data: data transformation, validation, relational databases, vector databases actually used
- Frontend: React, if relevant to the target role
- Cloud / deployment: only platforms and services you can describe technically

Keep skills that are supported by projects, experience, or credible practical work. Remove vague labels such as “AI,” “coding,” or “problem solving” from a technical skills inventory; demonstrate those in evidence.

## ATS readability without keyword stuffing

1. Use the exact role-relevant term if it accurately describes your experience. If the posting says “retrieval-augmented generation,” it is reasonable to use that phrase when applicable.
2. Place critical skills in the summary, skills section, and relevant evidence bullets only where natural.
3. Use common headings and a simple reading order.
4. Avoid graphics, skill bars, complex tables, multi-column layouts, and text in images for key content.
5. Export and inspect the PDF’s selectable text.
6. Use the portal’s requested format; do not assume every ATS works identically.

ATS is not a single universal system. A human still needs a clear, credible document.

## What to cut first

- Generic objective statements (“seeking a challenging role in a reputed company”).
- Long lists of soft skills without evidence.
- Old or unrelated coursework that displaces relevant work.
- Every course and certificate ever completed.
- Tool lists repeated in every bullet.
- Personal information not requested or needed.
- Unfinished projects presented as completed products.
- Claims of leadership, architecture, or production ownership when the candidate contributed only a component.

## Role-specific summary examples

Adapt the language to real experience; do not copy a title that overstates your level.

**Applied AI / backend:** “Python-focused software engineer with experience in data workflows and applied GenAI projects. Interested in building reliable AI-enabled services, with emphasis on API integration, retrieval quality, and evaluation.”

**Data / analytics:** “Python and SQL practitioner with experience preparing data and building internal reporting tools. Focused on trustworthy pipelines, useful metrics, and making analysis easier to act on.”

**AEC technology:** “Software/AI practitioner with a mechanical-engineering foundation and exposure to AI-enabled workflows in the AEC domain. Interested in translating engineering constraints into usable data and software tools.”

Use a summary only if it improves clarity. A generic summary consumes space without adding evidence.

## Final hiring-manager audit

Score the resume from 0 to 2 on each dimension:

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Role match | Unclear | Partial | Direct and visible |
| Evidence | Mostly claims | Some proof | Specific, verifiable examples |
| Ownership | Ambiguous | Mixed | Clear individual contribution |
| Technical depth | Tool list | Some decisions explained | Design, trade-offs, and evaluation evident |
| Impact | None or inflated | Scope is clear | Verified outcome or strong evidence |
| Readability | Hard to scan | Adequate | Key facts visible quickly |
| Accuracy | Inconsistent | Minor ambiguity | Defensible, consistent claims |

A low score is not a judgment of the person; it identifies missing evidence in the document. Fix the highest-impact weakness before changing fonts or colors.

## Final test

For every key line, ask: **What follow-up question would an engineer or hiring manager ask, and could I answer it with specific details?** Your resume should set up questions you are ready to answer—not promises you cannot support.
