import os
import json
import requests
import re
import time

# Environment Variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
RUN_ID = os.getenv("RUN_ID")
LOKI_ENDPOINT = os.getenv("LOKI_ENDPOINT")
LABELS = os.getenv("LABELS", "job=github-actions")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 5))  # Defaults to 5 retries if not setup in the action
RETRY_INTERVAL_SECONDS = int(os.getenv("RETRY_INTERVAL_SECONDS", 10))  # Defaults to 10 seconds if not setup in the action

HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def sanitize_labels(labels):
    """Sanitize labels to comply with Loki's label naming rules."""
    sanitized = {}
    for k, v in (item.split("=", 1) for item in labels.split(",") if "=" in item):
        # Replace invalid characters while preserving valid ones (ASCII letters, digits, _, :)
        key = re.sub(r"[^a-zA-Z0-9_:]", "_", k).lstrip("0123456789")
        if not key or not re.match(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$", key):
            raise ValueError(f"Invalid label key after sanitization: '{k}'")
        sanitized[key] = v
    return sanitized

def get_jobs(run_id):
    """Fetch all jobs metadata for the current workflow run."""
    print(f"Fetching job metadata for workflow run ID: {run_id}")
    jobs_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs/{run_id}/jobs"
    response = requests.get(jobs_url, headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch jobs: {response.text}")
    return response.json().get("jobs", [])

def fetch_job_logs(job_id):
    """Fetch logs for a specific job."""
    logs_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/jobs/{job_id}/logs"
    response = requests.get(logs_url, headers=HEADERS)
    if response.status_code == 200:
        return response.text.splitlines()
    elif response.status_code == 403:
        print(f"Logs not ready yet for job ID: {job_id}")
        return []
    else:
        print(f"Failed to fetch logs for job {job_id}: {response.status_code}")
        return []

def push_to_loki(logs, labels, job_name=None, job_id=None):
    """Push logs to Loki."""
    # Add job name and job ID as additional labels if provided
    if job_name:
        labels += f",job_name={job_name}"
    if job_id:
        labels += f",job_id={job_id}"

    # Sanitize labels before sending to Loki
    sanitized_labels = sanitize_labels(labels)

    payload = {
        "streams": [
            {
                "stream": sanitized_labels,
                "values": [[str(int(time.time() * 1e9)), log] for log in logs if log],  # Include timestamps
            }
        ]
    }
    print(f"Pushing logs to Loki: {LOKI_ENDPOINT}")
    response = requests.post(f"{LOKI_ENDPOINT}/loki/api/v1/push", json=payload)
    if response.status_code == 204:
        print("Logs successfully sent to Loki.")
    else:
        print(f"Failed to send logs to Loki: {response.status_code}, {response.text}")

def main():
    jobs = get_jobs(RUN_ID)
    for job in jobs:
        job_id = job.get("id")
        status = job.get("status")
        name = job.get("name")
        print(f"Processing job ID: {job_id} ({name}), Status: {status}")

        if status != "completed":
            print(f"Skipping job ID: {job_id} (status: {status})")
            continue

        logs_to_send = []
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"Fetching logs for job ID: {job_id} (Attempt {attempt}/{MAX_RETRIES})")
            logs = fetch_job_logs(job_id)
            if logs:
                logs_to_send.extend(logs)
                break  # Stop retrying once logs are fetched
            print(f"No logs available yet for job ID: {job_id}. Retrying in {RETRY_INTERVAL_SECONDS} seconds...")
            time.sleep(RETRY_INTERVAL_SECONDS)

        if logs_to_send:
            print(f"Sending {len(logs_to_send)} log lines to Loki for job {name}...")
            push_to_loki(logs_to_send, LABELS, job_name=name, job_id=job_id)
        else:
            print(f"No logs to send for job {name}.")

if __name__ == "__main__":
    main()
