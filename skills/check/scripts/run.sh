#!/usr/bin/env bash
# Run one Makefile target and print a fixed report.
# The report is extracted by this script, not by the model, so the evidence
# cannot be summarized, reordered, or picked selectively.
set -u

target="${1:?usage: run.sh <make-target>}"
log="$(mktemp "${TMPDIR:-/tmp}/factory-${target}-XXXXXX")"

make "$target" >"$log" 2>&1
code=$?

# Strip color codes so the patterns below match (portable: no sed -i, no \x1b).
esc="$(printf '\033')"
sed "s/${esc}\[[0-9;]*m//g" "$log" >"$log.clean" && mv "$log.clean" "$log"

status=PASS
[ "$code" -ne 0 ] && status=FAIL

# Coverage and warnings follow pytest's output format; other stacks print "not printed".
coverage="$(grep -oE 'Total coverage: [0-9.]+%' "$log" | tail -n 1 | grep -oE '[0-9.]+%')"
[ -z "$coverage" ] && coverage="$(grep -E '^TOTAL[[:space:]]' "$log" | tail -n 1 | awk '{print $NF}')"
warnings="$(grep -E '^=+ .*(passed|failed|error)' "$log" | tail -n 1 | grep -oE '[0-9]+ warnings?' | grep -oE '^[0-9]+')"

echo "target:   $target"
echo "status:   $status (exit $code)"
echo "coverage: ${coverage:-not printed}"
echo "warnings: ${warnings:-not printed}"
echo "full log: $log"
echo "--- last 15 lines ---"
tail -n 15 "$log"

exit "$code"
