# 🧠 AI Master OS

### Governed AI Runtime • Decision Intelligence • Real Provider Integration • Safe Execution

> **AI Master OS is a governed AI operating layer designed to turn AI reasoning into traceable, policy-controlled, auditable execution — without allowing intelligence, UI, automation, or external providers to bypass governance.**

---

## 🌐 What Is AI Master OS?

AI Master OS is an **AI operating layer / runtime architecture** for building AI systems that can reason, evaluate, govern, prepare, and execute actions in a controlled way.

It is not intended to be just:

- a chatbot
- a prompt framework
- an automation script
- a workflow builder
- an AI dashboard
- a single-agent application

Instead, AI Master OS is designed as a **governed runtime** connecting intelligence to execution through explicit contracts and security boundaries.

The system brings together:

🧠 **Decision Intelligence**  
🔎 **Research & Evidence**  
📊 **Evaluation**  
🛡️ **Governance**  
🔐 **Authentication & Authorization**  
🧾 **Execution Intent**  
🤝 **Human Approval**  
⚙️ **Governed Execution**  
🌐 **Real Providers**  
🧰 **Tool Registry**  
🧾 **Receipts / Persistence**  
📡 **Observability**  
📈 **Outcomes & Learning**

The central design principle is:

> **AI can recommend, reason, plan, evaluate, and prepare execution — but governance and policy remain authoritative.**

---

# 🎯 Project Mission

The mission of AI Master OS is to provide a reusable runtime where increasingly capable AI systems can operate without turning AI intelligence into unrestricted execution authority.

A governed request should be able to move through the system as:

```text
Request
  ↓
Identity
  ↓
Decision
  ↓
Evaluation
  ↓
Governance
  ↓
Execution Intent
  ↓
Authorization
  ↓
Approval when required
  ↓
Governed Execution
  ↓
Tool / Provider
  ↓
Outcome
  ↓
Persistence
  ↓
Audit / Observability
  ↓
Learning / Future Decisions
```

Every important transition should remain:

**Explicit → Traceable → Governed → Auditable → Recoverable**

---

# 🧭 Canonical Runtime Architecture

The canonical target path is:

```text
┌─────────────────────────────────────────────────────────────────┐
│                         USER / CLIENT                           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                           HTTP / API                            │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY ADMISSION                           │
│                                                               │
│ Authentication → Identity → Authorization / Resource Access   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  UNIFIED RUNTIME ENTRYPOINT                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     REAL UNIFIED RUNTIME                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                              S1                                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     UDI / DECISION INTELLIGENCE                 │
│                                                               │
│ Evidence → Context → Recommendation → Decision Plan           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         EVALUATION                              │
│                                                               │
│ Confidence • Evidence • Uncertainty • Decision Readiness     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         GOVERNANCE                              │
│                                                               │
│ Risk • Policy • Approval Requirement • Execution Posture      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EXECUTION INTENT                           │
│                                                               │
│ Deterministic bridge between decision and execution           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 AUTHORIZATION / HUMAN APPROVAL                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                GOVERNED EXECUTION ORCHESTRATOR                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    O45 EXECUTION SERVICE                        │
│                                                               │
│ Idempotency • Governance • Approval • Leases • Recovery       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          TOOL REGISTRY                           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   REGISTERED HANDLER / PROVIDER                 │
│                                                               │
│ Internal Tool • Model Provider • Search Provider • Service    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                           OUTCOME                               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                PERSISTENCE / AUDIT / OBSERVABILITY              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        RESPONSE / LEARNING                      │
└─────────────────────────────────────────────────────────────────┘
```

---

# 🧠 Core Architecture Philosophy

AI Master OS intentionally separates:

```text
Decision
   ↓
Governance
   ↓
Execution Intent
   ↓
Authorization
   ↓
Approval
   ↓
Execution
   ↓
Outcome
```

These are different responsibilities.

A model recommendation is not an execution authorization.

A UI button is not a governance authority.

An execution intent is not proof that execution is approved.

A provider integration is not allowed to bypass the runtime.

---

# 🧠 Unified Decision Intelligence (UDI)

UDI is responsible for turning evidence, context, and decision inputs into a structured decision.

UDI can produce:

- recommendation
- decision basis
- selected route
- provider information
- confidence / uncertainty signals
- governance metadata
- structured decision context

UDI is **not the final execution authority**.

The system intentionally preserves the following principle:

> **Intelligence informs governance. Intelligence does not replace governance.**

---

# 📊 Evaluation Layer

The evaluation stage exists to determine whether a decision is sufficiently supported for downstream handling.

Relevant concepts include:

- evidence readiness
- confidence
- uncertainty
- decision readiness
- provenance
- reliability
- expected outcome

Evaluation does not grant execution authority by itself.

---

# 🛡️ Governance

Governance is a first-class policy boundary.

The system maintains explicit action classes such as:

```text
read_only_inspection
generate_internal_draft
write_memory
schedule_internal_workflow

publish_public_content
send_external_message
spend_ad_budget
change_price
payment_or_refund
delete_or_modify_critical_data
activate_integration
```

Unknown actions should fail closed.

Governance may classify an action as:

```text
AUTO_ALLOW
REVIEW
BLOCK
```

The distinction is fundamental:

```text
AUTO_ALLOW
    ↓
Execution may proceed subject to downstream execution controls

REVIEW
    ↓
Approval path required

BLOCK
    ↓
Execution prohibited
```

Governance remains authoritative.

The runtime must not silently reinterpret a blocked or review-required action as executable.

---

# 🔐 Governance Authority Invariant

The canonical invariant is:

```text
POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE
```

This invariant should remain valid across:

- Decision Intelligence
- Execution Intent
- O45
- Tool Execution
- Provider Integration
- UI / HTTP layers

No downstream component should promote itself into the policy authority.

---

# 🧾 Execution Intent

Execution Intent is the deterministic bridge between a decision and an executable request.

An intent contains information such as:

```text
intent_id
decision_plan_id
project_id
run_id
requested_by
action
provider
tool_name
payload
execution_request
governance_authority
```

The intent allows the system to bind:

```text
WHO
WHAT
WHY
WHERE
WITH WHICH TOOL
FOR WHICH RUN
UNDER WHICH GOVERNANCE CONTEXT
```

---

# ⚠️ Action vs Tool Name

A critical architectural invariant is:

```text
action != tool_name
```

### `action`

Represents the business / policy / risk classification.

Examples:

```text
read_only_inspection
publish_public_content
send_external_message
change_price
payment_or_refund
```

### `tool_name`

Represents the technical execution target.

Examples:

```text
internal.echo
decision-intelligence
real-search
```

This separation allows:

```text
Business intent
       ≠
Technical execution implementation
```

and prevents technical tool identifiers from silently becoming governance policy.

---

# 🤝 Human Approval

Human approval is a deliberate governance boundary.

A consequential action may move through:

```text
Execution Intent
      ↓
Governance
      ↓
AWAITING_APPROVAL
      ↓
Human Decision
      ↓
Approval Validation
      ↓
READY
      ↓
Execution
```

The system must never treat:

```text
REVIEW
```

as equivalent to:

```text
APPROVED
```

Approval must remain:

- explicit
- attributable
- persisted
- bound to the intended action
- bound to the relevant run
- validated before execution

Self-approval restrictions and approval authority checks are part of the security model.

---

# ⚙️ O45 Governed Execution

O45 is the canonical governed execution layer.

Its responsibilities include:

### 🔗 Request Binding

The execution request is bound to:

```text
project
run
action
tool
payload
request hash
idempotency key
decision plan
intent
```

### ♻️ Idempotency

The same logical execution request must not accidentally produce multiple executions.

### 👤 Approval Validation

Approval identity and approval state must be validated before consequential execution.

### 🔐 Authorization

Execution requires the relevant runtime capability.

### ⏳ Leases

Execution workers use bounded execution leases.

### 🧯 Recovery

Failed or interrupted executions can move into controlled recovery states.

### 🧾 Execution Receipts

Execution requests and outcomes are persisted for later inspection and audit.

### 📡 Observability

Important execution transitions are observable.

---

# 🚫 Submission Is Not Execution

One of the most important project rules is:

> **Submitting an execution intent does not automatically mean the underlying action has executed.**

Conceptually:

```text
submit_intent()
      ↓
governed submission
      ↓
READY / WAITING_HUMAN_APPROVAL / BLOCKED
      ↓
explicit execution drive
      ↓
tool handler
```

This distinction prevents automation from silently becoming execution authority.

---

# 🌐 Real Provider Integration

AI Master OS is being extended from simulated/internal execution toward real provider integration.

The architecture is:

```text
AI Decision
    ↓
Execution Intent
    ↓
Governance
    ↓
O45
    ↓
Tool Registry
    ↓
Provider Adapter
    ↓
Real Provider
    ↓
Provider Result
```

Provider integrations should never bypass:

```text
Identity
Authorization
Governance
Intent
Execution Service
Audit
```

Real providers may include:

- model providers
- search providers
- external APIs
- internal service adapters
- future business integrations

---

# 🔌 Provider Configuration

Provider configuration is environment-driven.

Examples of configuration classes include:

```text
AI_OS_MODEL_BASE_URL
AI_OS_MODEL_API_KEY
AI_OS_MODEL_NAME
AI_OS_SEARCH_BASE_URL
AI_OS_SEARCH_API_KEY
AI_OS_REQUEST_TIMEOUT_S
```

Actual secrets must never be committed to Git.

Do not place real credentials in:

- source code
- README files
- tests
- logs
- screenshots
- commits
- pull requests
- generated artifacts

---

# 🔐 Security Architecture

Security is treated as a system property, not a single middleware layer.

The security model includes:

```text
Authentication
      ↓
Identity
      ↓
RBAC / Scope Authorization
      ↓
Governance
      ↓
Approval
      ↓
Execution Authorization
      ↓
Tool / Provider Execution
```

---

# 🔒 Authentication

The canonical production path uses configured authentication and server-side identities.

The project supports signed bearer credentials through the identity system.

Production authentication should fail closed when required configuration is missing.

The system must not silently create an authenticated principal when an authenticator is unavailable.

---

# 🏠 Local Development Security

Local development may intentionally use a bypass to keep the development and test harness usable.

However:

```text
Local bypass ≠ Production authentication
```

The bypass must be explicitly enabled.

The intended pattern is:

```text
Authenticator()
        ↓
UNAUTHENTICATED

Authenticator(allow_local_bypass=True)
        ↓
BYPASS_FOR_LOCAL
```

This prevents an accidentally missing verifier from silently becoming an authenticated local principal.

---

# 👤 Identity Propagation

Requester identity must remain traceable across runtime boundaries.

Important fields include:

```text
principal
requested_by
principal_id
run_id
project_id
decision_plan_id
intent_id
```

The system should preserve identity rather than replacing it with anonymous or synthetic actors without an explicit reason.

---

# 🧾 Run Correlation

`run_id` is a primary cross-system correlation identifier.

It should allow the system to connect:

```text
HTTP Request
      ↓
Decision
      ↓
Execution Intent
      ↓
O45 Receipt
      ↓
Approval
      ↓
Execution
      ↓
Outcome
      ↓
Audit
```

This allows an operator or future diagnostic system to reconstruct what happened.

---

# 🧰 Tool Registry

Execution targets are resolved through a governed tool registry.

A tool should have:

```text
tool name
handler
version
execution contract
```

Tool registration provides an explicit boundary between:

```text
AI decision
```

and:

```text
actual executable capability
```

Unknown tools should not be treated as executable.

---

# 📦 Execution States

Representative states include:

```text
READY
AWAITING_APPROVAL
WAITING_HUMAN_APPROVAL
BLOCKED
SUBMITTED
RUNNING
SUCCEEDED
FAILED_RETRYABLE
FAILED_TERMINAL
RECOVERY_REQUIRED
CANCELLED
```

These states represent different lifecycle phases and must not be collapsed casually.

---

# 🧾 Persistence & Audit

AI Master OS is designed around persistent execution evidence.

Relevant persistent concepts include:

```text
Decision
Execution Intent
Approval
Execution Receipt
Execution Binding
Outcome
Audit Event
Observability Record
```

Persistence should allow later investigation of:

```text
What was requested?
Who requested it?
What did the AI decide?
What did governance decide?
Was approval required?
Was approval granted?
What tool executed?
What was the result?
What failed?
What was recovered?
```

---

# 📡 Observability

The system should expose structured evidence of key transitions.

Important observability concepts include:

```text
decision recorded
intent created
intent submitted
governance evaluated
approval requested
approval decided
execution started
execution finished
outcome recorded
recovery triggered
```

Observability is not just for debugging.

It is part of the system's accountability model.

---

# 📈 Outcomes & Learning

The runtime separates:

```text
Decision
```

from:

```text
Outcome
```

An AI decision can be reasonable while an execution can still fail.

Therefore:

```text
Expected decision
      ≠
Actual outcome
```

The system can use structured outcomes and evidence as future learning inputs without allowing learning to rewrite governance authority.

---

# 🔁 Closed-Loop Direction

The long-term architecture supports a governed closed loop:

```text
Research
   ↓
Evidence
   ↓
Decision
   ↓
Governance
   ↓
Intent
   ↓
Approval / Authorization
   ↓
Execution
   ↓
Outcome
   ↓
Learning Signal
   ↓
Persistence
   ↓
Re-entry
```

However:

> **Closed-loop learning must never become an excuse for uncontrolled autonomous execution.**

---

# 🤖 Multi-AI Collaboration Layer

AI Master OS is intentionally developed using multiple AI roles.

The collaboration model is designed so that no single model becomes the unquestioned authority over architecture or production behavior.

---

## 🏛️ Architect / Acceptance Gate

Responsible for:

- architecture
- invariants
- acceptance criteria
- scope control
- determining whether evidence actually proves a claim

---

## 🛠️ Claude

Primary implementation engineer.

Typical responsibilities:

- inspect repository
- implement focused patches
- preserve existing contracts
- add tests
- explain implementation impact

---

## 🔍 Gemini / Google AI Studio

Independent / adversarial engineering reviewer.

Typical responsibilities:

- challenge assumptions
- propose alternative designs
- inspect contracts
- identify hidden coupling
- look for security gaps
- review architecture independently

---

## 🧪 Copilot

Git-native implementation and review assistant.

Typical responsibilities:

- repository inspection
- code review
- Git-aware analysis
- implementation suggestions
- change-set review

---

## 👤 Human Operator

The human operator remains responsible for actual runtime verification.

Responsibilities include:

- executing commands
- validating Windows runtime behavior
- checking actual environment state
- deciding when to approve operational changes
- confirming that a claimed result actually occurred

---

# 🧠 Collaboration Principle

The project uses a multi-agent model:

```text
Architecture
      ↓
AI Implementation
      ↓
Independent AI Review
      ↓
Code Review
      ↓
Human Runtime Verification
      ↓
Acceptance
```

No model should be treated as the sole source of truth.

The repository, tests, runtime evidence, and architecture must agree.

---

# 🧪 Verification Philosophy

AI Master OS uses multiple layers of verification.

## 1. Focused Verification

Tests the exact change being introduced.

Example:

```text
Auth Hardening
5/5 PASS
```

## 2. Regression Verification

Checks existing security and runtime contracts.

Example:

```text
O38 Security
8/8 PASS
```

## 3. Compilation Verification

Source must compile successfully.

## 4. Integration Verification

Relevant boundaries must continue to work together.

## 5. Runtime Verification

Actual Windows execution must be tested when applicable.

## 6. Acceptance

A patch is not considered complete merely because:

```text
the code looks correct
```

or:

```text
the model says it works
```

Acceptance requires evidence.

---

# ✅ Definition of Done

A meaningful change should normally satisfy:

```text
[ ] Architecture inspected
[ ] Existing callers inspected
[ ] Existing consumers inspected
[ ] Scope kept narrow
[ ] Focused tests added
[ ] Focused tests pass
[ ] Relevant regression tests pass
[ ] Compilation passes
[ ] Diff reviewed
[ ] Secrets excluded
[ ] Working tree clean
[ ] Runtime verification performed where required
[ ] Claims match evidence
```

---

# 🚨 AI Agent Rules

Any AI coding agent working in this repository must follow these rules.

### ❌ Do not:

- bypass authentication
- bypass authorization
- bypass governance
- bypass approval
- invent execution capability
- silently enable external execution
- make consequential execution automatic
- weaken security to make tests pass
- delete safety checks without replacing their contract
- commit secrets
- print credentials
- ask users to paste production API keys
- fabricate PASS / VERIFIED / PROVEN results
- claim runtime verification without runtime evidence
- perform unrelated refactors during focused patches

### ✅ Do:

- inspect first
- trace callers
- trace consumers
- preserve architecture
- make narrow changes
- add focused tests
- run regression
- review the diff
- verify actual runtime behavior
- report uncertainty honestly

The default engineering sequence is:

> **Inspect → Understand → Patch → Test → Review → Verify**

---

# 🏗️ Repository Structure

The repository contains multiple architectural layers.

```text
AI Master OS/
│
├── src/
│   │
│   ├── core/
│   │   │
│   │   ├── src/
│   │   │   ├── auth.py
│   │   │   ├── identity.py
│   │   │   ├── rbac.py
│   │   │   ├── governance_intelligence.py
│   │   │   ├── execution_intent_planner.py
│   │   │   ├── governed_execution_orchestrator.py
│   │   │   ├── o45_execution_service.py
│   │   │   ├── tool registry / handlers
│   │   │   ├── provider integrations
│   │   │   ├── persistence
│   │   │   ├── observability
│   │   │   └── supporting runtime components
│   │   │
│   │   └── tests/
│   │
│   └── unified_runtime/
│       ├── entrypoint
│       ├── integrated runtime
│       ├── HTTP integration
│       ├── security boundary
│       └── runtime adapters
│
├── tests/
│   ├── patch-focused tests
│   ├── integration tests
│   └── cross-layer verification
│
├── scripts/
│
├── docs/
│
└── .github/
    ├── instructions/
    ├── collaboration guidance
    └── pull request templates
```

The exact file layout may evolve, but the architectural responsibilities should remain separated.

---

# 🔄 Preferred Development Workflow

The preferred workflow is:

```text
1. Inspect the existing implementation
        ↓
2. Identify the actual owner of the behavior
        ↓
3. Trace callers and consumers
        ↓
4. Define the smallest valid change
        ↓
5. Create a focused patch
        ↓
6. Add focused tests
        ↓
7. Run targeted regression
        ↓
8. Inspect the actual diff
        ↓
9. Commit a coherent change
        ↓
10. Push a dedicated branch
        ↓
11. Review through GitHub / AI reviewers
        ↓
12. Merge only when evidence supports the change
```

Unrelated changes should not be bundled into focused patches.

---

# 🧩 Important Concepts

| Concept | Meaning |
|---|---|
| **AI Master OS** | Governed AI runtime / operating layer |
| **UDI** | Unified Decision Intelligence |
| **Decision Plan** | Structured decision produced by decision intelligence |
| **Governance** | Policy/risk authority controlling execution posture |
| **Execution Intent** | Deterministic bridge between decision and execution |
| **Action** | Business/risk classification |
| **Tool Name** | Technical execution target |
| **O45** | Governed execution service |
| **Approval** | Explicit human authorization when required |
| **Run ID** | Cross-system execution correlation identity |
| **Provider** | External or internal execution integration |
| **Receipt** | Durable record of execution request/state |
| **Outcome** | Result after execution |
| **Observability** | Structured evidence of system transitions |

---

# 📦 Current Project Direction — 21.1

The current development line is focused on:

## 🌐 Real Provider Integration

The project is moving from a primarily simulated/test-oriented execution environment toward controlled real-provider integration.

The current architecture preserves the existing governance boundary while introducing:

- real provider adapters
- governed provider tool handlers
- explicit execution entry points
- provider configuration inspection
- authentication hardening
- real execution preparation
- execution/outcome observability

Real provider execution remains dependent on valid environment configuration.

---

# 🔐 Current Security Hardening

Recent security hardening established an important rule:

```text
Default Authenticator
        ↓
FAIL CLOSED
```

while development can explicitly request:

```text
allow_local_bypass=True
```

This preserves local development ergonomics without making a missing verifier behave like an authenticated production identity.

---

# 🧭 Long-Term Vision

The long-term goal is a governed AI operating layer that can coordinate increasingly capable AI systems while preserving human control and explicit policy boundaries.

The system should be able to support:

🧠 advanced AI reasoning  
🔎 research and evidence gathering  
📊 evaluation  
🛡️ deterministic governance  
🔐 strong identity and authorization  
🤝 human approval  
⚙️ controlled execution  
🌐 real external providers  
🧾 durable auditability  
📈 outcome-based learning  

without weakening its core safeguards.

---

# 🌟 Core Project Principle

## Build AI that can act — without giving AI unchecked authority.

The objective is not to make AI powerless.

The objective is to make AI:

**capable enough to act,**

while remaining:

**governed enough to trust.**

---

# 🏁 Final Architectural Invariants

The following principles define the intended behavior of AI Master OS:

```text
🧠 Intelligence informs.
🛡️ Governance decides execution posture.
🔐 Security controls access.
👤 Humans approve consequential actions when required.
🧾 Execution Intent binds decisions to executable requests.
⚙️ O45 governs execution.
🧰 Tools provide explicit capabilities.
🌐 Providers remain behind governed boundaries.
📡 Observability records important transitions.
🧾 Persistence preserves evidence.
📈 Outcomes inform learning.
🚫 No layer bypasses governance.
🚫 No implicit consequential execution.
🚫 No secrets in source control.
🚫 No false verification claims.
```

> **Capability should scale. Governance should remain intact.**
