This directory contains the OS2borgerPC Admin system, which is a remote
administration system for Debian-based GNU/Linux-systems, especially
Ubuntu systems.

The system was originally developed for public libraries in Denmark and
is specifically designed to manage their OS2borgerPC audience audience
desktop PCs.

By design, its functionality aims to be similar to that of Canonical's
Landscape product, but less ambitious. A special feature is security
alerts that may be triggered e.g. if a user changes a USB keyboard (some
libraries have experienced problems with people trying to insert key
loggers between keyboard and computer).

The system was prepared by Magenta: See http://www.magenta.dk

All code is made available under Version 3 of the GNU General Public
License - see the LICENSE file for details.



HOW TO SETUP DEVELOPMENT SERVER
=============================+

This guide describes how to get the admin site up and running for
development purposes, i.e. with no Apache or proxy setup. If you wish to
set up a production environment, please follow the instructions in
doc/HOWTO_INSTALL_SERVER.txt. If you wish to learn to use the system,
please install the server and use the on-site documentation (at present
only available in Danish).

Also check the guide to installing the client and preparing the server
further below.


You should normally be able to  install the development server in  10
minutes or less. An Internet connection is required.

The following instructions should work fine with any modern
GNU/Linux-based operating systems, but they were made with and are at
present only tested under Ubuntu 20.04 LTS Server Edition.



PRE-REQUISITES
++++++++++++++

Python >= 3.6
python3-venv

Get them with apt install


    $ apt install <package_name>


... or by whatever means necessary for your OS.


GRAB THE CODE
+++++++++++++


    $ git clone https://github.com/magenta-aps/bibos_admin.git


GET THE RIGHT BRANCH
++++++++++++++++++++


    $ cd </path/to>/admin_site



    git checkout <desired branch>

This only applies if you're not working directly on the master branch
(which you probably shouldn't). For <desired branch> substitute the branch
you want to work on.


INSTALL DJANGO AND OTHER COMPONENTS
+++++++++++++++++++++++++++++++++++



    $ cd admin_site/scripts && bash install.sh


This requires an Internet connection. It should run its course with a
number of warnings but no errors.


SET UP AND RUN THE DEVELOPMENT SERVER
+++++++++++++++++++++++++++++++++++++

In order to run **post-install-dev.sh** you must activate the virtual environment. 


    $ cd .. && source python-env/bin/activate
    (python-env) user@machine:~/path/to/admin-site/admin_site$

If you choose another HOSTNAME below than 'localhost' then remember to modify the variable
**ALLOWED_HOSTS** in the **.env** file located at 'admin-site/admin_site/bibos_admin/'.
By default Django does not allow access through IP., so don't bother trying to access 
the site through an IP. See Django documentation for more information about this.

In this guide we will assume you're using localhost as HOSTNAME.


    $ bash ./scripts/post-install-dev.sh <USERNAME> <EMAIL> <IP/HOSTNAME> <PORT>


**post-install-dev.sh** sets up and runs the development version of the admin 
system (using a local SQLite database). You'll be prompted for a password for the
new administrative user `USERNAME`.

Now access the site through http://localhost:8080/

In order to login your user needs a 'bibos_profile'.

PATCH THE USER
++++++++++++++

Log on to the admin site's user section, at:

http://localhost:8080/admin/auth/user/

Edit the user you just created. Scroll to the bottom of the site in the section 
*USER PROFILES*. Choose "Super Admin" as the user profile type. Click Save.

ENJOY
+++++

Go to http://localhost:8080 to start using the system - create sites,
create groups, etc. See further explanation below.

NOTE: The system was written in Django and consists of a Django site
with three apps: "account", "system" and "job". Most of the actual
functionality is concentrated in the "system"  app. Some knowledge of
Django is required to understand how the system is designed. Refer to
the graphical object model (BibOS.dia) for an explanation of the site's
object structure.



PREPARE THE ADMIN SYSTEM
========================


Create distribution
+++++++++++++++++++

You need to create a "distribution" in the BibOS Admin system.  This is
done in django-admin.  

The distribution ID needs to be a string with no spaces and preferrably
no special characters. It should reflect the operating system on the
corresponding clients, e.g. "ubuntu12.04".


Create Site 
+++++++++++

You need to create at least one "site" to which you can attach your
clients. The name of the site should describe your location, and the ID
should be a simple, lowercase string with no spaces or special
characters, e.g.  "aarhus".


Finalize the distribution
+++++++++++++++++++++++++

# TODO: This part of the functionality is being phased out and will be 
#       removed in a future version of the system. PCs will no longer
#       upload their package lists to the server, nor will we keep
#       complete listings of packages in the distribution.

This step is to be performed *after* you have registred a computer in the
admin system as described below. To finalize the distribution:

* Create a completely vanilla installation of the operating system you
  wish to define your "distribution", maybe with some additional
  packages which you wish to install on all your computers.

* Register the computer in the admin system as described below.

* When the registration is done, execute the command 

    os2borgerpc_upload_dist_packages

  in a command shell. This will upload the list of installed packages
  and register them as definition of this distribution.

* IMPORTANT: In the admin system's Django settings file, (e.g. in
  admin_system/bibos_admin/settings.py in the installed source code)
  close your distribution by adding its ID to the list
  CLOSED_DISTRIBUTIONS. 


REGISTER A CLIENT COMPUTER
==========================


Install bibos-client package
++++++++++++++++++++++++++++

First, you need to install the BibOS Admin client on the PC you wish to
control from the admin system.

We recommend that you install this from PyPI using pip.

Enter the following commands in a bash shell::

    # If not installed already
    sudo apt-get install python3-pip

    # This is what we want:
    sudo pip install http://bibos-admin.magenta-aps.dk/archive/client_packages/os2borgerpc_client-0.0.5.1.tar.gz

    # TODO: This will be changed when the new client package is on PyPI.


After succesfully installing bibos-client, run the registration script
in order to connect with the admin system. ::

    sudo register_new_os2borgerpc_client.sh


Guide to the steps:

# Do not enter a gateway IP unless you *know* you will be using a gateway.
# Enter a new host name for your computer if you want. If not, your PC
  will be registered with its current name.
# Enter the ID for the site you wish to register the PC on (e.g.
  "aarhus").
# Enter the ID for the distribution (e.g. "ubuntu12.04").
# Enter the URL of your admin system (e.g. "http://localhost:8000" if
  you're a developer or "http://yourdomain.com/your_admin_dir".

The registration will now proceed, and your new PC will show up in the
admin system as "New" in the corresponding site's status list.

In order to start running scripts etc. on the computer, you need to
manually approve it's registration by "activating" it in the admin
system. View the details on the new computer and check the box marked
"Aktiv" or "Active". The PC will now start uploading its package info
and is under the control of the admin system.
