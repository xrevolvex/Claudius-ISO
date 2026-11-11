#!/usr/bin/env bash
# Check every package in the given live-build package lists against the
# Debian archive. Missing ones are commented out with a warning, so the build
# carries on instead of failing 20 minutes in.
#   check-packages.sh <suite> <list files...>
set -euo pipefail
SUITE="$1"; shift

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/lists/partial" "$TMP/cache" "$TMP/etc"
cat > "$TMP/etc/sources.list" <<EOF
deb http://deb.debian.org/debian $SUITE main contrib non-free-firmware
deb http://deb.debian.org/debian $SUITE-updates main contrib non-free-firmware
EOF
APT_OPTS=(-o Dir::Etc::SourceList="$TMP/etc/sources.list" -o Dir::Etc::SourceParts=/dev/null
          -o Dir::State::Lists="$TMP/lists" -o Dir::Cache="$TMP/cache"
          -o APT::Architecture=amd64 -o Debug::NoLocking=1)
apt-get "${APT_OPTS[@]}" update -qq >/dev/null

missing=0
for list in "$@"; do
    while read -r pkg; do
        [ -z "$pkg" ] && continue
        # A real package has an installable candidate (virtual or removed ones show "(none)")
        cand=$(apt-cache "${APT_OPTS[@]}" policy "$pkg" 2>/dev/null | awk '/Candidate:/ {print $2}')
        if [ -z "$cand" ] || [ "$cand" = "(none)" ]; then
            echo "::warning::package '$pkg' is not in Debian $SUITE: removed from $(basename "$list")"
            sed -i "s/^${pkg}\$/# (not in $SUITE) ${pkg}/" "$list"
            missing=$((missing + 1))
        fi
    done < <(grep -Ev '^\s*(#|$)' "$list" | awk '{print $1}')
done
echo "package check finished: $missing missing"
