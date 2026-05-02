#!/usr/bin/env bash
# Daily object-store replication integrity check (S574 / RB-023).
#
# Lists every object in the source prefix, fetches the corresponding
# object's ETag + size from the destination region, and writes:
#   - integrity.tsv  (one row per object)
#   - summary.json   (counters)
#   - prom.txt       (Prometheus exposition snippet)
#
# Usage:
#   scripts/objstore_integrity_check.sh \
#     --bucket=loop-audit-log-us-east-1 \
#     --prefix=audit-log/ \
#     --dest=loop-audit-log-us-west-2 \
#     [--out=/tmp/objstore-integrity] \
#     [--dry-run]
#
#   scripts/objstore_integrity_check.sh repair \
#     --manifest /path/to/integrity.tsv
#
# Per RB-023, an object is considered failing only if it appears in
# two consecutive daily manifests. The grace window for newly-written
# objects is 15 min.
set -euo pipefail

MODE="check"
if [ "${1:-}" = "repair" ]; then
  MODE="repair"
  shift
fi

BUCKET=""
PREFIX=""
DEST=""
MANIFEST=""
OUT_DIR="/tmp/objstore-integrity"
DRY_RUN="false"
GRACE_SECONDS="900"

usage() {
  sed -n '2,22p' "$0" >&2
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bucket=*)   BUCKET="${1#*=}"   ;;
    --prefix=*)   PREFIX="${1#*=}"   ;;
    --dest=*)     DEST="${1#*=}"     ;;
    --manifest=*) MANIFEST="${1#*=}" ;;
    --manifest)   shift; MANIFEST="$1" ;;
    --out=*)      OUT_DIR="${1#*=}"  ;;
    --grace=*)    GRACE_SECONDS="${1#*=}" ;;
    --dry-run)    DRY_RUN="true"     ;;
    --help|-h)    usage              ;;
    *) echo "unknown arg: $1" >&2; usage ;;
  esac
  shift
done

mkdir -p "$OUT_DIR"

if [ "$MODE" = "repair" ]; then
  [ -n "$MANIFEST" ] || { echo "missing --manifest" >&2; exit 2; }
  [ -f "$MANIFEST" ] || { echo "manifest not found: $MANIFEST" >&2; exit 2; }
  repaired=0
  while IFS=$'\t' read -r bucket key src_etag dst_etag status; do
    [ "$status" = "ok" ] && continue
    [ "$bucket" = "bucket" ] && continue   # header row
    if [ "$DRY_RUN" = "true" ]; then
      echo "[dry-run] would re-upload s3://$bucket/$key" >&2
    else
      aws s3 cp "s3://$bucket/$key" "s3://$bucket/$key" \
        --metadata-directive REPLACE \
        --copy-props metadata-directive >/dev/null
    fi
    repaired=$((repaired + 1))
  done < "$MANIFEST"
  printf '{"mode":"repair","repaired":%d,"dry_run":%s}\n' "$repaired" "$DRY_RUN"
  exit 0
fi

[ -n "$BUCKET" ] || { echo "missing --bucket" >&2; exit 2; }
[ -n "$DEST" ]   || { echo "missing --dest" >&2; exit 2; }

INTEGRITY="$OUT_DIR/integrity.tsv"
SUMMARY="$OUT_DIR/summary.json"
PROM="$OUT_DIR/prom.txt"

started_at="$(date -u +%FT%TZ)"
checked=0; ok=0; missing=0; mismatch=0
printf 'bucket\tkey\tsource_etag\tdest_etag\tstatus\n' > "$INTEGRITY"

if [ "$DRY_RUN" = "true" ]; then
  # Synthetic fixture: one ok, one missing, one etag-mismatch.
  printf '%s\t%s\t%s\t%s\t%s\n' "$BUCKET" "audit-log/2026/05/01.json.gz" "abc123" "abc123" "ok"           >> "$INTEGRITY"
  printf '%s\t%s\t%s\t%s\t%s\n' "$BUCKET" "audit-log/2026/05/02.json.gz" "def456" ""       "missing"     >> "$INTEGRITY"
  printf '%s\t%s\t%s\t%s\t%s\n' "$BUCKET" "audit-log/2026/05/03.json.gz" "ghi789" "xyz999" "etag-mismatch" >> "$INTEGRITY"
  checked=3; ok=1; missing=1; mismatch=1
else
  while IFS=$'\t' read -r key src_etag src_age; do
    checked=$((checked + 1))
    if [ "$src_age" -lt "$GRACE_SECONDS" ]; then
      printf '%s\t%s\t%s\t%s\t%s\n' "$BUCKET" "$key" "$src_etag" "" "in-grace" >> "$INTEGRITY"
      ok=$((ok + 1))
      continue
    fi
    dst_meta="$(aws s3api head-object --bucket "$DEST" --key "$key" 2>/dev/null || echo MISSING)"
    if [ "$dst_meta" = "MISSING" ]; then
      printf '%s\t%s\t%s\t%s\t%s\n' "$BUCKET" "$key" "$src_etag" "" "missing" >> "$INTEGRITY"
      missing=$((missing + 1)); continue
    fi
    dst_etag="$(printf '%s' "$dst_meta" | python3 -c 'import json,sys;print(json.load(sys.stdin)["ETag"].strip(chr(34)))')"
    if [ "$src_etag" = "$dst_etag" ]; then
      printf '%s\t%s\t%s\t%s\t%s\n' "$BUCKET" "$key" "$src_etag" "$dst_etag" "ok" >> "$INTEGRITY"
      ok=$((ok + 1))
    else
      printf '%s\t%s\t%s\t%s\t%s\n' "$BUCKET" "$key" "$src_etag" "$dst_etag" "etag-mismatch" >> "$INTEGRITY"
      mismatch=$((mismatch + 1))
    fi
  done < <(aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "$PREFIX" \
             --query 'Contents[].[Key,ETag,LastModified]' --output text \
             | awk -v now="$(date -u +%s)" -F'\t' '{
                 cmd="date -u -d \"" $3 "\" +%s"; cmd | getline ts; close(cmd);
                 etag=$2; gsub("\"","",etag);
                 print $1 "\t" etag "\t" (now-ts)
               }')
fi

ended_at="$(date -u +%FT%TZ)"
failures=$((missing + mismatch))

cat > "$SUMMARY" <<JSON
{"bucket":"$BUCKET","prefix":"$PREFIX","dest":"$DEST","checked":$checked,"ok":$ok,"missing":$missing,"mismatch":$mismatch,"failures":$failures,"started_at":"$started_at","ended_at":"$ended_at"}
JSON

cat > "$PROM" <<PROM
# HELP loop_objstore_replication_integrity_failures Number of objects in the source bucket whose replicated copy is missing or mismatched.
# TYPE loop_objstore_replication_integrity_failures gauge
loop_objstore_replication_integrity_failures{bucket="$BUCKET",prefix="$PREFIX"} $failures
# HELP loop_objstore_replication_integrity_checked Number of objects scanned in the latest run.
# TYPE loop_objstore_replication_integrity_checked gauge
loop_objstore_replication_integrity_checked{bucket="$BUCKET",prefix="$PREFIX"} $checked
PROM

echo "integrity check complete: bucket=$BUCKET checked=$checked failures=$failures" >&2
exit 0
