# Claude research agent — Mexico City Field Guide

This repository contains a historical learning and travel application. Claude is a **research producer**, not the canonical database owner or app publisher.

## Before each research run
1. Read `research/handoff/manifest.json` from the **remote** `research-persistence` branch and note its `research_commit_sha`.
2. Inspect existing staged research and avoid duplicate findings. Keep a checkpoint identifying the last verified remote commit.
3. Work in a dedicated branch named `research/claude-<topic>-<date>`, created from the latest remote `research-persistence`. Never write directly to `main` or overwrite canonical V97.

## Deliverable
Produce source-grounded, page-specific findings with stable IDs, provenance, evidence and uncertainty flags; JSON batch plus `findings.jsonl`, `sources.csv`, validator report, checkpoint. Distinguish examined primary sources from bibliographic leads. Mark all new findings as staged, pending independent review. Favor historical chronology, social and political change, economic life, power and ordinary people. Archaeological methods and technical disputes should support historical explanations, not dominate them.

## Push and PR
- Confirm the authenticated GitHub account has **Contents: Read and write** access to `lizperry81/mexico-city-field-guide` and permission to create pull requests.
- Verify `git remote -v` and remote branch before making changes.
- Commit only the new research files. Check `git diff --stat origin/research-persistence...HEAD` and `git log origin/research-persistence..HEAD --oneline`; a local branch lacking a corresponding remote ref can make ahead counts misleading.
- Push the dedicated branch and open a **draft** pull request targeting `research-persistence`.
- After push, verify remote branch and PR URL. Report SHA, PR, new finding/source counts, pending checks. Do not claim success based on a local commit.
- If push returns **403**, STOP. This is an authorization issue. Do not repeat pushes or attempt to bypass permissions. Keep the commit and export a downloadable `.patch` plus JSON/JSONL/CSV; report the precise account/repo permission blocker. The user can authorize access, or ChatGPT's GitHub connection can transfer the patch.

## Editorial separation
Discover is an illustrated, chronological, historically sophisticated narrative; Explore is a situated on-site guide. New research does not automatically rewrite approved Discover chapters. Read `editorial/DISCOVER_APPROVED_BASELINE_2026-11-13.md`. Proposed changes need sources and human editorial approval.

## Security
Never print, store in repo, or ask the user to paste a GitHub token into chat or source code. Use the hosting service's authorized GitHub connector or credential integration.
