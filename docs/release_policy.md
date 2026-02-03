# Release & Tagging Policy
 
Guidelines for creating demo releases in IoT Hub Bravo.
 
## Versioning Scheme
 
We use [Semantic Versioning](https://semver.org/):
 
```
v<MAJOR>.<MINOR>.<PATCH>
```
 
| Part | When to bump |
|------|-------------|
| **MAJOR** | Breaking changes to API or data model |
| **MINOR** | New features, backward-compatible |
| **PATCH** | Bug fixes, documentation, minor improvements |
 
### Examples
 
- `v0.1.0` — first demo release (MVP)
- `v0.2.0` — new feature added
- `v0.2.1` — bug fix on existing feature
 
During internship, versions stay in `v0.x.x` range.
 
## How to Create a Release
 
### Step 1: Ensure `main` is Ready
 
- All PRs for the release are merged
- CI passes on `main`
- No open blocker issues
 
### Step 2: Create a Git Tag
 
```bash
git checkout main
git pull origin main
git tag -a v0.1.0 -m "Release v0.1.0: MVP with device admin and telemetry"
git push origin v0.1.0
```
 
### Step 3: Create GitHub Release
 
**Via GitHub UI:**
 
1. Go to **Releases > Draft a new release**
2. Choose the tag (`v0.1.0`)
3. Title: `v0.1.0 — MVP Release`
4. Write release notes (see template below)
5. Attach artifacts if applicable
6. Click **Publish release**
 
**Via GitHub CLI:**
 
```bash
gh release create v0.1.0 \
  --title "v0.1.0 — MVP Release" \
  --notes-file RELEASE_NOTES.md
```
 
### Step 4: Attach Artifacts (Optional)
 
Attach relevant files to the release:
 
- `openapi.json` or `api.yaml` — API specification
- Demo recordings (`.gif`, `.mp4`)
- Exported Postman collection
 
```bash
gh release upload v0.1.0 docs/api.yaml docs/postman_collection.json
```
 
## Release Notes Template
 
```markdown
## What's New
 
- Feature A: short description
- Feature B: short description
 
## Bug Fixes
 
- Fix X: short description
 
## Breaking Changes
 
- None (or list changes)
 
## Contributors
 
- @username1
- @username2
 
**Full Changelog:** https://github.com/Project-Stage-Academy/IoT-Hub-bravo/compare/v0.0.0...v0.1.0
```
 
## Release Cadence
 
- **Demo releases** — at the end of each sprint or milestone
- **Hotfix releases** — as needed for critical bugs
- No fixed schedule; releases are milestone-driven
 