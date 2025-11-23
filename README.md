# MongoDB Metrics App for Minikube (No-Auth MongoDB)

This repository contains everything you need to deploy a MongoDB metrics exporter locally on Minikube:

- Python app exposing MongoDB metrics at `/metrics`
- Kubernetes Deployment + Service for the app
- Deployment + Service for MongoDB (no authentication, for testing only)
- ServiceMonitor and PrometheusRule for Prometheus Operator (`kube-prometheus-stack`)
- Slack alerts
- Grafana dashboard JSON

## Notes
- It was created using a WSL environment
- A slack webhook needs to be configured in order to set the email alerts
- Ensure you have Python installed on your system. You can verify this by running:
```bash
python3 --version
```
- Activate virtual environment and install requirements
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Quick Start

### 1. Start Minikube
   Ensure Minikube has enough resources:

   ```bash
   minikube start --memory=4096 --cpus=2
   ```
### 2. Build the Docker image inside Minikube
   ```bash
   docker build -t mongodb-metrics-app:latest .
   ```

### 3. Create namespace and deploy MongoDB + app + monitoring resources
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/mongo-deployment.yaml
   kubectl apply -f k8s/app-deployment.yaml
   kubectl apply -f k8s/app-service.yaml
   kubectl apply -f k8s/servicemonitor.yaml
   kubectl apply -f k8s/prometheusrule.yaml
   kubectl apply -f k8s/slack-secret.yaml -n observability
   kubectl apply -f k8s/alertmanager-config-slack.yaml -n observability
   ```
   Sample output
   ![kubectl](/images/kubectl.png)
   
   Check that the namespace exists
   
   ```bash
   kubectl get ns
   ```
   Should see: 
 | Name         | Status | Age    |
|--------------|--------|--------|
| observability | Active | 2m14s |

   Review that the deployments are running
   ```bash
   kubectl get deployments -n observability
   ```
   Sample output:
| Name                 | Ready | Up-to-date | Available | Age   |
|----------------------|-------|------------|-----------|-------|
| mongo                | 1/1   | 1          | 1         | 3m20s |
| mongodb-metrics-app | 1/1   | 1          | 1         | 3m7s  |

![Mongo](/images/mongo.png)

   Review pods are up and running
   ```bash
   kubectl get pods -n observability
   ```
   Sample output
| Name                                   | Ready | Status  | Restarts | Age    |
|----------------------------------------|-------|---------|----------|--------|
| mongo-7c94fcd666-wdthz                 | 1/1   | Running | 0        | 4m44s |
| mongodb-metrics-app-5b4c96cbf4-pb2f9   | 1/1   | Running | 0        | 4m31s |

![Pods](/images/pods.png)

Check that the service exists
```bash
kubectl get svc -n observability
```

Expect to see something similar 
| Name                 | Type       | Cluster IP       | External IP | Port(s)     | Age   |
|----------------------|------------|------------------|-------------|-------------|-------|
| mongo-service        | ClusterIP  | 10.104.81.12     | <none>      | 27017/TCP   | 5m35s |
| mongodb-metrics-app | ClusterIP  | 10.103.223.89    | <none>      | 80/TCP      | 5m12s |

![]Service(/images/service.png)

### 4. Install Prometheus, Grafana, and Alertmanager
Execute the following commands
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo update
   helm install prometheus prometheus-community/kube-prometheus-stack --namespace observability --set grafana.enabled=true --set grafana.adminPassword="admin" --wait
   ```
   For helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

   Expect this output 
   "prometheus-community" has been added to your repositories

   For helm repo update
   Expected ouput:
   ```
   Hang tight while we grab the latest from your chart repositories...
   ...Successfully got an update from the "awx-operator" chart repository
   ...Successfully got an update from the "prometheus-community" chart repository
   Update Complete. ⎈Happy Helming!⎈
   ```
   ![Helm](/images/helm1.png)

   For helm install prometheus prometheus-community/kube-prometheus-stack --namespace observability --set grafana.enabled=true --set grafana.adminPassword="admin" --wait

   Expected output
   ```
   waitNAME: prometheus
   LAST DEPLOYED: Sat Nov 22 14:24:07 2025
   NAMESPACE: observability
   STATUS: deployed
   REVISION: 1
   NOTES:
   kube-prometheus-stack has been installed. Check its status by running:
   kubectl --namespace observability get pods -l "release=prometheus"
   ```
   ![Helm](/images/helm2.png)

   Review pods are running:  
   ```bash
   kubectl get pods -n observability 
   ```

You should see something like this :
| Name                                                       | Ready | Status  | Restarts | Age   |
|------------------------------------------------------------|-------|---------|----------|--------|
| alertmanager-prometheus-kube-prometheus-alertmanager-0     | 2/2   | Running | 0        | 2m40s |
| mongo-7c94fcd666-wdthz                                     | 1/1   | Running | 0        | 15m   |
| mongodb-metrics-app-5b4c96cbf4-pb2f9                       | 1/1   | Running | 0        | 15m   |
| prometheus-grafana-7769695b96-sq7dc                        | 3/3   | Running | 0        | 2m49s |
| prometheus-kube-prometheus-operator-79cf766677-pmvwc       | 1/1   | Running | 0        | 2m49s |
| prometheus-kube-state-metrics-7bbd865dd5-skxdg             | 1/1   | Running | 0        | 2m49s |
| prometheus-prometheus-kube-prometheus-prometheus-0         | 2/2   | Running | 0        | 2m38s |
| prometheus-prometheus-node-exporter-zgs25                  | 1/1   | Running | 0        | 2m49s |

### 5. Verify the app is running
   ```bash
   kubectl logs deploy/mongodb-metrics-app -n observability
   ```
Expected output:
```
INFO:mongodb-metrics-app:Starting flask app - connecting to mongodb://mongo-service:27017
 * Serving Flask app 'main'
 * Debug mode: off
INFO:werkzeug:WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8000
 * Running on http://10.244.1.248:8000
INFO:werkzeug:Press CTRL+C to quit
```
![App](/images/app-up.png)

Port-forward to access the metrics endpoint:
```bash
kubectl port-forward svc/mongodb-metrics-app -n observability 8000:80
```
Go to http://127.0.0.1:8000 and you will see
```
✅ MongoDB Metrics Exporter running. Visit /metrics for Prometheus metrics. 
```
Console will show:
![Mongo](/images/mongo-port.png)

Visit
http://127.0.0.1:8000/metrics

You can search for mongodb_up among the logs that are present, if the result is 1.0 everything is correct 

### 6. Port-forward to access Prometheus
   ```bash
   kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n observability 9090:9090
   ```
   You should see in target health like it is being displayed in the image
   ```
   service/monitor/observability/mongodb-metrics-app-sm/0
   ```
![Prometheus](/images/prometheus-scrapping.png)

If you execute mongodb_up in the query you should get data

![Prometheus](/images/prometheus-graph.png)
![Prometheus](/images/prometheus-query.png)

### Port-forward to access Grafana
Review that is running 
```bash
kubectl get pods -n observability | grep grafana
 ```
You should see something like 
| Name                                       | Ready | Status  | Restarts | Age |
|--------------------------------------------|-------|---------|----------|-----|
| prometheus-grafana-7769695b96-sq7dc        | 3/3   | Running | 0        | 57m |

![Grafana](/images/grafana.png)

Execute
```bash
kubectl port-forward svc/prometheus-grafana -n observability 3000:80
 ```
Go to http://localhost:3000/login
use admin as user and password, set a new user and password
Go to Dashboards, new, import dashboard
![Dashboard](/images/dashboard-start.png)
upload the grafana-dashboard.json file or copy paste it in the box click load
![Dashboard](/images/dashboard-import.png)
![Dashboard](/images/dashboard-creation.png)
Click Import and you should the graphs

![Dashboard](/images/dashboard.png)

### Port-forward to access Alert Manager
See that alert manager is up and running 
```bash
kubectl get pods -n observability | grep alertmanager
 ```
Something similar to this should be showed

| Name                                                         | Ready | Status  | Restarts | Age |
|--------------------------------------------------------------|-------|---------|----------|-----|
| alertmanager-prometheus-kube-prometheus-alertmanager-0       | 2/2   | Running | 0        | 96m |

check
```bash
kubectl get prometheusrule -n observability | grep mongo
 ```
Expected output:
mongodb-alerts            

Expose alert manager using port forward
```bash
kubectl port-forward svc/prometheus-kube-prometheus-alertmanager -n observability 9093:9093
 ```
Go to http://localhost:9093


# Slack Alerts
In order to trigger alerts, made the following change in the prometheusrule.yaml
```
rules:
    - alert: MongoDBDown
      expr: vector(1)
      for: 3s
 ```

Save the file and execute 
```
kubectl apply -f k8s/prometheusrule.yaml -n observability
```

If alerts are being triggerd you should see the following in prometheus, alert manager and slack
![Alerts Working](/images/prometheus-alerts.png)
![Alerts Working](/images/alert-manager1.png)
![Alerts Working](/images/slack.png)


