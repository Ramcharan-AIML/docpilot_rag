#!/bin/bash
# First-boot script (cloud-init "user data"): runs ONCE, as root, on the new server.
# Terraform fills in the placeholders like the region and the domain (templatefile).
# Read its log with:
#   sudo tail -n 50 /var/log/cloud-init-output.log
# No "set -x": it would print the Groq key into the log.
set -euo pipefail

REGION="${region}"
APP_DIR=/opt/docpilot

echo "== 1/6 swap: 2 GB of disk as slow extra RAM (B6: peak about 1.6 GB of containers)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo "/swapfile none swap sw 0 0" >> /etc/fstab # keep it after a reboot
fi

echo "== 2/6 Docker Engine + Compose plugin (Docker's official apt repository)"
apt-get update -y
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker # start now and after every reboot

echo "== 3/6 AWS CLI (reads the key and the seed with the server's role, no keys)"
snap install aws-cli --classic
AWS=/snap/bin/aws

echo "== 4/6 the stack's files"
mkdir -p "$APP_DIR/deploy" "$APP_DIR/seed"
echo "${compose_b64}" | base64 -d > "$APP_DIR/docker-compose.yml"
echo "${caddyfile_64}" | base64 -d > "$APP_DIR/deploy/Caddyfile"

echo "== 5/6 .env from SSM Parameter Store (waits until you have stored the key)"
until GROQ_KEY=$($AWS ssm get-parameter --region "$REGION" --name /docpilot/GROQ_API_KEY \
  --with-decryption --query Parameter.Value --output text 2>/dev/null); do
  echo "   /docpilot/GROQ_API_KEY not readable yet; retrying in 20 s"
  sleep 20
done
umask 077 # .env: readable by root only
cat > "$APP_DIR/.env" <<EOF
LLM_PROVIDER=groq
LLM_MODEL=${llm_model}
GROQ_API_KEY=$GROQ_KEY
APP_IMAGE=${app_image}
DOMAIN=${domain}
EOF
unset GROQ_KEY
umask 022

echo "== 6/6 start the stack, then seed the library from S3"
cd "$APP_DIR"
docker compose pull
docker compose up -d
until $AWS s3 cp --region "$REGION" "s3://${seed_bucket}/${seed_file}" "$APP_DIR/seed/" ; do
  echo "   seed file not in the bucket yet; retrying in 20 s"
  sleep 20
done
chmod 644 "$APP_DIR/seed/${seed_file}" # the app runs as uid 1000, not root
docker compose run --rm -v "$APP_DIR/seed:/seed:ro" app python -m docpilot.store.seed "/seed/${seed_file}"

echo "== DONE: check https://${domain}/ready"
