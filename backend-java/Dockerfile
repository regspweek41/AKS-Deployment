FROM eclipse-temurin:8-jdk-alpine
VOLUME /tmp
EXPOSE 8080
ADD target/*.jar app.jar
ARG APM_JAR=elastic/elastic-apm-agent-1.37.0.jar
COPY ${APM_JAR} elk.jar
ENV JAVA_OPTS=""
ENTRYPOINT [ "sh", "-c", "java -javaagent:elk.jar $JAVA_OPTS  -Delastic.apm.service_name=my-service-name -Delastic.apm.secret_token=aeh1yLP7rIDiKRDHX9 -Delastic.apm.server_url=https://3681141d325e43db8dea1f315201a4c2.apm.eastus2.azure.elastic-cloud.com:443 -Delastic.apm.environment=my-environment -Delastic.apm.application_packages=org.example -Djava.security.egd=file:/dev/./urandom -jar /app.jar" ]
