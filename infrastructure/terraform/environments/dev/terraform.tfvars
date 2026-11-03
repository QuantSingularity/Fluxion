aws_region  = "us-west-2"
environment = "dev"
app_name    = "fluxion"

vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["us-west-2a", "us-west-2b"]
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.4.0/24", "10.0.5.0/24"]

instance_type        = "t3.small"
asg_min_size         = 1
asg_max_size         = 3
asg_desired_capacity = 1

db_instance_class = "db.t3.small"
db_name           = "fluxiondb"
db_username       = "fluxion_admin"
# db_password must be set via environment variable: TF_VAR_db_password
db_multi_az                = false
db_backup_retention_period = 1
db_deletion_protection     = false
db_skip_final_snapshot     = true

enable_nat_gateway  = true
enable_flow_logs    = false
enable_guardduty    = false
enable_cloudtrail   = true
enable_security_hub = false

enable_s3_versioning  = false
backup_retention_days = 30

default_tags = {
  Terraform   = "true"
  Environment = "dev"
  Project     = "Fluxion"
}
