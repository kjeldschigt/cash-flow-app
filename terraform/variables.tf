variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "cash-flow-app"
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "docker_image" {
  description = "Docker image repository"
  type        = string
  default     = "your-dockerhub-username/cash-flow-app"
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "task_cpu" {
  description = "CPU units for ECS task"
  type        = string
  default     = "512"
}

variable "task_memory" {
  description = "Memory for ECS task"
  type        = string
  default     = "1024"
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 10
}

variable "encryption_master_key" {
  description = "Master encryption key"
  type        = string
  sensitive   = true
}

variable "stripe_secret_key" {
  description = "Stripe secret key"
  type        = string
  sensitive   = true
}
