# Copyright (C) 2021 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.
#


# Settings for gunicorn in docker.
import multiprocessing


bind = "0.0.0.0:9999"
workers = multiprocessing.cpu_count() * 2 + 1
accesslog =  "/log/access.log"
errorlog =  "/log/error.log"
worker_tmp_dir = "/dev/shm"
max_requests = 1000
max_requests_jitter = 50
# The IP of the traefik container - if not specified gunicorn
# only trusts x forwarded for coming from 127.0.0.1
forwarded_allow_ips = "127.0.0.1,172.18.0.2"
# Default access log format except showing X forwarded for IP instead of host IP, as the host IP is just traefik's
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
