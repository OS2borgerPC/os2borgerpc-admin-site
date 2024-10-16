"""
WSGI config for OS2borgerPC admin project.

This module contains a WSGI application to run cron jobs.
"""

import subprocess
import uuid
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def application(environ, start_response):
    path = environ.get('PATH_INFO', '/')

    job_routes = {
        '/jobs/check_notifications': 'check_notifications',
        '/jobs/clean_up_database': 'clean_up_database',
    }
    command = job_routes.get(path, None)
        
    if command:
        error = run(command)
        if error:
            trace_id = str(uuid.uuid4())
            logging.error(f"Error occured (trace ID '{trace_id}')\n{error}")
            response, status = (f"An internal server error occured. The error has been logged with trace ID '{trace_id}'.", "500 Internal Server Error")
        else:
            response, status = ("", "200 OK")
    else:
        response, status = "Not found", "404 Not Found"

    start_response(status, [("Content-Type", "text/plain")])
    return iter([response.encode("utf-8")])

        
def run(command):
    try:
        subprocess.run(['python', 'manage.py', command], check=True, text=True, capture_output=True)
        return None
    except subprocess.CalledProcessError as e:
        return "Internal server error: " + e.stderr.strip() if e.stderr else 'An error occurred without stderr output.'