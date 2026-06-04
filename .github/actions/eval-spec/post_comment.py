"""Post evaluation results as GitHub PR comment."""

import json
import sys


def main():
    data = json.load(sys.stdin)
    summary = data.get("summary", data)
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    errors = summary.get("errors", 0)
    rate = summary.get("pass_rate", 0) * 100
    latency = summary.get("avg_latency", 0)
    tokens = summary.get("total_tokens", 0)

    if rate >= 80:
        icon = "🟢"
    elif rate >= 50:
        icon = "🟡"
    else:
        icon = "🔴"
    print(f"## {icon} AgentSpec Evaluation Results")
    print()
    print("| Metric | Value |")
    print("|--------|-------|")
    print(f"| Pass rate | {passed}/{total} ({rate:.0f}%) |")
    print(f"| Passed | {passed} |")
    print(f"| Failed | {failed} |")
    print(f"| Errors | {errors} |")
    print(f"| Avg latency | {latency:.2f}s |")
    print(f"| Total tokens | {tokens} |")
    print()
    print("---")
    print("*Run by AgentSpec GitHub Action*")


if __name__ == "__main__":
    main()
