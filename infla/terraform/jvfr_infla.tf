resource "aws_dynamodb_table" "jvfr_dynamodb_table" {
  name           = "jvfr_glass"
  read_capacity  = 10
  write_capacity = 10
  hash_key       = "ProductID"

  attribute {
    name = "ProductID"
    type = "S"
  }

}
