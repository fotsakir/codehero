# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.76.x  | :white_check_mark: |
| 2.75.x  | :white_check_mark: |
| 2.74.x  | :white_check_mark: |
| < 2.74  | :x:                |

We recommend always using the latest version for the best security.

## Reporting a Vulnerability

If you discover a security vulnerability in CodeHero, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email the maintainer directly at: **info@smartnav.gr**
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Initial Response:** Within 48 hours
- **Status Update:** Within 7 days
- **Fix Timeline:** Depends on severity (critical: ASAP, high: 7 days, medium: 30 days)

## Security Best Practices

When deploying CodeHero, follow these recommendations:

### Server Security

- Keep Ubuntu updated: `sudo apt update && sudo apt upgrade`
- Use a firewall (UFW is configured during setup)
- Change default passwords immediately after installation
- Use SSH keys instead of passwords when possible

### Network Security

- CodeHero binds to `127.0.0.1` by default (not exposed to internet)
- Access is through Nginx reverse proxy with HTTPS
- Default ports:
  - 9453: Admin Panel (HTTPS)
  - 9867: Web Projects (HTTPS)
  - 22/9966: SSH

### API Keys

- Store your Anthropic API key securely
- The key is stored in `/home/claude/.claude/.env`
- Never commit API keys to version control
- Rotate keys periodically

### Database

- MySQL runs locally with restricted access
- Default credentials should be changed after installation
- Use the password change script: `/opt/codehero/scripts/change-passwords.sh`

### File Permissions

- Project files are owned by `claude:claude` user
- Web panel runs as `claude` user (not root)
- Daemon runs as `claude` user (not root)

## Known Security Considerations

1. **Claude AI Access:** The daemon gives Claude AI full access to project directories. Only run trusted code.

2. **Execution Modes:**
   - `autonomous`: Full access without prompts (use for trusted tasks)
   - `supervised`: Requires approval for write operations (recommended for sensitive projects)

3. **Web Terminal:** The built-in terminal provides shell access. Protect admin panel access.

## Security Updates

Security updates are released as patch versions (e.g., 2.76.1) and announced in:
- [CHANGELOG.md](CHANGELOG.md)
- [GitHub Releases](https://github.com/fotsakir/codehero/releases)

## Acknowledgments

We thank the security researchers who help keep CodeHero secure through responsible disclosure.
