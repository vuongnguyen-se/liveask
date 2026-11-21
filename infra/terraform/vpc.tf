locals {
  name = "${var.project}-${var.environment}"
  azs  = slice(data.aws_availability_zones.available.names, 0, 2)
}

# Two AZs. Public subnets hold the ALB and the NAT gateway; private subnets hold
# the worker nodes; isolated database subnets hold RDS and have no internet route.
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.21"

  name = local.name
  cidr = var.vpc_cidr
  azs  = local.azs

  public_subnets   = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, i)]
  private_subnets  = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 4, i + 1)]
  database_subnets = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, i + 100)]

  create_database_subnet_group = true

  enable_nat_gateway = true
  # One NAT gateway instead of one per AZ: saves ~$33/month, at the cost of AZ redundancy.
  single_nat_gateway   = true
  enable_dns_hostnames = true

  # Tags the AWS Load Balancer Controller uses to find subnets for load balancers.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}
