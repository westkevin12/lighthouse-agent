# Project name used for resource naming
project_name = "lighthouse-auditor"

# Your Production Google Cloud project id
prod_project_id = "your-prod-project-id"

# Your Staging / Test Google Cloud project id
staging_project_id = "your-staging-project-id"

# Your Google Cloud project ID that will be used to host the Cloud Build pipelines.
cicd_runner_project_id = "your-cicd-project-id"

# Name of the host connection you created in Cloud Build
host_connection_name = "your-git-host-connection"

# Name of the repository you added to Cloud Build
repository_name = "your-repository-name"

# The Google Cloud region you will use to deploy the infrastructure
region = "us-central1"

# Log filters for telemetry and feedback
telemetry_logs_filter = "jsonPayload.attributes.\"traceloop.association.properties.log_type\"=\"tracing\" jsonPayload.resource.attributes.\"service.name\"=\"lighthouse-auditor\""
feedback_logs_filter = "jsonPayload.log_type=\"feedback\""

# GitHub configuration
repository_owner = "your-github-username"
github_app_installation_id = "your-github-app-installation-id"
github_pat_secret_id = "your-github-pat-secret-id"
connection_exists = false
repository_exists = false
