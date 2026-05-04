terraform {
  required_version = ">= 1.7.0"
  required_providers {
    pagerduty = {
      source  = "pagerduty/pagerduty"
      version = ">= 3.11.0"
    }
  }
}

locals {
  schedule      = yamldecode(file(var.schedule_file))
  rotation_map  = { for rotation in local.schedule.rotations : rotation.name => rotation }
  user_emails   = toset(flatten([for rotation in local.schedule.rotations : rotation.users]))
}

data "pagerduty_user" "oncall" {
  for_each = local.user_emails
  email    = each.value
}

resource "pagerduty_schedule" "rotation" {
  for_each  = local.rotation_map
  name      = "${local.schedule.team}-${each.key}"
  time_zone = local.schedule.timezone

  layer {
    name                         = each.key
    start                        = each.value.start
    rotation_virtual_start       = each.value.start
    rotation_turn_length_seconds = each.value.turn_length_hours * 3600
    users                        = [for email in each.value.users : data.pagerduty_user.oncall[email].id]
  }
}

resource "pagerduty_escalation_policy" "oncall" {
  name      = "${local.schedule.team}-escalation"
  num_loops = 2

  dynamic "rule" {
    for_each = local.schedule.escalation
    content {
      escalation_delay_in_minutes = rule.value.delay_minutes
      target {
        type = "schedule_reference"
        id   = pagerduty_schedule.rotation[rule.value.target].id
      }
    }
  }
}
