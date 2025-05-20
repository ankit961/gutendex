pipeline {
    agent any
    environment {
        DOCKER_IMAGE = "ankitchauhan961/gutendex-app:latest"
    }
    triggers { githubPush() }

    stages {
        stage('Copy .env from Azure VM') {
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'gutendex-ssh-key',
                    keyFileVariable: 'SSH_KEY',
                    usernameVariable: 'SSH_USER'
                )]) {
                    sh '''
                        scp -i $SSH_KEY -o StrictHostKeyChecking=no $SSH_USER@<YOUR_AZURE_VM_IP>:/home/azureuser/gutendex/.env .
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps { script { docker.build('gutendex-app') } }
        }

        stage('Test Docker Image') {
            steps {
                // run the test suite without an env-file
                // (if tests need specific vars, export them inline here)
                sh 'docker run --rm gutendex-app pytest'
            }
        }

        stage('Push to DockerHub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: '13879567-0459-4f4c-960e-884d1ee91f2e',
                    usernameVariable: 'DOCKERHUB_USER',
                    passwordVariable: 'DOCKERHUB_PASS')]) {
                    sh '''
                        echo "$DOCKERHUB_PASS" | docker login -u "$DOCKERHUB_USER" --password-stdin
                        docker tag gutendex-app $DOCKER_IMAGE
                        docker push $DOCKER_IMAGE
                    '''
                }
            }
        }

        stage('Deploy to Azure VM') {
            when { expression { currentBuild.currentResult == 'SUCCESS' } }
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'gutendex-ssh-key',
                    keyFileVariable: 'SSH_KEY')]) {

                    sh """
                        ssh -i \$SSH_KEY -o StrictHostKeyChecking=no azureuser@135.235.193.30 '
                            docker pull $DOCKER_IMAGE &&
                            docker stop gutendex-app || true &&
                            docker rm   gutendex-app || true &&
                            docker run -d \
                               --env-file /home/azureuser/gutendex/.env \
                               --name gutendex-app \
                               -p 80:8000 \
                               $DOCKER_IMAGE
                        '
                    """
                }
            }
        }
    }
    post { always { cleanWs() } }
}
