# Agent Black Box

**Flight recorder for AI coding agents.**

Agent Black Box records what happened when an AI agent, script, or risky command
touched your repository: command, exit code, duration, stdout, stderr, git
status, diff, and a Markdown summary.

It is built for the new workflow where humans ask agents to modify code and
then need a fast answer to one question:

> What exactly did it do?

## Why

AI coding agents are useful, but they can fail quietly:

- commands run but tests do not
- files change outside the expected area
- output contains secrets
- the final answer says “done” while the repo says otherwise

Agent Black Box gives every run an audit trail under `.agent-black-box/runs/`.

## Install

```bash
git clone https://github.com/debraj-m/agent-black-box.git
cd agent-black-box
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

Record a command:

```bash
agent-black-box run -- python -m unittest
```

Record with a label:

```bash
agent-black-box run --label fix-login -- npm test
```

List runs:

```bash
agent-black-box list
```

Show a run summary:

```bash
agent-black-box show 20260426-120000-fix-login
```

JSON output:

```bash
agent-black-box run --json -- python -m pytest
agent-black-box list --json
agent-black-box show RUN_ID --json
```

## What Gets Recorded

Each run writes:

```text
.agent-black-box/runs/<run-id>/
  manifest.json
  summary.md
  stdout.txt
  stderr.txt
  diff.patch
```

The manifest includes:

- command
- exit code
- duration
- git HEAD
- git status before and after
- files changed
- lines added and removed
- stdout/stderr byte counts

## Secret Redaction

By default, Agent Black Box redacts common secrets from `stdout.txt` and
`stderr.txt`, including OpenAI-style keys, GitHub tokens, and key/value secrets
such as `token=...`.

Disable this only when you are sure output is safe:

```bash
agent-black-box run --no-redact -- your-command
```

## Examples

Run an AI-generated test command:

```bash
agent-black-box run --label agent-test -- python -m unittest discover -s tests
```

Inspect what changed:

```bash
agent-black-box list
cat .agent-black-box/runs/<run-id>/diff.patch
cat .agent-black-box/runs/<run-id>/summary.md
```

## Local Checks

```bash
pip install -e .
python -m unittest discover -s tests
agent-black-box run -- python -c "print('hello')"
```

## Roadmap

- HTML report mode
- GitHub Action wrapper
- Policy checks for changed file paths
- Test result parsing
- MCP/server mode for agent integrations

## License

MIT. See [LICENSE](LICENSE).
