1. Build the image locally:
   `docker build -t transfer-system:latest .`
2. If you use `kind`, load the image into the cluster:
   `kind load docker-image transfer-system:latest`
3. Install cluster add-ons required for autoscaling:
   - HPA needs `metrics-server`.
   - Worker autoscaling needs KEDA and its CRDs.
4. Create local secrets:
   `Copy-Item k8s/secrets.yaml.example k8s/secrets.yaml`
   Update passwords, `DATABASE_URL`, `RABBITMQ_URL`, and `SENTRY_DSN`.
5. Apply the runtime manifests:
   `kubectl apply -f k8s/namespace.yaml`
   `kubectl apply -f k8s/secrets.yaml`
   `kubectl apply -f k8s/configmap.yaml`
   `kubectl apply -f k8s/postgres.yaml`
   `kubectl apply -f k8s/redis.yaml`
   `kubectl apply -f k8s/rabbitmq.yaml`
   `kubectl apply -f k8s/app-deployment.yaml`
   `kubectl apply -f k8s/worker-deployment.yaml`
   `kubectl apply -f k8s/nginx.yaml`
   `kubectl apply -f k8s/hpa-app.yaml`
   `kubectl apply -f k8s/keda-worker-scaledobject.yaml`
6. Check pods:
   `kubectl get pods -n transfer-system`
7. If the pods are running, open the API through nginx locally:
   `kubectl port-forward -n transfer-system svc/transfer-nginx 8080:80`
8. Call the API at:
   `http://localhost:8080`

Notes:
- `imagePullPolicy: Never` means Kubernetes will not download the image from Docker Hub or another registry. The image must already exist inside the cluster runtime.
- This setup is for local development. Postgres uses a 1Gi `PersistentVolumeClaim`; delete the claim if you want to reset local cluster data.
- ConfigMap values are defined in `k8s/configmap.yaml`.
- Secrets are defined locally in `k8s/secrets.yaml`, which is ignored by Git. Use `k8s/secrets.yaml.example` as a template, then change database, RabbitMQ, and Sentry values before applying manifests.

Load testing:

1. Rebuild and reload the image after changing scripts:
   `docker build -t transfer-system:latest .`
   `kind load docker-image transfer-system:latest`
2. Run API load through Nginx rate limiting:
   `powershell -ExecutionPolicy Bypass -File scripts/k8s_load_test.ps1 -Mode api`
3. Run direct worker/RabbitMQ load for KEDA scaling:
   `powershell -ExecutionPolicy Bypass -File scripts/k8s_load_test.ps1 -Mode worker`
4. Watch scaling in separate terminals:
   `kubectl get hpa transfer-app-hpa -n transfer-system --watch`
   `kubectl get scaledobject transfer-worker-scaledobject -n transfer-system --watch`
   `kubectl get pods -n transfer-system --watch`

Tuning:

- `k8s/load-api-job.yaml` loads the public path through `http://transfer-nginx`.
- Keep `LOAD_RPS` at `20` or below to stay inside the Nginx `/transfers` limit.
- Set `LOAD_BASE_URL` to `http://transfer-app:8000` and raise `LOAD_RPS` if you want to bypass Nginx and push the FastAPI app harder for HPA.
- `k8s/load-worker-job.yaml` publishes notification tasks directly to RabbitMQ. This is the clearest way to grow the `celery` queue and trigger KEDA worker scaling.
