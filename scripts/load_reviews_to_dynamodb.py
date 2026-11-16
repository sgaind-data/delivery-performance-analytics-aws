"""
load_reviews_to_dynamodb.py

Loads the Olist order reviews CSV from S3 into the DynamoDB table
`olist_order_reviews` as JSON items, then counts the items to verify.

Run in AWS CloudShell (us-east-2): it is already authenticated, so no
access keys are needed, and boto3 is preinstalled.

    python3 load_reviews_to_dynamodb.py

Design notes
- Key: partition key order_id + sort key review_id. Some orders have more than
  one review, and the raw data contains a few duplicate (order_id, review_id)
  pairs; batch_writer(overwrite_by_pkeys=...) keeps the last copy of a duplicate
  instead of failing the batch.
- review_score is stored as a DynamoDB Number; dates stay as ISO strings.
- Empty optional fields (comment title/message) are omitted, which is the
  normal way to model "missing" in a NoSQL item.
"""

import csv
import io
from decimal import Decimal

import boto3

REGION = "us-east-2"
BUCKET = "sarika-olist-raw-2026"
KEY = "raw/olist_order_reviews_dataset.csv"
TABLE = "olist_order_reviews"

s3 = boto3.client("s3", region_name=REGION)
table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)

# Read the CSV from S3. The csv module handles quoted, multi-line review comments.
body = s3.get_object(Bucket=BUCKET, Key=KEY)["Body"].read().decode("utf-8-sig")
rows = list(csv.DictReader(io.StringIO(body)))
print(f"Read {len(rows):,} review rows from s3://{BUCKET}/{KEY}")

written = 0
with table.batch_writer(overwrite_by_pkeys=["order_id", "review_id"]) as batch:
    for row in rows:
        item = {
            "order_id": row["order_id"],
            "review_id": row["review_id"],
            "review_score": Decimal(row["review_score"]),
            "review_creation_date": row["review_creation_date"],
            "review_answer_timestamp": row["review_answer_timestamp"],
        }
        if row["review_comment_title"].strip():
            item["review_comment_title"] = row["review_comment_title"]
        if row["review_comment_message"].strip():
            item["review_comment_message"] = row["review_comment_message"]
        batch.put_item(Item=item)
        written += 1
        if written % 10000 == 0:
            print(f"  ...{written:,} items sent")

print(f"Sent {written:,} put requests to DynamoDB table {TABLE}")

# Verify: count items actually stored (a paginated COUNT scan).
count = 0
kwargs = {"Select": "COUNT"}
while True:
    page = table.scan(**kwargs)
    count += page["Count"]
    if "LastEvaluatedKey" not in page:
        break
    kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

print(f"Items stored in DynamoDB: {count:,}")
print(f"Duplicates collapsed by the (order_id, review_id) key: {written - count:,}")
