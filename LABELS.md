# GitHub Issue and PR Labels

This document describes the standard labels used in this repository.

## Issue Type Labels

| Label | Color | Description |
|-------|-------|-------------|
| `bug` | 🔴 | Something isn't working |
| `enhancement` | 🩵 | New feature or request |
| `user story` | ⚪ | User story from user perspective |
| `good first issue` | 🟣 | Good for newcomers |
| `help wanted` | 🟢 | Extra attention is needed |
| `question` | 🟪 | Further information is requested |
| `documentation` | 🔵 | Improvements or additions to documentation |

## Status Labels

| Label | Color | Description |
|-------|-------|-------------|
| `carry-over` | 🩵 | Carried over from previous sprint |

## Resolution Labels

| Label | Color | Description |
|-------|-------|-------------|
| `duplicate` | ⚪ | This issue or pull request already exists |
| `invalid` | 🟡 | This doesn't seem right |
| `wontfix` | ⚪ | This will not be worked on |

## Creating New Labels

To add a new label, go to **Issues > Labels > New label** in GitHub UI,
or use the GitHub CLI:

```bash
gh label create "<name>" --color "<hex>" --description "<description>"
