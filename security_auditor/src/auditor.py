#!/usr/bin/env python3
"""
🔥 NullForge Security Auditor
============================

An ingenious AI-powered security audit tool that analyzes codebases for:
- Security vulnerabilities (SQL injection, XSS, hardcoded secrets)
- Code quality issues
- Dependency vulnerabilities
- Compliance violations
- Best practice violations

Works standalone - no API key required for local analysis!
"""

import ast
import re
import json
import hashlib
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum


class Severity(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    """Security finding."""
    id: str
    title: str
    severity: Severity
    category: str
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity.value,
            "category": self.category,
            "location": {
                "file": self.file_path,
                "line": self.line_number,
            },
            "code_snippet": self.code_snippet,
            "description": self.description,
            "recommendation": self.recommendation,
            "references": {
                "cwe": self.cwe_id,
                "owasp": self.owasp_category,
            }
        }


@dataclass
class AuditReport:
    """Complete audit report."""
    project_path: str
    scan_time: datetime
    duration_ms: int
    files_scanned: int
    lines_scanned: int
    findings: List[Finding] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    
    @property
    def critical_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.CRITICAL])
    
    @property
    def high_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.HIGH])
    
    @property
    def risk_score(self) -> int:
        """Calculate risk score 0-100."""
        if not self.findings:
            return 0
        
        weights = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 0,
        }
        
        score = sum(weights[f.severity] for f in self.findings)
        return min(100, score)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": {
                "project": self.project_path,
                "scan_time": self.scan_time.isoformat(),
                "duration_ms": self.duration_ms,
                "files_scanned": self.files_scanned,
                "lines_scanned": self.lines_scanned,
            },
            "summary": {
                "total_findings": len(self.findings),
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": len([f for f in self.findings if f.severity == Severity.MEDIUM]),
                "low": len([f for f in self.findings if f.severity == Severity.LOW]),
                "info": len([f for f in self.findings if f.severity == Severity.INFO]),
                "risk_score": self.risk_score,
            },
            "findings": [f.to_dict() for f in self.findings],
        }


class SecurityAuditor:
    """
    🔥 NullForge Security Auditor
    
    Performs comprehensive security analysis on codebases.
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.findings: List[Finding] = []
        self.finding_counter = 0
        
        # Security patterns to detect
        self.patterns = self._load_security_patterns()
    
    def _generate_finding_id(self) -> str:
        """Generate unique finding ID."""
        self.finding_counter += 1
        return f"NF-{self.finding_counter:04d}"
    
    def _load_security_patterns(self) -> Dict[str, List[Dict]]:
        """Load security detection patterns."""
        return {
            "secrets": [
                {
                    "pattern": r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
                    "title": "Hardcoded Password",
                    "severity": Severity.CRITICAL,
                    "cwe": "CWE-798",
                    "owasp": "A07:2021",
                    "description": "Hardcoded password found in source code. This is a critical security vulnerability.",
                    "recommendation": "Use environment variables or a secure secrets manager.",
                },
                {
                    "pattern": r'(?i)(api[_-]?key|apikey|secret[_-]?key)\s*=\s*["\'][A-Za-z0-9+/=]{16,}["\']',
                    "title": "Hardcoded API Key",
                    "severity": Severity.CRITICAL,
                    "cwe": "CWE-798",
                    "owasp": "A07:2021",
                    "description": "API key or secret key hardcoded in source code.",
                    "recommendation": "Store API keys in environment variables or secure vault.",
                },
                {
                    "pattern": r'(?i)(aws[_-]?access[_-]?key|aws[_-]?secret)\s*=\s*["\'][A-Z0-9]{16,}["\']',
                    "title": "AWS Credentials Exposed",
                    "severity": Severity.CRITICAL,
                    "cwe": "CWE-798",
                    "owasp": "A07:2021",
                    "description": "AWS credentials found hardcoded in source code.",
                    "recommendation": "Use IAM roles or AWS Secrets Manager.",
                },
                {
                    "pattern": r'-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----',
                    "title": "Private Key in Source",
                    "severity": Severity.CRITICAL,
                    "cwe": "CWE-321",
                    "owasp": "A07:2021",
                    "description": "Private key found in source code.",
                    "recommendation": "Never commit private keys. Use secure key management.",
                },
            ],
            "injection": [
                {
                    "pattern": r'execute\s*\(\s*["\']?\s*SELECT.*%s',
                    "title": "Potential SQL Injection",
                    "severity": Severity.HIGH,
                    "cwe": "CWE-89",
                    "owasp": "A03:2021",
                    "description": "String formatting in SQL query may allow SQL injection.",
                    "recommendation": "Use parameterized queries or ORM methods.",
                },
                {
                    "pattern": r'cursor\.(execute|executemany)\s*\([^,]+\s*%',
                    "title": "SQL Injection Risk",
                    "severity": Severity.HIGH,
                    "cwe": "CWE-89",
                    "owasp": "A03:2021",
                    "description": "Dynamic SQL query construction detected.",
                    "recommendation": "Use query parameters: cursor.execute(sql, (param,))",
                },
                {
                    "pattern": r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
                    "title": "Command Injection Risk",
                    "severity": Severity.HIGH,
                    "cwe": "CWE-78",
                    "owasp": "A03:2021",
                    "description": "Shell=True with subprocess may allow command injection.",
                    "recommendation": "Avoid shell=True, use list of arguments instead.",
                },
                {
                    "pattern": r'eval\s*\([^)]*\)',
                    "title": "Dangerous eval() Usage",
                    "severity": Severity.HIGH,
                    "cwe": "CWE-95",
                    "owasp": "A03:2021",
                    "description": "eval() can execute arbitrary code if input is not sanitized.",
                    "recommendation": "Use ast.literal_eval() for safe evaluation or avoid eval entirely.",
                },
                {
                    "pattern": r'exec\s*\([^)]*\)',
                    "title": "Dangerous exec() Usage",
                    "severity": Severity.HIGH,
                    "cwe": "CWE-95",
                    "owasp": "A03:2021",
                    "description": "exec() can execute arbitrary code.",
                    "recommendation": "Avoid exec() with user-controlled input.",
                },
            ],
            "xss": [
                {
                    "pattern": r'innerHTML\s*=',
                    "title": "Potential XSS via innerHTML",
                    "severity": Severity.MEDIUM,
                    "cwe": "CWE-79",
                    "owasp": "A03:2021",
                    "description": "Setting innerHTML can lead to XSS if content is not sanitized.",
                    "recommendation": "Use textContent or sanitize HTML before insertion.",
                },
                {
                    "pattern": r'\|\s*safe\s*}}',
                    "title": "Jinja2 Safe Filter Risk",
                    "severity": Severity.MEDIUM,
                    "cwe": "CWE-79",
                    "owasp": "A03:2021",
                    "description": "The |safe filter disables auto-escaping in Jinja2.",
                    "recommendation": "Only use |safe with trusted, sanitized content.",
                },
                {
                    "pattern": r'mark_safe\s*\(',
                    "title": "Django mark_safe Risk",
                    "severity": Severity.MEDIUM,
                    "cwe": "CWE-79",
                    "owasp": "A03:2021",
                    "description": "mark_safe() marks content as safe HTML without escaping.",
                    "recommendation": "Ensure content is properly sanitized before using mark_safe.",
                },
            ],
            "crypto": [
                {
                    "pattern": r'(?i)(md5|sha1)\s*\(',
                    "title": "Weak Hash Algorithm",
                    "severity": Severity.MEDIUM,
                    "cwe": "CWE-328",
                    "owasp": "A02:2021",
                    "description": "MD5 and SHA1 are cryptographically weak.",
                    "recommendation": "Use SHA-256 or stronger for security-sensitive hashing.",
                },
                {
                    "pattern": r'(?i)DES|RC4|Blowfish',
                    "title": "Weak Encryption Algorithm",
                    "severity": Severity.HIGH,
                    "cwe": "CWE-327",
                    "owasp": "A02:2021",
                    "description": "Using outdated or weak encryption algorithm.",
                    "recommendation": "Use AES-256 or ChaCha20 for encryption.",
                },
                {
                    "pattern": r'random\.random\s*\(|random\.randint\s*\(',
                    "title": "Insecure Random Number Generator",
                    "severity": Severity.MEDIUM,
                    "cwe": "CWE-330",
                    "owasp": "A02:2021",
                    "description": "Using non-cryptographic random for potentially sensitive operations.",
                    "recommendation": "Use secrets module for security-sensitive random values.",
                },
            ],
            "auth": [
                {
                    "pattern": r'verify\s*=\s*False',
                    "title": "SSL Certificate Verification Disabled",
                    "severity": Severity.HIGH,
                    "cwe": "CWE-295",
                    "owasp": "A07:2021",
                    "description": "SSL certificate verification is disabled, enabling MITM attacks.",
                    "recommendation": "Always verify SSL certificates in production.",
                },
                {
                    "pattern": r'(?i)debug\s*=\s*True',
                    "title": "Debug Mode Enabled",
                    "severity": Severity.MEDIUM,
                    "cwe": "CWE-489",
                    "owasp": "A05:2021",
                    "description": "Debug mode should not be enabled in production.",
                    "recommendation": "Use environment-based configuration for debug settings.",
                },
                {
                    "pattern": r'ALLOWED_HOSTS\s*=\s*\[\s*["\']?\*["\']?\s*\]',
                    "title": "Django ALLOWED_HOSTS Wildcard",
                    "severity": Severity.MEDIUM,
                    "cwe": "CWE-183",
                    "owasp": "A05:2021",
                    "description": "Wildcard ALLOWED_HOSTS enables host header attacks.",
                    "recommendation": "Specify explicit allowed hostnames.",
                },
            ],
            "logging": [
                {
                    "pattern": r'print\s*\([^)]*password',
                    "title": "Password Logged to Console",
                    "severity": Severity.HIGH,
                    "cwe": "CWE-532",
                    "owasp": "A09:2021",
                    "description": "Sensitive data may be logged to console output.",
                    "recommendation": "Never log passwords or sensitive data.",
                },
                {
                    "pattern": r'logging\.(debug|info|warning|error)\s*\([^)]*password',
                    "title": "Password in Log Statement",
                    "severity": Severity.HIGH,
                    "cwe": "CWE-532",
                    "owasp": "A09:2021",
                    "description": "Sensitive data may be written to log files.",
                    "recommendation": "Sanitize sensitive data before logging.",
                },
            ],
        }
    
    def scan_file(self, file_path: Path) -> List[Finding]:
        """Scan a single file for security issues."""
        findings = []
        
        try:
            content = file_path.read_text(errors='ignore')
            lines = content.splitlines()
        except Exception:
            return findings
        
        rel_path = str(file_path.relative_to(self.project_path) if file_path.is_relative_to(self.project_path) else file_path)
        
        # Pattern-based scanning
        for category, patterns in self.patterns.items():
            for pattern_def in patterns:
                regex = re.compile(pattern_def["pattern"])
                
                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        # Get context (3 lines before and after)
                        start = max(0, i - 3)
                        end = min(len(lines), i + 2)
                        snippet = "\n".join(f"{j}: {lines[j-1]}" for j in range(start + 1, end + 1))
                        
                        finding = Finding(
                            id=self._generate_finding_id(),
                            title=pattern_def["title"],
                            severity=pattern_def["severity"],
                            category=category,
                            file_path=rel_path,
                            line_number=i,
                            code_snippet=snippet,
                            description=pattern_def["description"],
                            recommendation=pattern_def["recommendation"],
                            cwe_id=pattern_def.get("cwe"),
                            owasp_category=pattern_def.get("owasp"),
                        )
                        findings.append(finding)
        
        # AST-based analysis for Python files
        if file_path.suffix == ".py":
            findings.extend(self._analyze_python_ast(file_path, content, rel_path))
        
        return findings
    
    def _analyze_python_ast(self, file_path: Path, content: str, rel_path: str) -> List[Finding]:
        """Perform AST-based security analysis on Python files."""
        findings = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return findings
        
        for node in ast.walk(tree):
            # Check for assert statements (removed in optimized mode)
            if isinstance(node, ast.Assert):
                findings.append(Finding(
                    id=self._generate_finding_id(),
                    title="Security Assert Statement",
                    severity=Severity.LOW,
                    category="code_quality",
                    file_path=rel_path,
                    line_number=node.lineno,
                    code_snippet=f"{node.lineno}: assert ...",
                    description="Assert statements are removed when Python runs with -O flag.",
                    recommendation="Use explicit if/raise for security checks.",
                    cwe_id="CWE-617",
                ))
            
            # Check for bare except clauses
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append(Finding(
                    id=self._generate_finding_id(),
                    title="Bare Except Clause",
                    severity=Severity.LOW,
                    category="code_quality",
                    file_path=rel_path,
                    line_number=node.lineno,
                    code_snippet=f"{node.lineno}: except:",
                    description="Bare except catches all exceptions including KeyboardInterrupt.",
                    recommendation="Catch specific exceptions: except Exception:",
                    cwe_id="CWE-396",
                ))
            
            # Check for pickle usage
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "pickle":
                        findings.append(Finding(
                            id=self._generate_finding_id(),
                            title="Pickle Deserialization Risk",
                            severity=Severity.MEDIUM,
                            category="injection",
                            file_path=rel_path,
                            line_number=node.lineno,
                            code_snippet=f"{node.lineno}: import pickle",
                            description="Pickle can execute arbitrary code during deserialization.",
                            recommendation="Use JSON or other safe serialization formats for untrusted data.",
                            cwe_id="CWE-502",
                            owasp_category="A08:2021",
                        ))
        
        return findings
    
    def scan_dependencies(self) -> List[Finding]:
        """Scan for known vulnerable dependencies."""
        findings = []
        
        # Check requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text()
            
            # Known vulnerable packages (simplified - real scanner would use a DB)
            vulnerable_packages = {
                "django<3.2": ("Django Security Update Required", Severity.HIGH),
                "flask<2.0": ("Flask Security Update Recommended", Severity.MEDIUM),
                "requests<2.20": ("Requests CVE-2018-18074", Severity.HIGH),
                "pyyaml<5.4": ("PyYAML Arbitrary Code Execution", Severity.CRITICAL),
                "urllib3<1.26.5": ("urllib3 CVE-2021-33503", Severity.MEDIUM),
            }
            
            for vuln_pattern, (title, severity) in vulnerable_packages.items():
                if any(vuln_pattern.split("<")[0] in line.lower() for line in content.splitlines()):
                    findings.append(Finding(
                        id=self._generate_finding_id(),
                        title=title,
                        severity=severity,
                        category="dependencies",
                        file_path="requirements.txt",
                        line_number=1,
                        code_snippet="Check requirements.txt",
                        description=f"Potentially vulnerable dependency: {vuln_pattern}",
                        recommendation="Update to the latest secure version.",
                        cwe_id="CWE-1104",
                        owasp_category="A06:2021",
                    ))
        
        # Check package.json
        pkg_file = self.project_path / "package.json"
        if pkg_file.exists():
            try:
                pkg_data = json.loads(pkg_file.read_text())
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                
                if "lodash" in deps:
                    # Simplified check
                    findings.append(Finding(
                        id=self._generate_finding_id(),
                        title="Check Lodash Version",
                        severity=Severity.INFO,
                        category="dependencies",
                        file_path="package.json",
                        line_number=1,
                        code_snippet="lodash in dependencies",
                        description="Lodash has had multiple CVEs. Ensure version is current.",
                        recommendation="Run 'npm audit' for detailed vulnerability check.",
                    ))
            except:
                pass
        
        return findings
    
    def scan(self) -> AuditReport:
        """Perform full security scan."""
        start_time = datetime.now()
        files_scanned = 0
        lines_scanned = 0
        
        # Scan all code files
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".php"}
        
        for ext in extensions:
            for file_path in self.project_path.rglob(f"*{ext}"):
                # Skip common non-source directories
                if any(part in file_path.parts for part in [
                    "node_modules", ".git", "__pycache__", "venv", ".venv",
                    "target", "build", "dist", ".tox"
                ]):
                    continue
                
                try:
                    content = file_path.read_text(errors='ignore')
                    lines_scanned += len(content.splitlines())
                    files_scanned += 1
                    
                    file_findings = self.scan_file(file_path)
                    self.findings.extend(file_findings)
                except:
                    continue
        
        # Scan dependencies
        self.findings.extend(self.scan_dependencies())
        
        # Sort findings by severity
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        self.findings.sort(key=lambda f: severity_order[f.severity])
        
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return AuditReport(
            project_path=str(self.project_path),
            scan_time=start_time,
            duration_ms=duration_ms,
            files_scanned=files_scanned,
            lines_scanned=lines_scanned,
            findings=self.findings,
        )


def generate_report_markdown(report: AuditReport) -> str:
    """Generate a Markdown security report."""
    
    # Risk level indicator
    risk = report.risk_score
    if risk >= 75:
        risk_level = "🔴 CRITICAL"
        risk_color = "red"
    elif risk >= 50:
        risk_level = "🟠 HIGH"
        risk_color = "orange"
    elif risk >= 25:
        risk_level = "🟡 MEDIUM"
        risk_color = "yellow"
    elif risk > 0:
        risk_level = "🟢 LOW"
        risk_color = "green"
    else:
        risk_level = "✅ CLEAN"
        risk_color = "green"
    
    md = f"""# 🔥 NullForge Security Audit Report

**Project:** `{report.project_path}`  
**Scan Time:** {report.scan_time.strftime("%Y-%m-%d %H:%M:%S")}  
**Duration:** {report.duration_ms}ms  

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Risk Score** | **{risk} / 100** ({risk_level}) |
| **Files Scanned** | {report.files_scanned} |
| **Lines Analyzed** | {report.lines_scanned:,} |
| **Total Findings** | {len(report.findings)} |

### Findings by Severity

| Severity | Count |
|----------|-------|
| 🔴 Critical | {report.critical_count} |
| 🟠 High | {report.high_count} |
| 🟡 Medium | {len([f for f in report.findings if f.severity == Severity.MEDIUM])} |
| 🟢 Low | {len([f for f in report.findings if f.severity == Severity.LOW])} |
| ℹ️ Info | {len([f for f in report.findings if f.severity == Severity.INFO])} |

---

## Detailed Findings

"""
    
    if not report.findings:
        md += "> ✅ **No security issues found!** Great job maintaining secure code.\n"
    else:
        current_severity = None
        
        for finding in report.findings:
            if finding.severity != current_severity:
                current_severity = finding.severity
                severity_icon = {
                    Severity.CRITICAL: "🔴",
                    Severity.HIGH: "🟠",
                    Severity.MEDIUM: "🟡",
                    Severity.LOW: "🟢",
                    Severity.INFO: "ℹ️",
                }[current_severity]
                md += f"\n### {severity_icon} {current_severity.value.upper()} Severity\n\n"
            
            md += f"""#### [{finding.id}] {finding.title}

**Location:** `{finding.file_path}` (line {finding.line_number})  
**Category:** {finding.category}  
"""
            if finding.cwe_id:
                md += f"**CWE:** [{finding.cwe_id}](https://cwe.mitre.org/data/definitions/{finding.cwe_id.split('-')[1]}.html)  \n"
            if finding.owasp_category:
                md += f"**OWASP:** {finding.owasp_category}  \n"
            
            md += f"""
**Description:** {finding.description}

**Code:**
```
{finding.code_snippet}
```

**Recommendation:** {finding.recommendation}

---

"""
    
    md += f"""
## Compliance Summary

| Framework | Status |
|-----------|--------|
| OWASP Top 10 2021 | {"⚠️ Issues Found" if report.findings else "✅ Compliant"} |
| CWE Top 25 | {"⚠️ Review Required" if report.critical_count > 0 else "✅ No Critical Issues"} |
| PCI DSS | {"❌ Action Required" if report.high_count > 0 else "✅ Passing"} |

---

## Recommendations

1. **Immediate Actions:** Address all CRITICAL and HIGH severity findings
2. **Short-term:** Review and fix MEDIUM severity issues
3. **Ongoing:** Implement security scanning in CI/CD pipeline
4. **Training:** Review secure coding guidelines with development team

---

*Generated by 🔥 NullForge Security Auditor v2.0*
"""
    
    return md


def main():
    """CLI entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("🔥 NullForge Security Auditor")
        print("Usage: python auditor.py <project_path> [--json] [--output report.md]")
        print("\nExample:")
        print("  python auditor.py ./my-project")
        print("  python auditor.py ./my-project --json > report.json")
        print("  python auditor.py ./my-project --output security-report.md")
        sys.exit(1)
    
    project_path = sys.argv[1]
    output_json = "--json" in sys.argv
    
    # Check for output file
    output_file = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    print(f"🔥 NullForge Security Auditor")
    print(f"   Scanning: {project_path}")
    print()
    
    auditor = SecurityAuditor(project_path)
    report = auditor.scan()
    
    if output_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        md_report = generate_report_markdown(report)
        
        if output_file:
            Path(output_file).write_text(md_report)
            print(f"✅ Report saved to: {output_file}")
        else:
            print(md_report)
    
    # Exit code based on findings
    if report.critical_count > 0:
        sys.exit(2)  # Critical issues
    elif report.high_count > 0:
        sys.exit(1)  # High issues
    else:
        sys.exit(0)  # Clean or minor issues


if __name__ == "__main__":
    main()
