variable "region" {
  description = "AWS Region for every resource."
  type        = string
  default     = "ap-southeast-1"
}

variable "project" {
  description = "Name prefix and value of the Project cost allocation tag."
  type        = string
  default     = "liveask"
}

variable "environment" {
  type    = string
  default = "lab"
}

variable "owner" {
  description = "Value of the Owner tag (your name or GitHub handle)."
  type        = string
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version. Pick one in STANDARD support (aws eks describe-cluster-versions); extended support costs 6x more per hour."
  type        = string
  default     = "1.35"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "Who may reach the Kubernetes API. Set to your own IP, e.g. [\"203.0.113.10/32\"]."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium", "t3a.medium"]
}

variable "node_capacity_type" {
  description = "SPOT is about 60-70% cheaper than ON_DEMAND and fine for a lab."
  type        = string
  default     = "SPOT"

  validation {
    condition     = contains(["SPOT", "ON_DEMAND"], var.node_capacity_type)
    error_message = "node_capacity_type must be SPOT or ON_DEMAND."
  }
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "github_repo" {
  description = "GitHub repository allowed to deploy, as owner/name."
  type        = string
}

variable "create_github_oidc_provider" {
  description = "An account holds one GitHub OIDC provider. Set true only if your account has none yet."
  type        = bool
  default     = false
}

variable "monthly_budget_usd" {
  type    = number
  default = 30
}

variable "budget_email" {
  description = "Where AWS Budgets sends alerts. Leave empty to skip the budget."
  type        = string
  default     = ""
}
