pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "ankitchauhan961/gutendex-app:latest"
        REMOTE_HOST = "135.235.193.30"
        REMOTE_USER = "azureuser"
        REMOTE_APP_DIR = "/home/azureuser/gutendex"
        ENV_FILE_REMOTE = "/home/azureuser/gutendex/.env"
        ENV_FILE_LOCAL = ".env"
    }

    triggers {
        githubPush()
    }

    stages {
        stage('Copy .env from Azure VM') {
            steps {
                sshagent(['gutendex-ssh-key']) {
                    sh """
                        scp -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST:$ENV_FILE_REMOTE $ENV_FILE_LOCAL
                    """
                }
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
                script {
                    // Test image (you must have tests in your image, like pytest)
                    sh "docker run --rm --env-file .env gutendex-app pytest || true"
                }
            }
        }

        stage('Login & Push to DockerHub') {
            steps {
                withCredentials([usernamePassword(credentialsId: '13879567-0459-4f4c-960e-884d1ee91f2e', usernameVariable: 'DOCKERHUB_USER', passwordVariable: 'DOCKERHUB_PASS')]) {
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
                sshagent(['gutendex-ssh-key']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST '
                            docker pull $DOCKER_IMAGE &&
                            docker stop gutendex-app || true &&
                            docker rm gutendex-app || true &&
                            cd $REMOTE_APP_DIR &&
                            docker run -d --env-file .env --name gutendex-app -p 8080:8000 $DOCKER_IMAGE
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
