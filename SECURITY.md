# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.5.x   | Yes                |
| 0.3.x   | Security fixes only|
| < 0.3   | No                 |

## Reporting a Vulnerability

If you discover a security vulnerability in viznoir, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email **kimimgo@gmail.com** with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
3. You will receive an acknowledgment within **48 hours**.
4. A fix will be developed and released within **7 days** for critical issues.

## Security Measures

- **Path traversal prevention**: `VIZNOIR_DATA_DIR` restricts file access to a configured directory
- **Dependency auditing**: `pip-audit` runs weekly via CI and on every PR
- **Static analysis**: CodeQL scans on every push and weekly schedule
- **Dependency review**: License and vulnerability checks on all PRs
- **No arbitrary code execution**: Pipeline DSL compiles to VTK API calls only (`ProgrammableFilter` disabled by default, requires `VIZNOIR_ALLOW_PROGRAMMABLE=1`)
- **ffmpeg injection prevention**: `compose_assets` video export uses `--` separator to prevent output path injection
- **Asset path validation**: `compose_assets` validates all file paths against `VIZNOIR_DATA_DIR` and `VIZNOIR_OUTPUT_DIR` boundaries

## Scope

The following are in scope for security reports:

- Path traversal bypasses in `_validate_file_path`
- Arbitrary file read/write outside `VIZNOIR_DATA_DIR`
- Denial of service via crafted input files
- Dependency vulnerabilities in production dependencies

Out of scope:

- Issues in development-only dependencies
- Issues requiring physical access to the server
- Social engineering attacks
