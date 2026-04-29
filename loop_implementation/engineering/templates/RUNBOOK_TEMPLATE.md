# RB-NNN — Title

**Owner:** Name (role)
**SEV target:** SEV1 / SEV2 / SEV3
**RTO target:** ≤ X
**RPO target:** ≤ Y
**Last drilled:** YYYY-MM-DD (Name)

## Symptoms

The exact alert names, log lines, dashboard signals that say "this is happening." Be literal — these are what someone copy-pastes into search at 3 a.m.

```
PagerDuty: <alert name>
Grafana: <dashboard panel>
Logs (Loki):
  service="dp-runtime" level="error" code="LOOP-RT-401"
  Connection refused to gateway at ...
```

## Steps

Numbered. Copy-pasteable. Assume the runner has shell + cluster access but no recent context.

1. Acknowledge the page within X min. Open `#inc-YYYYMMDD-<short-slug>`.
2. **Verify the symptom is real:**
   ```bash
   <command 1>
   <command 2>
   ```
3. **Mitigate:**
   ```bash
   <command>
   ```
4. **Verify recovery:**
   - Metric A returns to baseline.
   - Health check returns 200.
5. **Update status page** with recovery message.
6. **Open a PIR ticket** within 24 h. Capture: root cause, time-to-detect, time-to-mitigate, action items.

## Rollback

If a step makes things worse, how to undo it. Be specific.

## Anti-patterns

- ❌ Don't do X — it'll cause Y.
- ❌ Don't skip step N — it leaves stale state.

## Recent drills

| Date | Owner | Result | Notes |
|------|-------|--------|-------|
| YYYY-MM-DD | Name | passed / failed | … |

## Related

- Runbook RB-MMM
- ADR-XXX
- Architecture §Y
