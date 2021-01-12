# Copyright (C) 2021 Magenta ApS, http://magenta.dk.
# Contact: info@magenta.dk.
#

################################################################################
# Changes to this file requires approval from Labs. Please add a person from   #
# Labs as required approval to your MR if you have any changes.                #
################################################################################


# Settings for gunicorn in docker.
import multiprocessing


bind = "0.0.0.0:9999"
workers = multiprocessing.cpu_count() * 2 + 1
accesslog =  "/log/access.log"
errorlog =  "/log/error.log"
worker_tmp_dir = "/dev/shm"


