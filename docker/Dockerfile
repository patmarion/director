FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
  xvfb \
  curl \
  ca-certificates \
  libgl1-mesa-dri \
  libglx-mesa0 \
  libegl1 \
  mesa-utils \
  libfontconfig1 \
  libglib2.0-0 \
  libdbus-1-3 \
  libxkbcommon-x11-0 \
  libx11-xcb1 \
  libxcb-cursor0 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-randr0 \
  libxcb-render-util0 \
  libxcb-shape0 \
  libxcb-shm0 \
  libxcb-sync1 \
  libxcb-util1 \
  libxcb-xfixes0 \
  libxcb-xkb1 \
  && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh