FROM public.ecr.aws/lambda/python:3.12
RUN dnf install -y git
RUN git clone https://github.com/ultralytics/yolov5 /opt/yolov5
RUN pip install --no-cache-dir "numpy<2" torch==2.2.2+cpu torchvision==0.17.2+cpu --extra-index-url https://download.pytorch.org/whl/cpu
RUN sed -i '/opencv-python/d' /opt/yolov5/requirements.txt && pip install --no-cache-dir -r /opt/yolov5/requirements.txt "numpy<2"
RUN pip uninstall -y opencv-python || true
RUN pip install --no-cache-dir --force-reinstall --no-deps "opencv-python-headless==4.9.0.80"
RUN curl -L -o /opt/yolov5/yolov5s.pt https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
CMD ["lambda_function.lambda_handler"]
