# HeroAgent - Development Status

## Overview

HeroAgent is a lightweight Python coding agent that replaces Claude Code in CodeHero.
Supports multiple AI providers and is 100% compatible with the CodeHero daemon.

---

## Completed Features

### Core CLI
- [x] CLI interface compatible with Claude Code (`-p`, `--model`, `--provider`, `--dangerously-skip-permissions`)
- [x] Configuration loader (YAML + environment variables)
- [x] Stream JSON output for daemon compatibility
- [x] Multiple output formats (stream-json, text, print)

### Providers
- [x] **Anthropic** - Claude models (opus, sonnet, haiku aliases)
- [x] **Grok** - xAI models via OpenAI-compatible API + Vision support
- [x] **OpenAI** - GPT models
- [x] **Gemini** - Google models
- [x] **Ollama** - Local models

### Tools (9 total)
| Tool | Description | Status |
|------|-------------|--------|
| Bash | Execute shell commands | ✅ |
| Read | Read files AND images (vision) | ✅ |
| Write | Create/overwrite files | ✅ |
| Edit | Edit files (search/replace) | ✅ |
| Glob | Find files by pattern | ✅ |
| Grep | Search file contents | ✅ |
| WebFetch | Fetch and analyze web pages | ✅ |
| Screenshot | Take screenshots (Playwright) | ✅ |
| Vision | See and analyze images | ✅ (via Read tool) |

### Features
- [x] Vision support - Grok can see and analyze screenshots
- [x] HTML entity unescaping for web files (fix for Grok)
- [x] Completion check after tool execution (not before)
- [x] Screenshot tool with desktop/mobile/both viewports
- [x] Image reading with base64 conversion
- [x] System prompt with global context rules

### System Prompt Includes
- Execution rules (immediate action, no descriptions)
- Protected paths list
- Security rules (SQL injection, XSS, passwords)
- Code quality guidelines
- UI verification workflow (mandatory screenshots)
- UI quality checklist
- Playwright URL format and settings

---

## Pending Features

### High Priority
- [x] **Protected paths enforcement** in Write/Edit tools ✅ DONE
  - Created `tools/protected.py` with path checking logic
  - Integrated into Write and Edit tools
  - Protected: `/opt/codehero/`, `/etc/codehero/`, `/etc/nginx/`, `~/.claude`
  - Allowed: `/var/www/projects/`, `/opt/apps/`, `/tmp/`, `/home/claude/codehero/`

- [x] **Daemon-compatible output format** ✅ DONE
  - Stream JSON matches Claude Code's format exactly
  - Assistant messages include `message.content[]` array
  - Tool uses embedded in assistant messages
  - Compatible with daemon's `parse_claude_output()`

- [ ] **Daemon integration**
  - Modify claude-daemon.py to use CODEHERO_AGENT env var
  - Test with real tickets

### Medium Priority
- [ ] **Hooks/Permissions system**
  - Semi-autonomous mode support
  - Permission prompts for risky operations
  - Integration with existing semi_autonomous_hook.py

- [ ] **MCP Client**
  - JSON-RPC 2.0 client for CodeHero MCP server
  - Tool discovery and execution
  - Connect to codehero_* tools

### Low Priority
- [ ] **Additional tools**
  - Git tool (dedicated, not just Bash)
  - Database tool (MySQL queries)
  - Test runner tool

- [ ] **Provider improvements**
  - Vision support for OpenAI provider
  - Vision support for Anthropic provider
  - Better error handling for API failures

- [ ] **Testing**
  - Unit tests for tools
  - Integration tests with daemon
  - Provider-specific tests

---

## File Locations

| Component | Path |
|-----------|------|
| Source code | `/home/claude/codehero/heroagent/` |
| Production | `/opt/codehero/heroagent/` |
| Config | `/etc/codehero/heroagent.conf` |
| Symlink | `/usr/local/bin/heroagent` (to create) |

---

## Configuration

**Config file:** `/etc/codehero/heroagent.conf`

```yaml
# Model aliases (per provider)
model_aliases:
  anthropic:
    opus: claude-opus-4-5-20251101
    sonnet: claude-sonnet-4-5
    haiku: claude-haiku-4-5
  grok:
    opus: grok-4-0709
    sonnet: grok-4-1-fast-reasoning
    haiku: grok-3-mini
  openai:
    opus: gpt-5.1
    sonnet: gpt-5.1
    haiku: gpt-4o-mini
```

---

## Testing Commands

```bash
# Simple test
heroagent --provider grok --model grok-4-1-fast-reasoning -p "Create hello.py"

# With skip permissions
heroagent --provider grok --model sonnet --dangerously-skip-permissions -p "task"

# Verbose mode
heroagent --provider grok --model sonnet --verbose -p "task"
```

---

## Bugs Fixed

1. **HTML Escape Bug** - Grok was writing `&lt;` instead of `<`
   - Fixed: Added `html.unescape()` in write.py for web files

2. **Completion Check Timing** - Tools not executed before "TASK COMPLETED"
   - Fixed: Check completion AFTER tool execution, not before

3. **Vision Not Working** - Grok couldn't see screenshots
   - Fixed: Read tool returns base64, Grok provider sends as image_url

4. **Wrong Directory Creation** - Bash brace expansion not working
   - Fixed: Better system prompt instructions

---

## Next Steps (Recommended Order)

1. **Protected paths check** - Add to Write/Edit tools
2. **Test thoroughly** - Various UI tasks with Grok
3. **Daemon integration** - Connect to CodeHero daemon
4. **Hooks system** - Semi-autonomous mode
5. **MCP client** - Connect to CodeHero MCP tools

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-01-21 | Daemon-compatible output format, ready for integration |
| 1.1.0 | 2026-01-21 | Protected paths enforcement added |
| 1.0.0 | 2025-01-21 | Initial implementation with all core features |

---

## Daemon Integration (When Ready)

To switch from Claude Code to HeroAgent in the daemon, modify `claude-daemon.py`:

```python
# Line ~1361 - Change from:
cmd = ['/home/claude/.local/bin/claude', ...]

# To:
AGENT_PATH = os.environ.get('CODEHERO_AGENT', '/home/claude/.local/bin/claude')
cmd = [AGENT_PATH, ...]
```

Then set the environment variable:
```bash
export CODEHERO_AGENT=/opt/codehero/heroagent/heroagent.py
```

---

*Last updated: 2026-01-21*
