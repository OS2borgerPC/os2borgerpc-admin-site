# Monitoring OS2BorgerPC admin-site

There are various ways of monitoring the application, som are:
1) health check
2) viewing logs
3) viewing resource usage

Below are examples on how this can be done for the provided docker-compose testing setup that can be used as inspiration.

## Health check
This section in the compose.yaml shows how to implement a health check for a docker-compose setup.
```
restart: always
healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9999"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 5s
```

## Viewing logs
```
docker logs bpc_admin_site_django
```

## Viewing resource usage
```
docker stats bpc_admin_site_django
```