aws_region  = "us-west-2"
environment = "prod"
app_name    = "fluxion"

vpc_cidr             = "10.2.0.0/16"
availability_zones   = ["us-west-2a", "us-west-2b", "us-west-2c"]
public_subnet_cidrs  = ["10.2.1.0/24", "10.2.2.0/24", "10.2.3.0/24"]
private_subnet_cidrs = ["10.2.4.0/24", "10.2.5.0/24", "10.2.6.0/24"]

instance_type        = "t3.large"
key_name             = "prod-key"
asg_min_size         = 2
asg_max_size         = 10
asg_desired_capacity = 3

db_instance_class = "db.t3.large"
db_name           = "fluxiondb"
db_username       = "fluxion_admin"
# db_password must be set via environment variable: TF_VAR_db_password
db_multi_az                = true
db_backup_retention_period = 14
db_deletion_protection     = true
db_skip_final_snapshot     = false
db_performance_insights    = true
db_monitoring_interval     = 60

enable_nat_gateway  = true
enable_flow_logs    = true
enable_guardduty    = true
enable_cloudtrail   = true
enable_security_hub = true

enable_s3_versioning  = true
backup_retention_days = 90

default_tags = {
  Terraform   = "true"
  Environment = "prod"
  Project     = "Fluxion"
  Owner       = "DevOps"
  CostCenter  = "Engineering"
  Compliance  = "Financial"
}
