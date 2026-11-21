output "cluster_name" {
  value = module.eks.cluster_name
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_DEPLOY_ROLE_ARN variable in the GitHub repository."
  value       = aws_iam_role.github_deploy.arn
}

output "db_endpoint" {
  value = aws_db_instance.notes.address
}

output "db_secret_arn" {
  description = "Secrets Manager secret holding the RDS master password."
  value       = aws_db_instance.notes.master_user_secret[0].secret_arn
}

output "app_namespace" {
  value = local.app_namespace
}
