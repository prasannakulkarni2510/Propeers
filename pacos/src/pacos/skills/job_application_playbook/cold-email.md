# Cold Email: Hiring-Manager Playbook

## The hiring manager’s mental filter

A cold email competes with work already on the recipient’s desk. The reader is not asking, “Is this candidate passionate?” They are asking:

1. Is this relevant to a problem or role I own?
2. Is there credible evidence that the candidate can help?
3. Will responding take very little effort?
4. Does the message feel researched rather than mass-produced?

The email must answer those questions quickly. Aim for roughly **90–150 words** for a first contact, unless the recipient explicitly requests a detailed note. Keep one objective per email.

## Choose the recipient before choosing the wording

| Recipient | What they can reasonably do | Best ask |
|---|---|---|
| Hiring manager / team lead | Assess role fit, suggest the right opening, possibly interview | Ask whether the candidate’s evidence maps to a specific need |
| Engineer on the team | Explain the work, share context, potentially refer | Ask one thoughtful question or whether a short conversation is appropriate |
| Founder / early-stage leader | Evaluate initiative and immediate usefulness | Tie a specific capability to a current product or execution problem |
| Recruiter / talent partner | Route candidates and clarify process | Ask whether the background fits a named role or team |
| Research lead / professor | Evaluate research preparation and interests | Connect a specific research question or technical skill to the group’s work |
| Former colleague / mutual contact | Provide context and trust | Make the request clear and easy to decline |

Do not ask a random engineer to “get you a job.” Do not ask a recruiter to judge a deep technical design. Match the request to the recipient’s role.

## Company and role adaptation

| Company / role type | What to emphasize | Evidence that helps | Avoid leading with |
|---|---|---|---|
| AI product company / applied GenAI | Reliability of the application, retrieval quality, evaluation, latency/cost awareness, user workflow | A shipped or demonstrable RAG/agent workflow, evaluation method, integration details | “I know all the latest models” without a working example |
| Backend / platform engineering | APIs, data models, failure handling, observability, testing, maintainability | FastAPI service, clear API contract, tests, error handling, deployment details | A long list of AI libraries when the role is backend-first |
| Data engineering / analytics | Data quality, transformations, SQL, repeatability, business definitions | Pipeline, validation checks, dashboard used by a real stakeholder | ML buzzwords unrelated to the job |
| Startup / founding engineer | Ability to turn ambiguity into a working product, make trade-offs, learn fast | A small end-to-end project, user feedback, clear ownership boundaries | Claiming to be a “10x engineer” |
| Enterprise / consulting / services | Delivery discipline, stakeholder communication, requirements, documentation, collaboration | Internal tools, dashboards, client/domain context, clear problem-to-outcome stories | Overly casual language or unsupported scale claims |
| AEC / engineering software | Domain-aware workflows, geometry, engineering constraints, AI applied to specialist users | Relevant domain work, structured data workflows, engineering background | Treating domain context as irrelevant or explaining every academic detail |
| Research / applied science | A focused question, experimental rigor, relevant methods, reproducibility | Technical report, benchmark, careful ablation/evaluation, related coursework | A generic “I want to do AI research” message |

## The five-part structure

1. **Subject:** Specific, neutral, and easy to parse.
2. **Reason for contacting them:** One real company, product, team, or job observation.
3. **Fit:** One or two relevant candidate facts, each tied to the need.
4. **Evidence:** A link to one strong artifact if it genuinely helps—repository, demo, technical write-up, or portfolio.
5. **Low-friction ask:** A yes/no question or a short, bounded request.

A strong email is not a biography. Your resume already contains the biography.

## Subject-line options

- `Question about [Team]’s work on [specific problem]`
- `Applied GenAI engineer — [relevant evidence]`
- `Interest in [Role Title] at [Company]`
- `Python/SQL experience relevant to [team or workflow]`
- `Prospective research fit: [specific topic]`

Avoid “URGENT,” “Please give me a chance,” “Job needed,” and vague subjects such as “Hello sir.” Do not misrepresent a referral or existing relationship.

## Template: hiring manager for a named role

**Subject:** Interest in [Role Title] — [specific relevant capability]

Hi [Name],

I saw that [Company/Team] is working on [specific product, workflow, or problem]. I’m interested in the [Role Title] role because it calls for [requirement 1] and [requirement 2].

In my work on [relevant project/work], I used [skill] to [specific action] and [outcome or verifiable artifact]. I’ve also worked with [second relevant skill], which seems useful for [part of the team’s work]. Here’s [a concise demo/write-up/resume link] if helpful: [link].

Would my background be relevant to the team’s current needs? If so, I’d appreciate the chance to discuss the role briefly.

Best,  
[Full name]  
[LinkedIn] · [Portfolio/GitHub, if relevant]

## Template: AI/GenAI product team

**Subject:** RAG / agent workflows relevant to [Company’s use case]

Hi [Name],

I noticed [specific product feature or customer workflow] at [Company]. I’m interested in how your team handles [relevant challenge, such as retrieval quality, grounding, tool execution, or evaluation].

My recent work includes [truthful example: a RAG/agent project, API integration, retrieval pipeline, or evaluation harness]. I can explain the design choices around [one concrete detail] and where I would measure failure modes. A short walkthrough is here: [link].

Is this experience potentially relevant to your team, or is there another person I should contact?

Best,  
[Name]

**Hiring-manager note:** “Built a RAG system” is not sufficient evidence by itself. Be ready to explain the data source, chunking/indexing choices, retrieval method, prompting, evaluation set, failure cases, and trade-offs. Mention only components actually implemented.

## Template: backend / platform role

**Subject:** Python backend experience relevant to [Team/Product]

Hi [Name],

I’m reaching out about [Role Title] because [Company]’s work on [specific system or customer problem] aligns with the kind of engineering I’m targeting. My relevant experience includes building with Python and SQL and developing [API/service/pipeline] for [purpose]. In [project], I focused on [validation, API design, failure handling, testing, or data reliability—choose what is true].

Here is the implementation or write-up: [link]. Would it be useful for me to apply with this background, or is there a particular capability you prioritize for this role?

Regards,  
[Name]

## Template: founder / small team

**Subject:** Could help with [specific problem] at [Company]

Hi [Name],

I saw [specific company signal: product launch, open role, feature, technical post]. It looks like [careful, non-presumptuous observation about a problem the team may be solving].

I’ve worked with [relevant skills] to build [concrete tool/project] and would be interested in applying that to [specific part of the product]. Here is the most relevant example: [link]. I’m not assuming this is a current priority, but would a short conversation about the team’s needs be useful?

Thanks,  
[Name]

## Template: recruiter

**Subject:** [Role Title] — Python / GenAI / backend fit

Hi [Name],

I’m interested in the [exact role title, requisition ID if available] at [Company]. My closest matches are [requirement 1] through [evidence] and [requirement 2] through [evidence]. My resume is here: [link or attachment, based on the recruiter’s process].

Could you let me know whether this background matches the role’s must-have requirements? I’m happy to provide any additional information needed.

Best,  
[Name]  
[Phone, optional] · [LinkedIn]

## Template: research lead

**Subject:** Question about [research group’s specific topic]

Dear Dr. [Surname],

I read your group’s work on [specific paper/project/question], especially [a precise method or finding]. I’m interested in exploring [narrow related question] and have preparation in [relevant methods, coursework, or engineering/software experience]. I have also worked on [relevant project], where I [specific contribution].

Would you be open to advising whether my background could fit a research internship or project in this area? I can send a short technical summary and CV if useful.

Sincerely,  
[Name]

## How to prove fit from a mixed background

A candidate moving from mechanical engineering/data analytics into AI engineering should not hide the transition or make it the whole story. Use a simple bridge:

**Prior foundation → recent technical evidence → target role.**

Example: “My mechanical-engineering background trained me to work with constrained, quantitative problems. Since then, I’ve developed Python/SQL workflows and worked on GenAI-oriented tools. I’m targeting applied AI roles where software implementation and domain problem-solving meet.”

This works only if the resume and projects support the claim. For a backend-first role, lead with the API/pipeline. For a research role, lead with the question and experimental evidence. For AEC software, the domain background may be a differentiator.

## Follow-up policy

- Send one brief follow-up after about **5–7 business days** if there has been no response.
- A second and final follow-up may be reasonable after another **7–10 business days**, depending on the context.
- Stop if the person declines, says they are not the right contact, or asks not to be contacted.
- Add new value in the follow-up: a relevant project update, a clearer fit statement, or a precise question. Do not send “just checking” repeatedly.

**Follow-up example**

Hi [Name] — following up once on my note about [role/problem]. The closest relevant example is [one-line evidence + link]. If this is not a priority for the team, no problem; I’d appreciate any direction to the right contact if one comes to mind. Thanks, [Name]

## Final pre-send checklist

- [ ] The company and recipient are correct.
- [ ] The first paragraph is specific to this company or role.
- [ ] The proof is relevant and defensible.
- [ ] There is one clear ask.
- [ ] Links open and show the strongest artifact first.
- [ ] The email does not ask the recipient to do a large amount of unpaid work.
- [ ] No generic flattery, desperation, inflated claims, or false familiarity.
