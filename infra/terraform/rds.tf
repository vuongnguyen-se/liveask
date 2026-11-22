resource "aws_security_group" "db" {
  name        = "${local.name}-db"
  description = "PostgreSQL, reachable only from EKS worker nodes"
  vpc_id      = module.vpc.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "db_from_nodes" {
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = module.eks.node_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  description                  = "Pods on EKS nodes"
}

resource "aws_db_instance" "liveask" {
  identifier     = "${local.name}-db"
  engine         = "postgres"
  engine_version = "17"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "liveask"
  username = "liveask_admin"
  # RDS creates the password and keeps it in Secrets Manager; it never appears in Terraform state.
  manage_master_user_password = true

  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false # lab; production would use true

  backup_retention_period = 1
  skip_final_snapshot     = true  # lab: destroy without leaving a snapshot to pay for
  deletion_protection     = false # lab
  apply_immediately       = true
}
