Name: Amisha
Student number: 240340
Unit: ITC5205 Assignment 2

Project: YOLOv5 object detection on AWS
Images uploaded to an S3 bucket are processed by a container-based AWS Lambda function running YOLOv5s (PyTorch CPU). The function is exposed through an API Gateway REST endpoint protected by an API key. Each detection result is stored as a JSON file in S3 (results/) and as an item in a DynamoDB table (yolo-detections). Write failures are retried three times and logged to CloudWatch.

Live API (POST, API key required):
https://bupdpufofc.execute-api.us-east-1.amazonaws.com/prod/detect
Request body: {"bucket":"itc5205-yolo-amisha","key":"images/<file>.jpg"}

Folders:
code/    lambda_function.py (Lambda source code)
deploy/  Dockerfile, IAM policies, lambda_function.py copy for the build, deploy-steps.md
images/  screenshots used in the report

Deploy: see deploy/deploy-steps.md
Model weights: https://github.com/ultralytics/yolov5/releases/tag/v7.0 (yolov5s.pt, COCO dataset)
