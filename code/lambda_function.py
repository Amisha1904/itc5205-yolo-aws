import json
import logging
import os
import time
from decimal import Decimal

os.environ["YOLOV5_CONFIG_DIR"] = "/tmp"
os.environ["TORCH_HOME"] = "/tmp"

import boto3
import torch
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
dynamodb_table = boto3.resource("dynamodb").Table(os.environ.get("TABLE_NAME", "yolo-detections"))
yolo_model = torch.hub.load(
    "/opt/yolov5", "custom", path="/opt/yolov5/yolov5s.pt", source="local"
)


def write_result_with_retry(bucket_name, result_key, result_body, maximum_attempts=3):
    for attempt_number in range(1, maximum_attempts + 1):
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=result_key,
                Body=json.dumps(result_body),
                ContentType="application/json",
            )
            return True
        except ClientError as error:
            logger.error("Write attempt %d failed: %s", attempt_number, error)
            time.sleep(2 ** attempt_number)
    return False


def write_to_dynamodb(image_key, inference_seconds, detected_objects):
    try:
        item = json.loads(
            json.dumps({
                "image": image_key,
                "inference_seconds": inference_seconds,
                "object_count": len(detected_objects),
                "objects": detected_objects,
            }),
            parse_float=Decimal,
        )
        dynamodb_table.put_item(Item=item)
        return True
    except ClientError as error:
        logger.error("DynamoDB write failed: %s", error)
        return False


def lambda_handler(event, context):
    try:
        request_body = json.loads(event.get("body") or "{}")
        bucket_name = request_body["bucket"]
        image_key = request_body["key"]
    except (KeyError, json.JSONDecodeError):
        return {"statusCode": 400, "body": json.dumps({"error": "bucket and key are required"})}

    local_image_path = "/tmp/" + os.path.basename(image_key)
    try:
        s3_client.download_file(bucket_name, image_key, local_image_path)
    except ClientError as error:
        logger.error("Download failed: %s", error)
        return {"statusCode": 404, "body": json.dumps({"error": "image not found"})}

    start_time = time.time()
    detection_results = yolo_model(local_image_path)
    detected_objects = detection_results.pandas().xyxy[0].to_dict(orient="records")
    inference_seconds = round(time.time() - start_time, 3)

    result_key = "results/" + os.path.basename(image_key) + ".json"
    result_body = {
        "image": image_key,
        "inference_seconds": inference_seconds,
        "objects": detected_objects,
    }

    if not write_result_with_retry(bucket_name, result_key, result_body):
        return {"statusCode": 500, "body": json.dumps({"error": "could not store results"})}

    write_to_dynamodb(image_key, inference_seconds, detected_objects)

    logger.info("Processed %s in %s seconds", image_key, inference_seconds)
    return {
        "statusCode": 200,
        "body": json.dumps({"result_key": result_key, "object_count": len(detected_objects)}),
    }
