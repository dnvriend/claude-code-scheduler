# AWS Infrastructure Reference

The project includes Pulumi IaC in `claude-code-scheduler-iac/` for deploying distributed architecture.

## Deployed Resources

```yaml
region              : "eu-central-1"
command_topic_arn   : "arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-command-topic"
control_bus_arn     : "arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-control-bus"
server_queue_url    : "https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-server-queue"
node_queue_url      : "https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-node-queue"
log_bucket_name     : "claude-code-scheduler-iac-claude-code-scheduler-logs"
instance_id         : "i-0c5604d825c172a85"
instance_private_ip : "172.31.20.208"
instance_public_ip  : "35.156.62.7"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Daemon                               │
│  (Server/Coordinator)                                        │
│  - Receives commands from CLI                                │
│  - Publishes tasks to SNS command topic                      │
│  - Listens to server queue for results                       │
│  - Stores logs in S3                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SNS Command Topic                         │
│  - Fan-out to node queues                                    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│     Node 1      │ │     Node 2      │ │     Node 3      │
│  (Worker)       │ │  (Worker)       │ │  (Worker)       │
│  - Polls queue  │ │  - Polls queue  │ │  - Polls queue  │
│  - Executes     │ │  - Executes     │ │  - Executes     │
│  - Reports back │ │  - Reports back │ │  - Reports back │
└─────────────────┘ └─────────────────┘ └─────────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SNS Control Bus                           │
│  - Node heartbeats                                           │
│  - Status updates                                            │
└─────────────────────────────────────────────────────────────┘
```

## Starting the Daemon (Server/Coordinator)

```bash
claude-code-scheduler daemon \
  --command-topic arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-command-topic \
  --server-queue https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-server-queue \
  --s3-bucket claude-code-scheduler-iac-claude-code-scheduler-logs
```

## Starting a Node (Worker)

```bash
claude-code-scheduler node \
  --command-queue https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-node-queue \
  --control-bus arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-control-bus \
  --s3-bucket claude-code-scheduler-iac-claude-code-scheduler-logs
```

## CLI Commands (Distributed Mode)

```bash
# List connected nodes
claude-code-scheduler cli nodes list

# Get cluster statistics
claude-code-scheduler cli stats

# Submit task to cluster
claude-code-scheduler cli tasks run <task-id>
```

## AWS Resources

### SNS Topics

| Topic | Purpose |
|-------|---------|
| command-topic | Daemon publishes tasks for nodes |
| control-bus | Nodes publish status/heartbeats |

### SQS Queues

| Queue | Purpose |
|-------|---------|
| server-queue | Daemon receives results from nodes |
| node-queue | Nodes receive tasks from daemon |

### S3 Bucket

| Bucket | Purpose |
|--------|---------|
| logs | Task execution logs storage |

### EC2 Instance

| Resource | Value |
|----------|-------|
| Instance ID | i-0c5604d825c172a85 |
| Private IP | 172.31.20.208 |
| Public IP | 35.156.62.7 |

## IAM Permissions

The daemon and nodes need:

**Daemon:**
- `sns:Publish` on command-topic
- `sqs:ReceiveMessage`, `sqs:DeleteMessage` on server-queue
- `s3:PutObject` on logs bucket

**Node:**
- `sqs:ReceiveMessage`, `sqs:DeleteMessage` on node-queue
- `sns:Publish` on control-bus
- `s3:PutObject` on logs bucket

## Deployment

```bash
cd claude-code-scheduler-iac

# Preview changes
pulumi preview

# Deploy
pulumi up

# Get outputs
pulumi stack output
```

## Environment Variables

For distributed mode, set:

```bash
export AWS_PROFILE=sandbox-ilionx-amf
export AWS_REGION=eu-central-1
```

Or use the Bedrock profile which includes these settings.
