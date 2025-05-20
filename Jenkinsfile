pipeline {
    agent any

    triggers {
        githubPush()  // triggers the build on every GitHub push event
    }

    environment {
        DOCKER_IMAGE = "ankitchauhan961/gutendex-app:latest"
        VM_HOST = "135.235.193.30"
        VM_USER = "azureuser"
        VM_APP_DIR = "/home/azureuser/gutendex"
        SSH_KEY_ID = "gutendex-ssh-key"
    }

    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/ankit961/gutendex.git'
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("gutendex-app")
                }
            }
        }
        stage('Test Docker Image') {
            steps {
                sh "docker run --env-file .env gutendex-app pytest"
            }
        }
        stage('Login & Push to DockerHub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: '13879567-0459-4f4c-960e-884d1ee91f2e',
                    usernameVariable: 'DOCKERHUB_USER',
                    passwordVariable: 'DOCKERHUB_PASS'
                )]) {
                    sh """
                        echo "$DOCKERHUB_PASS" | docker login -u "$DOCKERHUB_USER" --password-stdin
                        docker tag gutendex-app $DOCKER_IMAGE
                        docker push $DOCKER_IMAGE
                    """
                }
            }
        }
        stage('Deploy to Azure VM') {
            steps {
                sshagent (credentials: [env.SSH_KEY_ID]) {
                    sh """
                        ssh -o StrictHostKeyChecking=no $VM_USER@$VM_HOST '
                        docker pull $DOCKER_IMAGE && \
                        (docker stop gutendex-app || true) && (docker rm gutendex-app || true) && \
                        cd $VM_APP_DIR && \
                        docker run -d --env-file .env -p 8000:8000 --name gutendex-app $DOCKER_IMAGE
                        '
                    """
                }
            }
        }
    }
    post {
        always {
            cleanWs()
        }
    }
}
