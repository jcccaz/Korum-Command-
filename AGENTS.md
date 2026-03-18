# KorumOS Agent Protocol

This repository uses a strict execution protocol for coding tasks.

## Scope Discipline

- Do one job at a time.
- If a request contains multiple implementation jobs, split them into separate tasks and complete only one unless the user explicitly authorizes bundling.
- Treat these as separate jobs, not one combined change:
  - wire dock button
  - render docked chart
  - persist artifact state
  - export report JSON

## Required Pre-Code Explanation

Before making code changes, state all of the following in plain English:

- Root cause
- Fix plan
- Affected files
- Risk of regression

## Required Acceptance Criteria

Before coding, define:

- What success looks like
- What file should change
- What should not change
- How the change will be tested

## Behavior-Diff Requirement

Do not evaluate work with vague checks like "the code looks correct."

Define the requested behavior as concrete before/after outcomes. Example:

- When I click `Dock Chart`, the chart must appear in `Artifact Dock`.
- It must persist in mission state.
- It must be available to export.

Prefer behavior statements tied to the user action, destination, persistence layer, and downstream output.

## Completion Gate

Do not mark a task complete unless all of the following are true:

1. The requested behavior works.
2. The connected feature still works.
3. The output appears in the intended destination.
4. The change is explained in plain English.
5. The likely regression risk is stated.

## Verification Rule

- Verification must happen before a task is marked done.
- If testing could not be run, say so explicitly and state what remains unverified.
- If persistence, export, or cross-surface behavior is part of the request, verify each surface explicitly instead of assuming continuity.
