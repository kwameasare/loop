output "schedule_ids" {
  description = "PagerDuty schedule IDs keyed by rotation name"
  value       = { for name, schedule in pagerduty_schedule.rotation : name => schedule.id }
}

output "escalation_policy_id" {
  description = "PagerDuty escalation policy ID"
  value       = pagerduty_escalation_policy.oncall.id
}
