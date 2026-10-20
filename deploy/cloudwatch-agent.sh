#!/usr/bin/env bash
# Installs the Amazon CloudWatch agent on the EC2 app server so memory and disk
# usage show up in CloudWatch (EC2's built-in metrics only cover CPU, network
# and status checks). Run ON the server, as root:
#
#   sudo bash cloudwatch-agent.sh
#
# Prerequisite: the instance role (apps-ecr-readonly-role) must have the AWS-managed
# policy CloudWatchAgentServerPolicy attached, otherwise the agent starts but
# cannot publish anything. Safe to re-run.
#
# Metrics appear in the CloudWatch namespace "CWAgent":
#   mem_used_percent                         dimension: InstanceId
#   disk_used_percent (path=/)               dimensions: InstanceId, path, device, fstype
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "run as root: sudo bash $0" >&2; exit 1; }

CONFIG_DIR=/opt/aws/amazon-cloudwatch-agent/etc
CONFIG="$CONFIG_DIR/amazon-cloudwatch-agent.json"

echo "== install the agent =="
if ! command -v amazon-cloudwatch-agent-ctl >/dev/null 2>&1 && [ ! -x /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl ]; then
  dnf install -y amazon-cloudwatch-agent
else
  echo "already installed"
fi

echo "== write the config =="
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG" <<'JSON'
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root"
  },
  "metrics": {
    "namespace": "CWAgent",
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}"
    },
    "metrics_collected": {
      "mem": {
        "measurement": ["mem_used_percent"]
      },
      "disk": {
        "measurement": ["used_percent"],
        "resources": ["/"],
        "ignore_file_system_types": ["sysfs", "devtmpfs", "tmpfs", "overlay", "squashfs"]
      }
    }
  }
}
JSON

echo "== start it =="
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -c "file:$CONFIG" -s

sleep 3
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a status

cat <<'NEXT'

Agent started. After 2-3 minutes the metrics appear in CloudWatch -> Metrics -> All metrics -> CWAgent.
If nothing appears, the usual cause is the missing CloudWatchAgentServerPolicy on the instance role:
  sudo tail -n 30 /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log
NEXT
