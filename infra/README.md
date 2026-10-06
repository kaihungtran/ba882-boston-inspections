# Infrastructure as Code

Owner: **Project lead & DevOps** (see [TEAM.md](../TEAM.md))

Terraform for: GCS landing bucket, BigQuery datasets (`raw`, `staging`, `marts`), service accounts and IAM, Secret Manager secrets, Cloud Run services (later).

```bash
cd infra/terraform
terraform init
terraform plan -var-file=dev.tfvars
```
State: use a GCS backend bucket so the whole team shares one state. Never commit `*.tfstate` or `*.tfvars`.
