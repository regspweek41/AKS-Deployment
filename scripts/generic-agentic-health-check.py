import json
import os
import subprocess
import sys

APP_NAME = os.getenv("APP_NAME", "todo-rest-api")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "todo-rest-api")
NAMESPACE = os.getenv("NAMESPACE", "default")
HEALTH_THRESHOLD = int(os.getenv("HEALTH_THRESHOLD", "70"))

health_score = 100
findings = []

def run_cmd(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def reduce_health(points, reason):
    global health_score
    health_score -= points
    findings.append({
        "impact": points,
        "reason": reason
    })

# 1. Check deployment availability
code, out, err = run_cmd(
    f"kubectl get deployment {DEPLOYMENT_NAME} -n {NAMESPACE} -o json"
)

if code != 0:
    reduce_health(40, f"Deployment not found or inaccessible: {err}")
else:
    deployment = json.loads(out)
    desired = deployment["status"].get("replicas", 0)
    available = deployment["status"].get("availableReplicas", 0)

    if available < desired:
        reduce_health(30, f"Available replicas {available}/{desired}")

# 2. Check pod status
code, out, err = run_cmd(
    f"kubectl get pods -n {NAMESPACE} -l app={APP_NAME} -o json"
)

if code != 0:
    reduce_health(30, f"Unable to get pods: {err}")
else:
    pods = json.loads(out).get("items", [])

    if not pods:
        reduce_health(40, "No pods found for application")

    for pod in pods:
        pod_name = pod["metadata"]["name"]
        phase = pod["status"].get("phase", "Unknown")

        if phase != "Running":
            reduce_health(20, f"Pod {pod_name} is in {phase} state")

        for container in pod["status"].get("containerStatuses", []):
            restart_count = container.get("restartCount", 0)

            if restart_count > 0:
                reduce_health(10, f"Pod {pod_name} has {restart_count} restarts")

            waiting = container.get("state", {}).get("waiting")
            if waiting:
                reason = waiting.get("reason", "Unknown")
                reduce_health(30, f"Pod {pod_name} container waiting: {reason}")

# 3. Final decision
health_score = max(health_score, 0)

decision = "HEALTHY" if health_score >= HEALTH_THRESHOLD else "UNHEALTHY"

report = {
    "application": APP_NAME,
    "deployment": DEPLOYMENT_NAME,
    "namespace": NAMESPACE,
    "health_score": health_score,
    "health_threshold": HEALTH_THRESHOLD,
    "decision": decision,
    "findings": findings
}

with open("agentic-health-report.json", "w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))

if decision == "UNHEALTHY":
    print("❌ Agentic AI health check failed")
    sys.exit(1)

print("✅ Agentic AI health check passed")
sys.exit(0)