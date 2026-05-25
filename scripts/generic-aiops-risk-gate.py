import json
import os
from pathlib import Path

RISK_THRESHOLD = int(os.getenv("RISK_THRESHOLD", "70"))

risk_score = 0
findings = []

def add_risk(points, reason):
    global risk_score
    risk_score += points
    findings.append({
        "points": points,
        "reason": reason
    })

# 1. Check Semgrep SAST report
semgrep_file = Path("semgrep-report.json")

if semgrep_file.exists():
    try:
        data = json.loads(semgrep_file.read_text())
        results = data.get("results", [])

        if len(results) > 0:
            add_risk(min(len(results) * 10, 30), f"Semgrep found {len(results)} SAST issues")
        else:
            findings.append({"points": 0, "reason": "No Semgrep issues found"})
    except Exception as e:
        add_risk(15, f"Unable to parse Semgrep report: {str(e)}")
else:
    add_risk(20, "Semgrep report missing")

# 2. Check OWASP Dependency Check report
dependency_file = Path("backend-java/target/dependency-check-report.json")

if dependency_file.exists():
    try:
        data = json.loads(dependency_file.read_text())
        dependencies = data.get("dependencies", [])

        critical_count = 0
        high_count = 0

        for dep in dependencies:
            for vuln in dep.get("vulnerabilities", []):
                severity = vuln.get("severity", "").upper()
                if severity == "CRITICAL":
                    critical_count += 1
                elif severity == "HIGH":
                    high_count += 1

        if critical_count > 0:
            add_risk(40, f"{critical_count} critical dependency vulnerabilities found")

        if high_count > 0:
            add_risk(20, f"{high_count} high dependency vulnerabilities found")

        if critical_count == 0 and high_count == 0:
            findings.append({"points": 0, "reason": "No critical/high dependency vulnerabilities found"})

    except Exception as e:
        add_risk(15, f"Unable to parse Dependency Check report: {str(e)}")
else:
    add_risk(20, "Dependency Check report missing")

# 3. Check SBOM
sbom_file = Path("sbom.json")

if sbom_file.exists():
    findings.append({"points": 0, "reason": "SBOM file exists"})
else:
    add_risk(15, "SBOM file missing")

# 4. Check Kubernetes manifests
manifest_dir = Path(os.getenv("K8S_MANIFEST_DIR", "k8s"))

if manifest_dir.exists():
    yaml_files = list(manifest_dir.glob("*.yaml")) + list(manifest_dir.glob("*.yml"))

    if not yaml_files:
        add_risk(10, "No Kubernetes YAML manifests found")

    for file in yaml_files:
        content = file.read_text()

        if "limits:" not in content:
            add_risk(10, f"Resource limits missing in {file}")

        if "readinessProbe:" not in content:
            add_risk(10, f"Readiness probe missing in {file}")

        if "livenessProbe:" not in content:
            add_risk(10, f"Liveness probe missing in {file}")

        if "runAsNonRoot" not in content:
            add_risk(10, f"Security context runAsNonRoot missing in {file}")
else:
    add_risk(20, "Kubernetes manifest directory missing")

# 5. Cap score at 100
risk_score = min(risk_score, 100)

decision = "BLOCK" if risk_score >= RISK_THRESHOLD else "ALLOW"

report = {
    "risk_score": risk_score,
    "risk_threshold": RISK_THRESHOLD,
    "decision": decision,
    "findings": findings
}

with open("risk-score.txt", "w") as f:
    f.write(str(risk_score))

with open("aiops-risk-report.json", "w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))

if decision == "BLOCK":
    print("Deployment risk is too high. Blocking deployment.")
else:
    print("Deployment risk is acceptable. Proceeding.")