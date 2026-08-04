aws_region   = "us-east-1"
project_name = "targeting-service-dev"

# Remote State da plataforma
platform_state_bucket = "toggle-master-terraform-state-103568492404"
platform_state_key    = "platform/dev/terraform.tfstate"

# RDS
db_instance_class = "db.t3.micro"
db_name           = "targeting_db"
db_username       = "fiap"
