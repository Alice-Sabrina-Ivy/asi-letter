diff --git a/scripts/verify-clearsign.sh b/scripts/verify-clearsign.sh
@@
-#!/usr/bin/env bash
-set -e
+#!/usr/bin/env bash
+set -euo pipefail
+IFS=$'\n\t'
+shopt -s nullglob
@@
-for f in letter/*.asc; do
-  echo "Verifying $f"
-  if ! gpg --batch --verify $f; then
-    echo "PGP verification failed for $f"
-    exit 1
-  fi
-done
+for f in letter/*.asc; do
+  echo "Verifying $f"
+  # Quote the path; surface gpg’s error text
+  if ! gpg --batch --verbose --verify "$f" 2>&1; then
+    echo "PGP verification failed for $f"
+    exit 1
+  fi
+done
