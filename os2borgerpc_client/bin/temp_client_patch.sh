#!/usr/bin/env bash


git_url=https://raw.githubusercontent.com/magenta-aps/os2borgerpc_admin/feature/22059-update/os2borgerpc_client
bin_folder="/usr/local/bin"

sudo curl $git_url/os2borgerpc_client/admin_client.py > /usr/local/lib/python2.7/dist-packages/os2borgerpc_client/admin_client.py
sudo curl $git_url/bin/os2borgerpc_register_in_admin > $bin_folder/os2borgerpc_register_in_admin
sudo curl $git_url/bin/register_new_os2borgerpc_client.sh > $bin_folder/register_new_os2borgerpc_client.sh
