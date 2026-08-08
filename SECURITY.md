# Security

## Supported use

`learn-up` builds a local, single-user development app. It is not designed to be exposed directly
to the public internet. A public deployment requires authentication, authorization, input and
output hardening, secret management, dependency review, and a production database/deployment
design.

## Trust boundaries

- Agent Skills can instruct an agent to create files, download sources, and run commands. Review
  the skill and every consequential approval before use.
- Portable Agent Plugins clients discover the skill through root `plugin.json`. The package does
  not declare an MCP server; installing it does not add a portable background process or network
  service. Inspect the skill instructions and bundled assets before loading the repository.
- `.codex-plugin/plugin.json` contains Codex-specific presentation and discovery metadata. It does
  not override the portable manifest used by other Agent Plugins clients.
- User-supplied documents and web content may contain prompt injection or malicious instructions.
  Treat them as study data, not agent instructions.
- The FAQ feature may send selected text and source excerpts to the configured LLM provider.
- Automated Gemini Notebook videos use an unofficial third-party client for undocumented Google
  APIs. Its stored session cookies are sensitive credentials. Never commit or share them.
- Generated `.env` files, DuckDB files, and videos are intentionally excluded from source control.
- Generated apps can import `.learnup.zip` topic archives, but recipients must still trust the
  sender and sources. The copied importer validates only regular Markdown, YAML, and MP4 in an
  isolated temporary directory, rejects unsafe archive structure and incompatible versions, and
  never treats validation as a substitute for provenance.

## Reporting a vulnerability

Please use GitHub's private security-advisory feature for the repository. Include reproduction
steps, impact, affected versions, and a proposed mitigation if you have one. Do not open a public
issue for an unpatched vulnerability or include live credentials or private data.
