aws_region  = "us-west-2"
environment = "staging"
app_name    = "fluxion"

vpc_cidr             = "10.1.0.0/16"
availability_zones   = ["us-west-2a", "us-west-2b"]
public_subnet_cidrs  = ["10.1.1.0/24", "10.1.2.0/24"]
private_subnet_cidrs = ["10.1.4.0/24", "10.1.5.0/24"]

instance_type        = "t3.medium"
asg_min_size         = 1
asg_max_size         = 5
asg_desired_capacity = 2

db_instance_class = "db.t3.medium"
db_name           = "fluxiondb"
db_username       = "fluxion_admin"
# db_password must be set via environment variable: TF_VAR_db_password
db_multi_az                = false
db_backup_retention_period = 7
db_deletion_protection     = true
db_skip_final_snapshot     = false

enable_nat_gateway  = true
enable_flow_logs    = true
enable_guardduty    = true
enable_cloudtrail   = true
enable_security_hub = false

enable_s3_versioning  = true
backup_retention_days = 60

default_tags = {
  Terraform   = "true"
  Environment = "staging"
  Project     = "Fluxion"
}
