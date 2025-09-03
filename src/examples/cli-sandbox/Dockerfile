# examples/cli-sandbox/Dockerfile
FROM debian:bookworm-slim

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      bash ca-certificates coreutils procps git curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
CMD ["bash", "-lc", "sleep infinity"]
