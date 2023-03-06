plugin "terraform" {
  enabled = true
  preset  = "recommended"
  version = "0.2.2"
  source  = "github.com/terraform-linters/tflint-ruleset-terraform"
}
plugin "google" {
  enabled = true
  version = "0.22.2"
  source  = "github.com/terraform-linters/tflint-ruleset-google"
}
config {
  #  format              = "compact"
  module              = true
  force               = false
  disabled_by_default = false
}
rule "terraform_deprecated_interpolation" {
  enabled = false
}
rule "terraform_module_pinned_source" {
  enabled = false
}
rule "terraform_required_providers" {
  enabled = false
}
rule "terraform_required_version" {
  enabled = false
}
