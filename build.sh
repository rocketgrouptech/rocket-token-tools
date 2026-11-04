#!/bin/sh
# Rebuild the claude.ai upload zips in dist/ from the plugin's skills.
set -e
cd "$(dirname "$0")/plugins/rocket-token-tools/skills"
find . -name '__pycache__' -prune -exec rm -rf {} +
for s in token-usage token-pattern; do
  rm -f "../../../dist/$s.zip"
  zip -rq "../../../dist/$s.zip" "$s"
  echo "dist/$s.zip"
done
