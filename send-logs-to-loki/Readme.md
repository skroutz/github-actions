# Send Logs to Loki GitHub Action

The **Send Logs to Loki** GitHub Action collects logs from all jobs in a GitHub Actions workflow and sends them to a Loki instance. Logs are labeled with metadata like job names, job IDs, and custom labels, making them easily searchable and organized in Loki.

## Features

- Aggregates logs from all jobs in a workflow, including job-specific logs.
- Allows dynamic injection of custom labels.
- Automatically retries fetching logs if they are not immediately available.

## Inputs

| Name            | Description                                              | Required | Default              |
| --------------- | -------------------------------------------------------- | -------- | -------------------- |
| `loki_endpoint` | Loki push endpoint                                       | Yes      |                      |
| `labels`        | Custom labels for logs (comma-separated key=value pairs) | No       | job_id=<>``, job_name=<>` |
| `github_token`  | GitHub token for API authentication                      | Yes      |                      |

## Example Usage

```yaml

  - name: Send Logs to Loki
    uses: skroutz/github-actions/send-logs-to-loki@latest
    with:
      loki_endpoint: "https://loki.example.com"
      labels: "job=github-actions,run_id=${{ github.run_id }}"
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

## How It Works

1. **Log Aggregation**: The action iterates over all jobs in the workflow using the GitHub Actions API.
2. **Log Retrieval**: Logs are fetched for completed jobs and skipped for jobs still in progress.
3. **Log Transmission**: Logs are sent to Loki with the specified labels.

## How to Configure

- **Add Custom Labels**: Use the `labels` input to include additional metadata for your logs.
  - Example: `labels: "job=github-actions,env=production"`
- **Loki Endpoint**: Specify the Loki instance URL with `loki_endpoint`.

By default, the `job_id` and `job_name` are automatically added as labels for each job. (Be mindful of cardinality!)

## Known Limitations

- Logs are only fetched for completed jobs. Logs for in-progress jobs will be skipped.
- Timestamps in Loki are processed as arrived. Therefore Loki timestamps are injected at time of transmision, along with Github Actions real Timestamps. 

