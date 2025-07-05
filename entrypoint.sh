#!/bin/bash
set -e

# 1) Find the GID of the mounted docker.sock
DOCKER_SOCKET=/var/run/docker.sock
if [ -e "$DOCKER_SOCKET" ]; then
  DOCKER_GID=$(stat -c '%g' "$DOCKER_SOCKET")
else
  echo "⚠ $DOCKER_SOCKET not found, skipping docker group setup"
  exec "$@"
fi

# 2) Create a 'docker' group with that GID if it doesn't exist
if ! getent group docker >/dev/null; then
  groupadd --gid "$DOCKER_GID" docker
fi

# 3) Add appuser to the 'docker' group
usermod -aG docker appuser

# 4) Exec under appuser
#    We install 'su-exec' to do this cleanly without a full su shell.
exec su-exec appuser "$@"
