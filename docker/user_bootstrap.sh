#!/usr/bin/env bash
set -euo pipefail

# Runs as root. Ensures the in-container user/group match the host (UID/GID/name/home),
# then execs the provided command as that user.

host_uid="${HOST_UID}"
host_gid="${HOST_GID}"
host_user="${HOST_USER}"
host_home="${HOST_HOME}"

# Ensure a named primary group exists for HOST_GID.
existing_group_name="$(getent group "${host_gid}" | cut -d: -f1 || true)"
if [[ -z "${existing_group_name}" ]]; then
  groupadd -g "${host_gid}" "${host_user}"
  existing_group_name="${host_user}"
elif [[ "${existing_group_name}" != "${host_user}" ]] && ! getent group "${host_user}" >/dev/null 2>&1; then
  # If the group for this GID has a different name (common: ubuntu), rename it for consistency.
  groupmod -n "${host_user}" "${existing_group_name}" >/dev/null 2>&1 || true
  existing_group_name="${host_user}"
fi

# Ensure the user exists and matches the desired name.
existing_user_name="$(getent passwd "${host_uid}" | cut -d: -f1 || true)"
if [[ -n "${existing_user_name}" ]] && [[ "${existing_user_name}" != "${host_user}" ]] && ! getent passwd "${host_user}" >/dev/null 2>&1; then
  # If this UID already exists (common: ubuntu=1000), rename it so whoami/prompt match the host.
  usermod -l "${host_user}" "${existing_user_name}" >/dev/null 2>&1
fi

if ! getent passwd "${host_user}" >/dev/null 2>&1; then
  useradd -m -u "${host_uid}" -g "${host_gid}" -d "${host_home}" -s /bin/bash "${host_user}"
fi

# Ensure home directory exists and is writable.
usermod -d "${host_home}" "${host_user}" >/dev/null 2>&1 || true
mkdir -p "${host_home}/.cache" "${host_home}/.config"
chown -R "${host_uid}:${host_gid}" "${host_home}" >/dev/null 2>&1 || true

# Add supplemental groups (e.g. render/video for /dev/dri).
IFS=, read -r -a pairs <<< "${EXTRA_GROUPS:-}"
for pair in "${pairs[@]}"; do
  [[ -z "${pair}" ]] && continue
  name="${pair%%:*}"
  gid="${pair##*:}"
  group_name="$(getent group "${gid}" | cut -d: -f1 || true)"
  if [[ -z "${group_name}" ]]; then
    if getent group "${name}" >/dev/null 2>&1; then
      group_name="hostgrp${gid}"
    else
      group_name="${name}"
    fi
    groupadd -g "${gid}" "${group_name}" >/dev/null 2>&1
  fi
  usermod -aG "${group_name}" "${host_user}" >/dev/null 2>&1
done

exec runuser -u "${host_user}" -- "$@"


