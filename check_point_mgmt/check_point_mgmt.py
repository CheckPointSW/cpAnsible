#!/usr/bin/python
import ast
import json
import sys

from ansible.module_utils.basic import AnsibleModule

sys.path.append("/usr/lib/python2.7/site-packages/ansible/modules/extras/check_point_mgmt/")
from mgmt_api_lib import APIClient, APIClientArgs

# arguments for the module:
fields = {
    "command": {
        "required": True,
        "type": "str"
    },
    "parameters": {},
    "session-data": {
        "type": "str"
    },
    "fingerprint": {
        "type": "str"
    }
}

DOCUMENTATION = """
module: check_point_mgmt
short_description: Control a management server via access to the web API.
                   Please read the readme.txt file for more detailed information.
requirements:
  - "2.7.9 <= python < 3.0"
options:
    command:
        description:
          - The command to run on the management server.
        required: true
    session-data:
        description:
          - domain:       Log in to this domain on the management server.
          - management:   IP address of the management server to control.
          - port:         Port to connect through to the management server.
                          Default: 443
          - username:     Username to log in to the management server with.
          - password:     Password to log in to the management server with.
        required: false
    fingerprint:
        description:
          - Fingerprint to verify the server's fingerprint with.
        required: false
"""

EXAMPLES = """
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
      fingerprint: "7D:FE:DE:EE:C7:B9:D0:67:35:E4:C4:16:EC:7A:03:13:48:CD:CA:8D"
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
"""

module = AnsibleModule(argument_spec=fields, supports_check_mode=True)

response = {}
can_publish = True
was_published = False

# Commands that are unable to be run in check mode.
# The module will stop and tell you to add an "always_run: yes" when running in check mode
unavailable_in_check_commands = ["publish", "run-script", "install-policy", "add-domain"]


# Validate the fingerprint of the server with a local one
# If it's validated, assign the API client's fingerprint accordingly
# If not, display an error and exit.
def validate_fingerprint(client, local_fingerprint):
    # If given a fingerprint, save it so we don't have to give it next time
    if local_fingerprint:
        client.save_fingerprint_to_file(client.server, local_fingerprint)
    # If not given a fingerprint, try to read one from a file previously written
    else:
        local_fingerprint = client.read_fingerprint_from_file(client.server)
    # Getting the server's fingerprint
    server_fingerprint = client.get_server_fingerprint()
    if local_fingerprint.replace(':', '').upper() == server_fingerprint.replace(':', '').upper():
        client.fingerprint = local_fingerprint
    else:
        error("Cannot operate on an unverified server. Please verify the server's fingerprint: '"
              + server_fingerprint + "' and add it via the 'fingerprint' option of this module.")


def main():
    global can_publish
    global was_published
    # Initializing parameters to variables:
    command = module.params["command"]
    parameters = module.params["parameters"] if "parameters" in module.params else None
    session_data = module.params["session-data"] if "session-data" in module.params else None
    fingerprint = module.params["fingerprint"] if "fingerprint" in module.params else None
    if parameters:
        parameters = json.loads(parameters.replace("'", '"'))
    if command == "login":
        # Login parameters:
        username = parameters["user"] if "user" in parameters else (
            parameters["username"] if "username" in parameters else None)
        password = parameters["pass"] if "pass" in parameters else (
            parameters["password"] if "password" in parameters else None)
        management = parameters["management"] if "management" in parameters else "127.0.0.1"
        port = parameters["port"] if "port" in parameters else 443
        domain = parameters["domain"] if "domain" in parameters else None
        client_args = APIClientArgs(server=management, port=port)
        client = APIClient(client_args)
        # Validate fingerprint:
        validate_fingerprint(client, fingerprint)
        # Tries to login:
        client.login(username=username, password=password, domain=domain)
        # Building a session data object
        session_data = {
            "url": management + ":" + str(port),
            "domain": domain,
            "sid": client.sid,
            "fingerprint": client.fingerprint
        }
        resp = session_data
    else:
        # Parsing the session-data argument:
        try:
            session_data = ast.literal_eval(session_data)["response"]
        except (ValueError, KeyError):
            if not session_data:
                error("You must specify session-data for commands that are not login (use the command \"login\""
                      " to obtain the session data).")
            else:
                error("session-data variable is invalid.")

        session_id = session_data["sid"]
        domain = session_data["domain"]
        management = session_data["url"].split('//')[1].split('/')[0].split(':')[0] if '//' in session_data["url"] else \
            session_data["url"].split('/')[0].split(':')[0]
        fingerprint = session_data["fingerprint"]
        client_args = APIClientArgs(server=management, sid=session_id)
        client = APIClient(client_args)
        client.domain = domain
        validate_fingerprint(client, fingerprint)

        # Doesn't run commands that act immediately (not waiting for 'publish'), like install-policy, publish, etc.
        if module.check_mode and command in unavailable_in_check_commands:
            error("Can't run the following commands in check mode: " + str(unavailable_in_check_commands) +
                  ". Know that your script ran fine up to this point " +
                  ("and we've discarded the changes made, you can now run it without check mode." if
                   command == "publish" else "and we are skipping this command."),
                  client=client if command == "publish" else None, discard=True, logout=False, exit=True, fail=False)

        # Run the command:
        res = client.api_call(command=command, payload=parameters)

        if not res.success:
            error("Command '" + command + " " + str(
                parameters) + "' failed{}. All changes are discarded and the session is invalidated.".format(
                " with error message: " + str(res.error_message) if hasattr(res, "error_message") else ""),
                  client=client)
            can_publish = False

        resp = res.data
    module.exit_json(response=resp, changed=was_published)


def is_int(_str):
    try:
        int(_str)
        return True
    except ValueError:
        return False


# Errors out nicely in ansible
def error(message, exit=True, fail=True, error_code=1, client=None, discard=True, logout=True):
    if client:
        if discard:
            client.api_call(command="discard")
        if logout:
            client.api_call(command="discard")
            client.api_call(command="logout")
    if exit:
        if fail:
            module.fail_json(changed=was_published, failed=True, msg=message)
        else:
            module.exit_json(response=message, changed=False)
        sys.exit(error_code)


# filling the APIClient with login credentials so it can perform actions that require authorization
def login(client, management, domain=None, username=None, password=None, session_id=None):
    # will use the given session-id to perform actions
    if session_id:
        client.sid = session_id
        client.server = management
        client.domain = domain
        return session_id
    # will try to login using the given username and password
    else:
        login_res = client.login(server=management, user=username, password=password, domain=domain)
        if not login_res.success:
            error("Login failed: {}".format(login_res.error_message))
    return login_res.res_obj["data"]["sid"]


if __name__ == "__main__":
    main()
