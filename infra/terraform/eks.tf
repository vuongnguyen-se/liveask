module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.37"

  cluster_name    = local.name
  cluster_version = var.kubernetes_version

  cluster_endpoint_public_access       = true
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.private_subnets

  cluster_addons = {
    coredns                = {}
    kube-proxy             = {}
    vpc-cni                = { before_compute = true }
    eks-pod-identity-agent = {}
  }

  eks_managed_node_groups = {
    default = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      capacity_type  = var.node_capacity_type

      min_size     = 1
      desired_size = 2
      max_size     = 3
    }
  }

  # Whoever runs terraform apply becomes cluster admin (EKS access entries, no aws-auth ConfigMap).
  enable_cluster_creator_admin_permissions = true

  # The GitHub Actions role may only edit objects in the app namespace.
  access_entries = {
    github_deploy = {
      principal_arn = aws_iam_role.github_deploy.arn
      policy_associations = {
        app = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"
          access_scope = {
            type       = "namespace"
            namespaces = [local.app_namespace]
          }
        }
      }
    }
  }
}

locals {
  app_namespace = "liveask"
}
