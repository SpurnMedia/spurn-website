# SPURN controlled Pages release — NO-GO until configured

This repository now contains a manual-only, disabled-by-default deployment workflow.

## Current source risk
SPURN previously used branch-based Pages deployment. The existing Site acceptance
workflow runs independently and cannot by itself prevent Pages from deploying a
failed main push. This repository does not have an observable GitHub ruleset.
Repository Pages settings are not writable by this integration.

## Production prerequisites (not completed)
1. Repository owner: Settings > Pages > Build and deployment > Source > GitHub Actions.
2. Protect main using a ruleset; require Site acceptance and restrict bypasses.
3. Configure github-pages environment restrictions where available.
4. Deploy the private OIDC + PostgreSQL + production Ed25519 signing service;
   ensure the signer verifies real, single-gate human approvals before signing.
5. Complete real content and media-rights QA, pilot, end-to-end release, stop,
   rollback and recovery exercises. Ratify canonical Model B policy changes.
6. Place the base64url raw 32-byte Ed25519 PUBLIC key in secret
   SPURN_RELEASE_PUBLIC_KEY_B64. NEVER place a private signing key here.
7. Only then configure SPURN_PAGES_RELEASE_ENABLED=true. It is absent today.

## Workflow contract
Manual workflow dispatch accepts: commit_sha, release_intent_b64, signature_b64.
The intent must be canonical UTF-8 JSON with exact fields:
schema, repository, commit_sha, release_type, issue_id,
frozen_manifest_sha256, human_approval_sha256, approval_schema,
production_authority, issued_at, expires_at, nonce.

The only allowed schema is spurn.production.release-intent.v1.
The only allowed approval schema is spurn.private.production-approval.v1.
Shadow and simulated decisions are rejected. Commit must equal GitHub main HEAD.
The intent expires within 15 minutes and must pass Ed25519 verification.
The repository stores only public metadata, never raw story drafts or approver PII.

## Scope limitation
The verifier can authenticate the *production signer*. It cannot independently
prove that the signer correctly checked a human's OIDC session. That private
attestation chain does not exist in production yet. All live publishing remains
disabled until those gates are satisfied.

PR success does NOT change GitHub Pages publishing source and is not evidence of
an end-to-end production release.
