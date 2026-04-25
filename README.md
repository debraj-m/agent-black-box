# Agent Black Box

Flight recorder for AI coding agents.

It runs a command, captures timing, exit code, stdout/stderr, git status, and git diff into `.agent-black-box/runs/`.

## Usage

```bash
agent-black-box -- npm test
agent-black-box -- python -m pytest
```
