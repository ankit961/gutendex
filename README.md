

# Gutendex API

##  Overview

Gutendex is a modern, scalable API service that exposes a RESTful interface for querying books, authors, and subjects—mirroring Project Gutenberg’s public domain eBooks metadata—built on [FastAPI](https://fastapi.tiangolo.com/), backed by a PostgreSQL database.
It’s fully containerized, with a robust CI/CD pipeline powered by Jenkins and Docker, deployed on Azure VM.
**No Docker Compose is used in production for explicit control and separation of concerns.**

---

##  Features

* **REST API** for querying books, authors, download counts, and more.
* **FastAPI** backend for high-performance, async requests.
* **PostgreSQL** as the database.
* **CI/CD**: Automated testing, building, and deployment with Jenkins.
* **Dockerized**: Consistent environments across local/dev/prod.
* **Configurable**: All secrets and configs via `.env` file.

---

##  Technology Stack

* **FastAPI** (Python 3.9)
* **SQLAlchemy** (ORM)
* **PostgreSQL** (DB)
* **Docker** (Containerization)
* **Jenkins** (CI/CD)
* **Azure VM** (Deployment)
* **Docker Hub** (Image Registry)
* **pytest** (Testing)

---

## Architecture & Deployment Flow

### High-Level Architecture

```mermaid
flowchart TD
    User([User / Client])
    API["Gutendex API (FastAPI in Docker)"]
    DB[(PostgreSQL Database)]
    Env[.env Config File]
    Jenkins[Jenkins CI/CD Server]
    DockerHub[(Docker Hub Registry)]
    AzureVM[(Azure VM)]

    User -- HTTP Request --> API
    API -- SQL Query --> DB
    API -- Reads env vars --> Env
    Jenkins -- Push --> DockerHub
    Jenkins -- Deploy SSH --> AzureVM
    AzureVM -- Runs Docker Container --> API
    API -- Docker Image --> DockerHub

    classDef infra fill:#e5f3ff,stroke:#0072c6
    class AzureVM,DB infra
    classDef cicd fill:#fff0f6,stroke:#b8005d
    class Jenkins cicd


```

### System Flow

1. **User** sends an HTTP request to the `/books` endpoint.
2. **FastAPI app** (inside Docker) receives the request and reads configuration from `.env`.
3. The app queries **PostgreSQL** for matching books/authors.
4. **Jenkins** automates building, testing, and deployment:

   * Pulls latest code from GitHub.
   * Copies latest `.env` from Azure VM (for secure config).
   * Builds Docker image and runs tests.
   * Pushes image to Docker Hub.
   * SSHes to Azure VM, pulls latest image, restarts the container (using real `.env`).

### Why Not Docker Compose?

* **Production practice**: Compose is excellent for local dev or multi-service prototyping, but for production, explicit Docker commands give more control and transparency.
* **Separation of Concerns**: Database and API managed independently; PostgreSQL can be managed by systemd, cloud, or external PaaS.
* **CI/CD pipeline**: Jenkins manages each deployment step explicitly, ensuring repeatable, auditable releases.

---

## 🧑‍💻 API Endpoints

| Endpoint      | Description                   |
| ------------- | ----------------------------- |
| `/books`      | List/query books with filters |


All endpoints return JSON.
See `/docs` (Swagger UI) or `/redoc` for live API docs when running.

---

## ⚙️ Configuration

All sensitive values (DB connection, keys) are stored in a `.env` file (never committed to git):

```ini
DATABASE_URL=postgresql://<user>:<password>@<server>:5432/<db>
LLM_MODEL_PATH=/path/to/model  # Example only if your API loads a model
SECRET_KEY=your_secret
DEBUG=True
```

**Copy your .env from your VM to the Jenkins workspace before build, as in the CI/CD script.**

---

## Running Locally

1. **Prerequisites:**

   * Python 3.9
   * Docker
   * PostgreSQL running and accessible (can be remote)

2. **Clone and setup:**

   ```sh
   git clone https://github.com/ankit961/gutendex.git
   cd gutendex
   cp .env.example .env  # or copy your real .env here
   ```

3. **Build Docker image:**

   ```sh
   docker build -t gutendex-app .
   ```

4. **Run Docker container:**

   ```sh
   docker run --rm --env-file .env -p 8000:8000 gutendex-app
   ```

   Access the API at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🚦 CI/CD Pipeline (Jenkins)

**Pipeline stages:**

1. **Checkout code** from GitHub.
2. **Copy .env** from Azure VM.
3. **Build Docker image** (`docker build`).
4. **Run tests** inside container (`pytest`).
5. **Push to Docker Hub.**
6. **SSH to Azure VM**, pull latest image, stop old container, start new one with `.env`.

**Sample Jenkinsfile (snippet):**

```groovy
stage('Copy .env from Azure VM') {
    steps {
        sshagent(['azureuser-ssh-key']) {
            sh "scp -o StrictHostKeyChecking=no azureuser@<AZURE_VM_IP>:/home/azureuser/gutendex/.env .env"
        }
    }
}
...
stage('Build Docker Image') {
    steps {
        script { docker.build("gutendex-app") }
    }
}
...
stage('Deploy to Azure VM') {
    steps {
        sshagent(['azureuser-ssh-key']) {
            sh '''
                ssh -o StrictHostKeyChecking=no azureuser@<AZURE_VM_IP> '
                    docker pull ankitchauhan961/gutendex-app:latest &&
                    docker stop gutendex-app || true &&
                    docker rm gutendex-app || true &&
                    cd /home/azureuser/gutendex &&
                    docker run -d --env-file .env --name gutendex-app -p 8000:8000 ankitchauhan961/gutendex-app:latest
                '
            '''
        }
    }
}
```

---

## 🩺 Troubleshooting

**Common Issues & Fixes:**

### Database Connection Issues

* **Connection refused**

  * Is Postgres running? `sudo systemctl status postgresql`
  * Can you connect via `psql`?

    ```sh
    psql "postgresql://user:pass@host:5432/db"
    ```
  * Check `listen_addresses` in `postgresql.conf` (should be `'*'` for external connections).
  * Add Docker network IPs to `pg_hba.conf`, e.g.:

    ```
    host all all 172.17.0.0/16 md5
    ```

    Then reload Postgres:

    ```sh
    sudo systemctl reload postgresql
    ```

* **No pg\_hba.conf entry**

  * Ensure the Docker bridge subnet (e.g., `172.17.0.0/16`) is allowed in `pg_hba.conf`.

* **Host resolution errors**

  * Use **actual VM IP** (e.g., `10.2.0.5` or `localhost` if API & DB run on same machine), not `host.docker.internal` unless using Docker for Mac/Windows.

### Port Already in Use

* Another process is running on 8000/80.
* Free the port:

  ```sh
  sudo lsof -i :8000
  sudo kill <pid>
  ```

### Docker Daemon Permission

* If you see `permission denied while trying to connect to the Docker daemon socket`:

  * Add your user to the docker group:

    ```sh
    sudo usermod -aG docker azureuser
    ```
  * Reboot or re-login.

### Container Debugging

* Check logs:

  ```sh
  docker logs <container-id>
  ```
* Get shell:

  ```sh
  docker exec -it <container-id> /bin/bash
  ```

---

## 🔒 Security Best Practices

* **Never commit your `.env` file** to version control.
* Always use strong DB passwords.
* Use firewalls to restrict DB access to the VM only.
* Rotate SSH keys and credentials regularly.

---

##  FAQ

**Q: Can I run everything with Docker Compose?**
*A: You could for local development, but for production, we keep DB and API management separate for security and stability. Explicit `docker run` commands are used in deployment scripts for full control and better troubleshooting.*

**Q: How do I add new environment variables?**
*A: Add them to the `.env` file, update your code to read them via Pydantic/`os.environ`, and re-deploy.*

---
