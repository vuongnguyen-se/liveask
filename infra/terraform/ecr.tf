resource "aws_ecr_repository" "api" {
  name                 = "${var.project}/notes-api"
  image_tag_mutability = "IMMUTABLE" # a tag (the git SHA) always means the same image
  force_delete         = true        # lab: terraform destroy also removes images

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Keep storage cost flat: only the 10 newest images stay.
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
