# Local Kubernetes deployment

These manifests deploy the complete Transfer System stack to the
`transfer-system` namespace:

- FastAPI application
- Alembic migration Job
- PostgreSQL with a persistent volume
- Redis
- RabbitMQ
- Celery worker
- Nginx
- HPA and optional KEDA worker autoscaling
- API and worker load-test Jobs

The commands below are written for Git Bash.

## Prerequisites

- Docker Desktop with Kubernetes enabled
- `kubectl` using the `docker-desktop` context
- `metrics-server` for HPA metrics
- KEDA and its CRDs if worker autoscaling is required

Check the cluster before deploying:

```bash
docker desktop kubernetes status
kubectl config current-context
kubectl get nodes
```

The Kubernetes status must be `running`, and the node must be `Ready`.

## Build the application image

Docker Desktop Kubernetes can use images from the local Docker image store:

```bash
docker build -t transfer-system:latest .
```

The manifests use:

```yaml
image: transfer-system:latest
imagePullPolicy: Never
```

For a `kind` cluster, explicitly load the image:

```bash
kind load docker-image transfer-system:latest
```

## Configure secrets

Create the local secrets manifest:

```bash
cp k8s/secrets.yaml.example k8s/secrets.yaml
sed -i "s|AUTH_JWT_SECRET:.*|AUTH_JWT_SECRET: \"$(openssl rand -hex 32)\"|" \
  k8s/secrets.yaml
```

Review and replace all remaining `change-me` values. In particular, verify:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `AUTH_JWT_SECRET`
- `RABBITMQ_DEFAULT_PASS`
- `RABBITMQ_URL`
- `SENTRY_DSN`

`k8s/secrets.yaml` is excluded by `.gitignore` and `.dockerignore`. Never commit
it.

## Deploy infrastructure

Create the namespace and configuration:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
```

Deploy PostgreSQL, Redis, and RabbitMQ:

```bash
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/rabbitmq.yaml
```

Wait for the infrastructure:

```bash
kubectl wait --for=condition=available deployment/postgres \
  -n transfer-system --timeout=180s
kubectl wait --for=condition=available deployment/redis \
  -n transfer-system --timeout=180s
kubectl wait --for=condition=available deployment/rabbitmq \
  -n transfer-system --timeout=180s
```

## Apply database migrations

The application does not create database tables at startup. The migration Job
must complete before app and worker deployments are rolled out.

For a new database:

```bash
kubectl delete job transfer-migrate -n transfer-system --ignore-not-found
kubectl apply -f k8s/migration-job.yaml
kubectl wait --for=condition=complete job/transfer-migrate \
  -n transfer-system --timeout=180s
kubectl logs job/transfer-migrate -n transfer-system
```

Delete and recreate the Job for every release. Reapplying an already completed
Job does not execute newly added Alembic revisions.

If the PostgreSQL PVC contains a database created before Alembic was introduced,
do not run the regular Job immediately. First mark that database as baseline
revision `20260830_01`, then run `alembic upgrade head`. Do not stamp a new or
empty database.

## Deploy the application

After the migration Job completes:

```bash
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/nginx.yaml
```

Check the rollout:

```bash
kubectl rollout status deployment/transfer-app \
  -n transfer-system --timeout=180s
kubectl rollout status deployment/transfer-worker \
  -n transfer-system --timeout=180s
kubectl rollout status deployment/transfer-nginx \
  -n transfer-system --timeout=180s
kubectl get pods,services,pvc,jobs -n transfer-system
```

Inspect problems with:

```bash
kubectl get events -n transfer-system --sort-by=.lastTimestamp
kubectl logs deployment/transfer-app -n transfer-system
kubectl logs deployment/transfer-worker -n transfer-system
kubectl describe pod -n transfer-system POD_NAME
```

## Open the API

Forward the Nginx service:

```bash
kubectl port-forward -n transfer-system svc/transfer-nginx 8080:80
```

The API is then available at:

- <http://localhost:8080/health>
- <http://localhost:8080/docs>

## Autoscaling

Apply HPA only after `metrics-server` is available:

```bash
kubectl apply -f k8s/hpa-app.yaml
kubectl get hpa transfer-app-hpa -n transfer-system
```

Apply the worker ScaledObject only after KEDA is installed:

```bash
kubectl apply -f k8s/keda-worker-scaledobject.yaml
kubectl get scaledobject transfer-worker-scaledobject -n transfer-system
```

## Load testing

Run API load through Nginx:

```bash
powershell -ExecutionPolicy Bypass \
  -File scripts/k8s_load_test.ps1 -Mode api
```

Run direct RabbitMQ/Celery worker load:

```bash
powershell -ExecutionPolicy Bypass \
  -File scripts/k8s_load_test.ps1 -Mode worker
```

Watch scaling:

```bash
kubectl get hpa transfer-app-hpa -n transfer-system --watch
kubectl get scaledobject transfer-worker-scaledobject \
  -n transfer-system --watch
kubectl get pods -n transfer-system --watch
```

`k8s/load-api-job.yaml` targets Nginx by default. Keep `LOAD_RPS` at `20` or
below to remain within the configured `/transfers` rate limit. Set
`LOAD_BASE_URL` to `http://transfer-app:8000` to bypass Nginx when testing HPA.
The Job creates temporary authenticated accounts and sends each transfer with
the source wallet owner's Bearer token. Run it only against disposable data or
remove the generated `load_*` accounts after inspecting the results.

## Reset local Kubernetes data

PostgreSQL uses a `1Gi` PVC. Deleting deployments does not remove database data.
To intentionally reset the local database, delete the PVC only after confirming
that its contents are disposable:

```bash
kubectl delete pvc postgres-data -n transfer-system
```

PVC deletion is destructive and cannot be undone without a backup.
