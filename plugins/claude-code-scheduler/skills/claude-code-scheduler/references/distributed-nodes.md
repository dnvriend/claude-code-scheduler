# Distributed Node Mode Reference

The scheduler supports distributed execution via worker nodes that run Claude Code tasks in isolated environments.

## Architecture

```
┌─────────────┐
│   Server    │ (GUI + Control Bus)
│ + Scheduler │
└──────┬──────┘
       │
       │ SNS/SQS
       │
┌──────┴──────────────────┐
│                         │
▼                         ▼
┌───────────┐      ┌───────────┐
│  Node 1   │      │  Node 2   │
│  (Worker) │      │  (Worker) │
└───────────┘      └───────────┘
```

## Node Command

Run a worker node that listens for tasks from the scheduler:

### Basic Usage

```bash
claude-code-scheduler node \
  --queue-url https://sqs.us-east-1.amazonaws.com/123/command-queue \
  --topic-arn arn:aws:sns:us-east-1:123:control-bus \
  --log-bucket my-log-bucket
```

### With Custom Node ID and Name

```bash
claude-code-scheduler node \
  --queue-url <url> \
  --topic-arn <arn> \
  --log-bucket <bucket> \
  --node-id worker-01 \
  --node-name "Production Worker 1"
```

### With AWS Profile and Region

```bash
claude-code-scheduler node \
  --queue-url <url> \
  --topic-arn <arn> \
  --log-bucket <bucket> \
  --profile production \
  --region us-west-2
```

### With Custom Heartbeat Interval

```bash
claude-code-scheduler node \
  --queue-url <url> \
  --topic-arn <arn> \
  --log-bucket <bucket> \
  --heartbeat-interval 60  # default: 30s
```

### Mock Mode

Simulate execution without running Claude CLI:

```bash
claude-code-scheduler node \
  --queue-url <url> \
  --topic-arn <arn> \
  --log-bucket <bucket> \
  --mock-mode
```

### Verbose Logging

```bash
claude-code-scheduler node <options> -v      # INFO
claude-code-scheduler node <options> -vv     # DEBUG
claude-code-scheduler node <options> -vvv    # TRACE
```

## AWS Infrastructure Requirements

Nodes require the following AWS resources:

1. **SQS Queue** - Command queue for receiving tasks
2. **SNS Topic** - Control bus for publishing events
3. **S3 Bucket** - Storage for task output logs

## Node Lifecycle

1. **Initialization** - Node starts and validates configuration
2. **Registration** - Node registers with control bus (publishes `NodeRegistered` event)
3. **Idle** - Node waits for commands from the queue
4. **Task Execution** - Node receives and executes tasks
5. **Heartbeat** - Node sends periodic heartbeat events
6. **Shutdown** - Node deregisters gracefully on exit

## Node Events

Nodes publish the following events to the control bus:

| Event | Description |
|-------|-------------|
| `NodeRegistered` | Node startup and registration |
| `NodeDeregistered` | Node shutdown |
| `NodeHeartbeat` | Periodic health check |
| `TaskStarted` | Task execution began |
| `TaskOutput` | Task output chunk |
| `TaskCompleted` | Task finished successfully |
| `TaskFailed` | Task encountered an error |

## Environment Variables

Nodes support environment variable configuration:

```bash
# AWS credentials (if not using IAM roles)
export AWS_ACCESS_KEY_ID=<key>
export AWS_SECRET_ACCESS_KEY=<secret>
export AWS_REGION=us-east-1

# Node configuration
export CLAUDE_NODE_QUEUE_URL=<url>
export CLAUDE_NODE_TOPIC_ARN=<arn>
export CLAUDE_NODE_LOG_BUCKET=<bucket>
export CLAUDE_NODE_ID=worker-01
```

## Monitoring

Monitor node health via:

- **Heartbeat events** - Sent every 30 seconds (configurable)
- **AWS CloudWatch** - SQS metrics, SNS delivery stats
- **S3 logs** - Task execution logs in `s3://<bucket>/logs/<run-id>.log`

## Security Considerations

- Nodes require IAM permissions for SQS, SNS, and S3
- Use IAM roles for EC2 instances or ECS tasks
- Enable SQS encryption at rest
- Use VPC endpoints to avoid internet traffic
- Implement least-privilege IAM policies

## IAM Policy Example

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:*:*:command-queue"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:*:*:control-bus"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::log-bucket/logs/*"
    }
  ]
}
```

## Deployed Resources (Example)

```yaml
region              : "eu-central-1"
command_topic_arn   : "arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-command-topic"
control_bus_arn     : "arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-control-bus"
server_queue_url    : "https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-server-queue"
node_queue_url      : "https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-node-queue"
log_bucket_name     : "claude-code-scheduler-iac-claude-code-scheduler-logs"
```

## Full Node Example

```bash
# Start a production worker node
claude-code-scheduler node \
  --queue-url https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-node-queue \
  --topic-arn arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-control-bus \
  --log-bucket claude-code-scheduler-iac-claude-code-scheduler-logs \
  --node-id worker-eu-01 \
  --node-name "EU Production Worker" \
  --heartbeat-interval 30 \
  -v
```
