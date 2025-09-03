# src/examples/cli-sandbox/Dockerfile
# Minimal sandbox image with Python and common CLI tools
FROM python:3.11-slim

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      bash curl git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Workdir is driven by env substitution; default to /workspace
ARG WORKDIR=/workspace
WORKDIR ${WORKDIR}

# Keep container alive; commands are executed via solitary exec
CMD ["bash", "-lc", "sleep infinity"]

