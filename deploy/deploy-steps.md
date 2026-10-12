# Deployment steps (region us-east-1)

## 1. S3
Create bucket `itc5205-yolo-amisha` with folders `images/` and `results/`. Upload sample JPG images to `images/`.

## 2. DynamoDB
Create table `yolo-detections`, partition key `image` (String), capacity mode On-demand.

## 3. IAM role for Lambda (`yolo-lambda-role`)
Trusted entity: Lambda. Add two inline policies:
- `iam-lambda-policy.json` (S3 read on images/*, write on results/*, CloudWatch Logs)
- `iam-dynamodb-policy.json` (dynamodb:PutItem on the table only)

## 4. Build and push the container image (on an Ubuntu EC2 instance with Docker and AWS CLI)
```
cd deploy
aws ecr create-repository --repository-name yolo-lambda --region us-east-1
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
docker build -t yolo-lambda .
docker tag yolo-lambda:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/yolo-lambda:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/yolo-lambda:latest
```

## 5. Lambda
Create function `yolo-detect-function` from the container image (x86_64), role `yolo-lambda-role`, memory 3008 MB, timeout 1 minute.
To update after a code change: Lambda > Image > Deploy new image > Browse images > yolo-lambda:latest > Save.

## 6. API Gateway
Create REST API, resource `/detect`, method POST with Lambda proxy integration, "API key required" enabled.
Create a usage plan (rate 10 req/s, burst 20, quota 1000/day), create an API key, attach the key and stage `prod` to the plan, deploy to stage `prod`.

## 7. Test
```
curl -X POST "https://<API_ID>.execute-api.us-east-1.amazonaws.com/prod/detect" \
  -H "x-api-key: $KEY" -H "Content-Type: application/json" \
  -d '{"bucket":"itc5205-yolo-amisha","key":"images/download.jpg"}'
```
Expected: `{"result_key": "results/download.jpg.json", "object_count": 1}`. Check `results/` in S3 and the `yolo-detections` table.

## Troubleshooting
- 403 Forbidden: API key missing, wrong, or not attached to the usage plan / stage not redeployed.
- 404 image not found: wrong key, or the object is not in `images/`.
- 500 could not store results: PutObject denied or S3 unavailable (see CloudWatch logs for the three retry attempts).
- 500 under parallel load: Lambda throttling from the account concurrency limit (check Service Quotas).
- First request slow (about 20 s): cold start while the container image and model load.
