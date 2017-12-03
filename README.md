# Ansible Module - check_point_mgmt by Check Point®

Installation instructions
-------------------------
1. Clone the repository with this command:
```git
git clone --recursive https://github.com/CheckPoint-APIs-Team/cpAnsible
```
or by clicking the Download ZIP button. In this case, the "cp_mgmt_api_python_sdk" folder will be created empty and you will need to manually download and copy the [Check Point API Python SDK](https://github.com/CheckPoint-APIs-Team/cpapi-python-sdk) content into this folder.  
2. [Install Ansible.](http://docs.ansible.com/ansible/intro_installation.html)  
3. [Install a Python interpreter with version >= 2.7.9, but not Python 3 or above.](https://www.python.org/downloads/)
4. In your `/etc/ansible/ansible.cfg` file, there is a `library` line, uncomment it and set it to be whatever you want, this will be your library folder for modules.
5. Move the `check_point_mgmt` folder to your library folder.  
6. Move the `cp_mgmt_api_python_sdk` directory from the `check_point_mgmt` directory, into `/usr/lib/python2.7/site-packages`  
7. Edit `/etc/ansible/hosts` so that it would contain a section similar to this one:  

```sh
[localhost]
127.0.0.1
[localhost:vars]
ansible_user=[a username with SSH access to the ansible server, not the Check Point server]
ansible_ssh_pass=[password]
ansible_python_interpreter=[path to the Python installation (>=2.7.9 and < 3.0) on the Ansible server]
# Optional (variables detailing the Check Point's management server access):
mgmt_server=[management server's IP address. In case of a multi-domain setup, provide the IP address of the MDS]
mgmt_user=[Check Point admin username]
mgmt_password=[Check Point admin password]
```

Usage
-----

Run a playbook:
```sh
ansible-playbook your_ansible_playbook.yml
```
or

Run a playbook in "check mode":
```sh
ansible-playbook -C your_ansible_playbook.yml
```

Before connecting to a Check Point management server for the first time, follow the instructions in step #4.
Otherwise, an "unverified server" error could appear.


Description
-----------
This Ansible module provides control over a Check Point management server using
Check Point's web-services APIs.
The web-services API reference can be found here:
https://community.checkpoint.com (under "Developer Network > API Reference > Web Services").

A typical ansible command in a playbook should look like this:
  ```yaml
  - name: "adding a demo host"
    check_point_mgmt:
      command: add-host                     # web-service command name.
      parameters:                           # The web-service request arguments.
                                            # Note that the API web-services samples use JSON format.
                                            # Ansible requires these arguments to use YAML format.
        name: "host_demo2"
        ip-address: "1.2.3.5"
      session-data: "{{ login_response }}"  # where {{ login_response }} is received from
                                            # the login command that was called previously.
                                            # This replaces the need for the HTTP
                                            # headers that are mentioned in the API reference.
  ```
###  Notes:

  1. Because this Ansible module is controlling the management server remotely via the web API, 
     the ansible server needs to have access to the Check Point API server.
     Open `SmartConsole`, navigate to "Manage & Settings > Blades > Management API > Advanced settings"
     and check the API server's accessibility settings.

  2. The ansible "hosts" field in the playbook should refer to the Ansible machine (i.e. 127.0.0.1),
     there is no need to ssh to the management server, the commands are sent to the management server
     as API web-service requests.

  3. Asynchronous commands - A few Check Point APIs run asynchronously, 
     for example: publish, install-policy and run-script.
     By default, all commands in an ansible playbook will run synchronously.
     In other words, the ansible playbook will wait as much time as needed for 
     the command to complete, before moving to the next command.
     If you need to override this default behavior and run the command in asynchronous manner,
     use Ansible's "async: <timeout_in_seconds>" option, for more info:
     http://docs.ansible.com/ansible/playbooks_async.html

  4. Ansible has a feature called "Check Mode" that enables you to test the
     changes without actually changing anything.
     When running in Ansible's "check mode", calling Check Point's "publish" API
     would actually call Check Point's "discard" API.
     This would allow you to test your script without making changes in the Check Point
     database and without keeping objects in the database locked.
     In this mode, the "install-policy", "run-script" and "add-domain" APIs will be skipped.
  5. Logout - The last task in your playbook should typically be `logout`, to cleanly close the session, unless you intend otherwise. Simple example:  
  ```yaml
  - name: logout
    check_point_mgmt:
      command: logout
      session-data: '{{login_response}}'
  ```


Every communication with the Check Point server must start with a "login" command.
The login command takes some parameters that are not listed in the API reference,
The list of the parameters login takes can be seen in the [options](#options) section:
```
Example of a login task:
```yaml
- name: "login task"
  check_point_mgmt:
    command: login
    parameters:
      username: user1
      password: pass1
      management: 192.168.1.193
    fingerprint: "7D:FE:DE:EE:C7:B9:D0:67:35:E4:C4:16:EC:7A:03:13:48:CD:CA:8D"
  register: login_response    # Register the output from the login command so
                              # it can later be used by subsequent commands.
```

You must add Ansible's "register" field to the Login task so that other management APIs could
continue that session.

```yaml
  - name: "adding a demo host"
    check_point_mgmt:
      command: add-host                     # web-service command name.
      parameters:                           # The web-service request arguments.
                                            # Note that the API web-services samples use JSON format.
                                            # Ansible requires these arguments to use YAML format.
        name: "host_demo2"
        ip-address: "1.2.3.5"
      session-data: "{{ login_response }}"  # The session data we received from
                                            # the login command is used here.
                                            # This replaces the need for the HTTP
                                            # headers that are mentioned in the API reference.
```

Before communicating with a Check Point management server for the first time
----------------------------------------------------------------------------

   To keep the connection secure, the ansible server should trust the Check Point
   server certificate.
   In a typical deployment, the Check Point server is using a self-signed
   certificate (that should not to be trusted).

   In order to make the ansible server trust the Check Point certificate, follow these steps:
   1. Use console access, or some other means of trusted communication to 
      log into the Check Point server.
   2. On the Check Point server, run "api fingerprint".
      a typical response, should look like this:
      ```
      Fingerprint:
      SHA1: 7E:FF:DE:CE:C7:B9:D0:67:35:E4:C4:16:EC:7A:03:13:48:CD:CA:8D
      Using English words: FARM WAND MIMI GOWN HURD PHI QUO LOY BAH SEES JADE GAUL
      ```
   3. Copy the SHA1 fingerprint and pass it as an argument to the check_point_mgmt
      module in the first task of your playbook (login).
      Example:
      ```yaml
      - name: "login task"
        check_point_mgmt:
          command: login
          parameters:
            username: user1
            password: pass1
            management: 192.168.1.123
          fingerprint: "7E:FF:DE:CE:C7:B9:D0:67:35:E4:C4:16:EC:7A:03:13:48:CD:CA:8D"
        register: login_response
      ```
      Note:
      After you do this once and run the playbook, the fingerprint will be saved
      in a fingerprints.txt file in the current working directory, so there is no
      need to do this procedure again, unless you move the playbook file.



Requirements
------------
* The Check Point server should be using R80 or above
* The Check Point server should be open for API communication from the ansible server.
  Open SmartConsole ans check "Manage & Settings > Blades > Management API > Advanced settings".
* The Ansible server's Python version should be 2.7.9 or higher (but not Python 3).



Options
-------
**command** - the command to run on the management server (Required)  
**parameters** - The parameters for the command (given as a dictionary - key: value)  
**fingerprint** - Fingerprint to verify the server's fingerprint with (Unncesseray to give this after the login task as it is stored in *session-data*).  
**session-data** - After logging in, use this variable to give the output of the login command, including details such as the session id, the management server's IP and port, the domain to log into, and the fingerprint.  

### Special case for the command 'login':

### parameters:
  management - IP address of the management server to control.  
  domain - Log in to this domain on the management server.  
  port - Port to connect through to the management server (Default: 443).  
  username - Check Point admin username  
  password - Check Point admin password  


Example playbook
----------------
```yaml
---
- hosts: "localhost"                        # Note #2 in the Description section
  tasks:
  - name: "login"                           # You have to login to the management
                                            # server before running any commands
    check_point_mgmt:
      command: login
      parameters:
        username: "{{mgmt_user}}"           # Variables set in /etc/ansible/hosts, to avoid needing
        password: "{{mgmt_password}}"       # to type your login details in every playbook.
        management: "{{mgmt_server}}"
      fingerprint: "C3:B4:54:8D:0E:C0:7E:D4:31:64:94:13:F5:14:CD:93:68:6A:4F:4D"
    register: login_response                # Register the output from the login
                                            # command so we can use it later to run commands.
  - name: "add host"
    check_point_mgmt:
      command: add-host                     # Name of the command
      parameters:                           #  The parameters for it, in dictionary form
        name: "host_demo"
        ip-address: "1.2.3.5"
      session-data: "{{ login_response }}"  # The session data we received from
                                            # the login command is used here to run 'add-host'
  - name: "add group"
    check_point_mgmt:
      command: add-group
      parameters:
        name: "group_demo"
        members:
          - "host_demo"
      session-data: "{{ login_response }}"
  - name: "publish"                         # Publishing is important if you want
                                            # your changes to be saved.
    check_point_mgmt:                       # This will actually 'discard' when
                                            # check mode is enabled (ansible-playbook -C)
                                            # unless you add 'always_run: yes' to the task.
      command: publish
      session-data: "{{login_response}}"
```
