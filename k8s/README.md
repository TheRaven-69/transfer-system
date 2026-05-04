1. Build the image locally:
   `docker build -t transfer-system:latest .`
2. If you use `kind`, load the image into the cluster:
   `kind load docker-image transfer-system:latest`
3. Apply all manifests:
   `kubectl apply -f k8s/`
4. Check pods:
   `kubectl get pods`
5. If the pods are running, open the API through nginx locally:
   `kubectl port-forward svc/transfer-nginx 8080:80`
6. Call the API at:
   `http://localhost:8080`

Notes:
- `imagePullPolicy: Never` means Kubernetes will not download the image from Docker Hub or another registry. The image must already exist inside the cluster runtime.
- This setup is for local development. Postgres uses `emptyDir`, so data is lost after pod recreation.
