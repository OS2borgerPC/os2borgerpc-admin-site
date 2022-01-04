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


