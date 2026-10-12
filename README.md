# YOLOv5 Object Detection on AWS (Serverless)

**ITC5205 Assignment 2** · Amisha (240340)

A serverless pipeline that detects objects in images stored in Amazon S3. A container-based AWS Lambda function runs the pre-trained **YOLOv5s** model (PyTorch CPU) behind an **API Gateway** REST endpoint protected by an API key. Each result is saved as a JSON file in S3 and as an item in a **DynamoDB** table.

## Architecture

```
Client (curl / Postman, x-api-key)
        │  POST /prod/detect  {"bucket": "...", "key": "images/<file>.jpg"}
        ▼
API Gateway (REST, API key + usage plan)
        │  Lambda proxy integration
        ▼
AWS Lambda  yolo-detect-function  (container image from ECR, YOLOv5s)
        │  read image                      │  write results
        ▼                                  ▼
S3 images/                    S3 results/<image>.json  +  DynamoDB yolo-detections
                                           │
                                     CloudWatch Logs
```

| Component | Purpose |
|---|---|
| S3 bucket `itc5205-yolo-amisha` | `images/` holds input images, `results/` holds output JSON |
| API Gateway (REST, stage `prod`) | `POST /detect` with API key and usage plan (10 req/s, burst 20, 1000/day) |
| Lambda `yolo-detect-function` | Container image with PyTorch and YOLOv5s; retries failed S3 writes three times and logs errors |
| DynamoDB `yolo-detections` | One item per image (partition key `image`), on-demand capacity |
| ECR `yolo-lambda` | Stores the container image built on EC2 |
| EC2 (m7i-flex.large) | Used to install and verify YOLOv5 and to build the Docker image |
| IAM `yolo-lambda-role` | Least-privilege access to S3, DynamoDB `PutItem` on one table, and CloudWatch Logs |
| CloudWatch | Logs and metrics for tuning and cold-start evidence |

All resources are deployed in **us-east-1**.

## Repository structure

```
code/
  lambda_function.py         Lambda handler (S3 read, YOLOv5 inference, S3 + DynamoDB write with retries)
deploy/
  Dockerfile                 Lambda container image (Python 3.12 base, PyTorch CPU, YOLOv5s)
  lambda_function.py         Copy of the handler used by the Docker build
  iam-lambda-policy.json     S3 read on images/*, write on results/*, CloudWatch Logs
  iam-dynamodb-policy.json   dynamodb:PutItem on the yolo-detections table only
  deploy-steps.md            Step-by-step deployment guide
images/                      Screenshots used in the report
readme.txt                   Name, student number and short project description
```

## Deployment

The full steps are in [`deploy/deploy-steps.md`](deploy/deploy-steps.md). In short:

1. Create the S3 bucket with `images/` and `results/` folders and upload sample images.
2. Create the DynamoDB table `yolo-detections` (partition key `image`, on-demand).
3. Create the Lambda role with the two inline policies in `deploy/`.
4. On EC2, build the Docker image from `deploy/` and push it to ECR (`yolo-lambda`).
5. Create the Lambda function from the image (x86_64, 3008 MB, 1-minute timeout).
6. Create the REST API (`POST /detect`, Lambda proxy, API key required), a usage plan and the `prod` stage.

## Usage

1. Upload a JPG to the `images/` folder of the bucket. Use letters, numbers and hyphens in the file name.
2. Send a POST request with your API key:

```bash
curl -X POST "https://bupdpufofc.execute-api.us-east-1.amazonaws.com/prod/detect" \
  -H "x-api-key: $KEY" -H "Content-Type: application/json" \
  -d '{"bucket":"itc5205-yolo-amisha","key":"images/download.jpg"}'
```

3. A successful reply looks like:

```json
{"result_key": "results/download.jpg.json", "object_count": 1}
```

4. Open `results/<image>.json` in S3 for each object's class name, confidence and bounding box, plus the inference time. The same detection is also stored in the `yolo-detections` table.

| Status | Meaning |
|---|---|
| 200 | Detection succeeded and results were stored |
| 400 | `bucket` and `key` are required in the body |
| 403 | Missing or wrong API key |
| 404 | Image not found in the bucket |
| 500 | Results could not be stored, or the request was throttled |

The API key is provided in the report and is not stored in this repository.

## Results

| Memory | Cold request | Warm request |
|---|---|---|
| 2048 MB | 6.24 s and 6.49 s | 0.454 s |
| 3008 MB | 6.30 s | 0.345 s |

- Warm requests were about **18× faster** than cold requests. The first-ever invocation took 20,151 ms and used 621 MB.
- Raising memory from 2048 MB to 3008 MB made warm requests about **24% faster**, because Lambda allocates CPU in proportion to memory.
- **Failure handling:** when S3 writes were denied, the function retried three times with 2, 4 and 8 s back-off, logged each error, and returned HTTP 500. After the policy was restored, the call succeeded.
- **Scaling:** in a test of 20 parallel requests, about half were throttled because this account's Lambda concurrency limit is 10 (the usual default is 1,000). DynamoDB on-demand capacity was not a bottleneck.

## Model and dataset

- Model: YOLOv5s pre-trained weights, [ultralytics/yolov5 v7.0](https://github.com/ultralytics/yolov5/releases/tag/v7.0)
- Test data: sample JPG images in the S3 `images/` folder
