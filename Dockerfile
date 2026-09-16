ARG BUILD_IMAGE=docker.io/library/gradle@sha256:92729579a0def4685bb8d772cea499052ad2f7bbc34feac5253b6a379671ff77
ARG BASE_IMAGE=docker.io/library/eclipse-temurin@sha256:ec72ba5962b45ae4e7f96bfb5ebf6eeb34a488b967f937c8e14f0aaec688954f
FROM ${BUILD_IMAGE} AS builder
WORKDIR /build
COPY . .
RUN gradle --no-daemon bootJar
FROM ${BASE_IMAGE}
WORKDIR /app
COPY --from=builder /build/build/libs/fedops-mail-auth-0.0.1-SNAPSHOT.jar /app/fedops-mail-auth.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/fedops-mail-auth.jar"]
