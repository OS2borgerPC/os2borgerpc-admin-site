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
===============================

This guide describes how to get the admin site up and running for
development purposes. The development site is set up with Docker.


If you wish to learn to use the system, please install the system as
described below and use the on-site documentation (at present only
available in Danish).

You should normally be able to  install the development server in  10
minutes or less. An Internet connection is required.


PRE-REQUISITES
++++++++++++++

Recent versions of Docker and docker-compose.

The current best practice is to install them from the official site
and follow the instructions for your platform: 

    https://docs.docker.com/engine/install/
    https://docs.docker.com/compose/install/


GRAB THE CODE
+++++++++++++


    $ git clone https://github.com/OS2borgerPC/admin-site.git


GET THE RIGHT BRANCH
++++++++++++++++++++


    $ cd </path/to>/admin-site

    $ git checkout <desired branch>

This only applies if you're not working directly on the master branch
(which you probably shouldn't). For <desired branch> substitute the branch
you want to work on.


SET UP AND RUN THE DEVELOPMENT SERVER
+++++++++++++++++++++++++++++++++++++

As above, go to the root of the repository:

    $ cd cd </path/to>/admin-site
    $ docker-compose up --build

This will run the site in the foreground. If you wish to run the site in
the background, give the ``-d`` option:

    $ docker-compose up --build -d


Out of the box, the development server will contain one user called
``magenta``, with password ``magenta``.

Likewise, the will be one "site", also called "Magenta".


Create distribution
+++++++++++++++++++

# TODO: This part of the functionality is being phased out and will be 
#       removed in a future version of the system. PCs will no longer
#       upload their package lists to the server, nor will we keep
#       complete listings of packages in the distribution.

You need to create a "distribution" in the  Admin system.  This is
done in django-admin.  

The distribution ID needs to be a string with no spaces and preferrably
no special characters. It should reflect the operating system on the
corresponding clients, e.g. "ubuntu22.04".



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


Install os2borgerpc-client package
++++++++++++++++++++++++++++

First, you need to install the OS2borgerPC Admin client on the PC you wish to
control from the admin system.

We recommend that you install this from PyPI using pip.

Enter the following commands in a bash shell::

    # If not installed already
    sudo apt-get install python3-pip

    # This is what we want:
    sudo pip3 install os2borgerpc-admin


After succesfully installing os2borgerpc-client, run the registration script
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
"Aktiv" or "Active". Next time the OS2borgerPC ``jobmanager`` is run on
the PC, normally within five minutes, the PC will be under the control of
the admin system and you will be able to execute scripts on it.
