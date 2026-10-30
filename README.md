# concertpass

## Prerequisitos

Instalar kubectl:

https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/

Instalar eksctl:

https://docs.aws.amazon.com/eks/latest/eksctl/installation.html

Instalar helm:

https://helm.sh/docs/intro/install/

## Cómo correrlo

**1. Crear recursos y publicar imágenes:**
```bash
   export AWS_PAGER=""
   ./scripts/create-rds-instance.sh
   ./scripts/create-sqs.sh
   ./scripts/create-dynamodb-table.sh
   ./scripts/publish-ecr.sh ticket-api
   ./scripts/publish-ecr.sh ticket-worker
   ./scripts/publish-ecr.sh ticket-checkout
```

**2. Crear cluster de EKS y desplega los manifests:**
```bash
   ./scripts/create-eks-cluster.sh
   ./scripts/deploy-k8s.sh
```
La creacion del cluster puede tardar varios minutos.

Al terminar el despliege con ```deploy-k8s.sh``` confirma que los pods de ```ticket-api``` y ```ticket-checkout``` queden con el estado ```Running```:
```bash
   kubectl get pods
   kubectl get services
```

**3. Corre la aplicacion con kubectl:**
```bash
   kubectl port-forward svc/ticket-api 8080:8080
```
En otra terminal, para ticket-checkout:
```bash
   kubectl port-forward svc/ticket-checkout 8081:8080
```

**4. Probar:**

Puedes probar con Postman o con cURL en otra terminal.

**ticket-api:**

```bash
   curl -X POST "http://localhost:8080/reserve" -H "Content-Type: application/json" -d '{"concert_id":"bad-bunny-gdl","user_id":"usr_123","ticket_type":"vip","quantity":2}'
```
Respuesta esperada: reservacion con `"status":"pending"`.

**ticket-checkout:**

```bash
   curl -i -X POST "http://localhost:8081/checkout" -H "Content-Type: application/json" -d '{"reservation_id":"550e8400-e29b-41d4-a716-446655440000","quantity":2}'
```
Respuesta esperada: `HTTP/1.1 200 OK` con `{"status":"success"}`.

**5. Limpiar:** 

`./scripts/teardown.sh`
