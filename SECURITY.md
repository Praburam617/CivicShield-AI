# Security Policy — CivicShield AI

## 1. Educational and Demonstration Scope

CivicShield AI is an engineering demonstration and academic research project showcasing AI-assisted public grievance management, secure software development practices, and full-stack Python application design. It is **not** an officially authorized government system or legal emergency dispatcher. In actual emergency situations, citizens should contact official law enforcement helplines (such as 112 or 100).

## 2. Supported Versions

Security patches and improvements are actively maintained on the primary development branch:

| Version | Supported | Notes |
| :--- | :--- | :--- |
| `2.0.x` (Current) | Yes | Role-Based Access Control, Sanitized Evidence Storage, Local NLP |
| `1.0.x` (Legacy) | No | Deprecated prototype architecture |

## 3. Reporting a Vulnerability

If you discover a potential security vulnerability within CivicShield AI, we welcome responsible disclosure:

1. **Direct Communication**: Open a private advisory on GitHub or email the developer at `praburam.official@gmail.com` with the subject line `[SECURITY] CivicShield AI Vulnerability Report`.
2. **Details to Include**:
   - Description of the issue (e.g. CSRF, injection, privilege escalation).
   - Step-by-step reproduction instructions or proof-of-concept.
   - Affected routes, parameters, or components.
   - Proposed remediation if available.
3. **Response Timeline**:
   - Initial acknowledgement: within 48 hours.
   - Assessment and triage: within 5 business days.
   - Remediation commit or patch: coordinated disclosure upon fix deployment.

Please refrain from publicly posting vulnerability details or exploiting findings against demonstration instances.

## 4. Built-in Security Defenses

CivicShield AI incorporates multiple defensive controls:

- **Authentication & Password Hashing**: Passwords stored using PBKDF2 with SHA-256 via Werkzeug security hashing. Plaintext credentials are never saved.
- **Cross-Site Request Forgery (CSRF)**: All form submissions and AJAX requests enforce cryptographic CSRF token validation via Flask-WTF.
- **Role-Based Access Control (RBAC)**: Strict server-side route decorators (`@admin_required`, `@officer_required`) prevent privilege escalation and enforce jurisdictional isolation between police officers.
- **Protected File Storage**: Evidence documents and photos are quarantined outside the public static directory. Downloads are validated using MIME magic-byte inspections and served through authorized streaming handlers.
- **CSV Formula Injection Mitigation**: Dynamic exports sanitize cells containing trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) with leading apostrophes to protect administrative spreadsheets.
- **Rate Limiting**: Critical authentication and reporting endpoints are gated using Flask-Limiter to discourage brute-force attempts.
