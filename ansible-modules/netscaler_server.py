#!/usr/bin/python
# -*- coding: utf-8 -*-

# TODO review status and supported_by when migrating to github
ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'commiter',
                    'version': '1.0'}


# TODO: Add appropriate documentation
DOCUMENTATION = '''
---
module: netscaler_server
short_description: Manage server configuration
description:
    - Manage server configuration
    - This module is intended to run either on the ansible  control node or a bastion (jumpserver) with access to the actual netscaler instance

version_added: 2.2.3
options:
    name:
        description:
            - Name for the server.
            - "Must begin with an ASCII alphabetic or underscore (_) character, and must contain only ASCII alphanumeric, underscore, hash (#), period (.), space, colon (:), at (@), equals (=), and hyphen (-) characters."
            - Can be changed after the name is created.
            - Minimum length = 1

    ipaddress:
        description:
            - IPv4 or IPv6 address of the server. If you create an IP address based server, you can specify the name of the server, instead of its IP address, when creating a service. Note. If you do not create a server entry, the server IP address that you enter when you create a service becomes the name of the server.
            
extends_documentation_fragment: netscaler
requirements:
    - nitro python sdk
'''

# TODO: Add appropriate examples
EXAMPLES = '''
- name: Connect to netscaler appliance
    local_action:
        nsip: 172.18.0.2
        nitro_user: nsroot
        nitro_pass: nsroot
        ssl_cert_validation: no

        module: netscaler_server
        operation: present

        name: vserver1
        ipaddress: 192.168.1.1
'''

# TODO: Update as module progresses
RETURN = '''
loglines:
    description: list of logged messages by the module
    returned: always
    type: list
    sample: ['message 1', 'message 2']

msg:
    description: Message detailing the failure reason
    returned: failure
    type: str
    sample: "Action does not exist"

diff:
    description: List of differences between the actual configured object and the configuration specified in the module
    returned: failure
    type: dict
    sample: { 'targetlbvserver': 'difference. ours: (str) server1 other: (str) server2' }
'''

from ansible.module_utils.basic import AnsibleModule
import StringIO


def main():
    from ansible.module_utils.netscaler import ConfigProxy, get_nitro_client, netscaler_common_arguments, log, loglines
    try:
        from nssrc.com.citrix.netscaler.nitro.resource.config.basic.server import server
        from nssrc.com.citrix.netscaler.nitro.exception.nitro_exception import nitro_exception
        python_sdk_imported = True
    except ImportError as e:
        python_sdk_imported = False

    module_specific_arguments = dict(
        name=dict(type='str'),
        ipaddress=dict(type='str'),
    )

    argument_spec = dict()

    argument_spec.update(netscaler_common_arguments)

    argument_spec.update(module_specific_arguments)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    module_result = dict(
        changed=False,
        failed=False,
        loglines=loglines,
    )

    # Fail the module if imports failed
    if not python_sdk_imported:
        module.fail_json(msg='Could not load nitro python sdk')

    # Fallthrough to rest of execution

    client = get_nitro_client(module)
    client.login()


    # Instantiate Server Config object
    readwrite_attrs = ['name', 'ip', 'ipaddress']
    readonly_attrs = []
    equivalent_attributes = {
        'ip': ['ipaddress',]
    }

    server_proxy = ConfigProxy(
        actual=server(),
        client=client,
        attribute_values_dict=module.params,
        readwrite_attrs=readwrite_attrs,
        readonly_attrs=readonly_attrs,
    )

    def server_exists():
        if server.count_filtered(client, 'name:%s' % module.params['name']) > 0:
            return True
        else:
            return False

    def server_identical():
        if server.count_filtered(client, 'name:%s' % module.params['name']) == 0:
            return False
        server_list = server.get_filtered(client, 'name:%s' % module.params['name'])
        if server_proxy.has_equal_attributes(server_list[0]):
            return True
        else:
            return False

    def diff_list():
        return server_proxy.diff_object(server.get_filtered(client, 'name:%s' % module.params['name'])[0]),


    try:

        # Apply appropriate operation
        if module.params['operation'] == 'present':
            if not server_exists():
                if not module.check_mode:
                    server_proxy.add()
                    server_proxy.update()
                    client.save_config()
                module_result['changed'] = True
            elif not server_identical():
                if not module.check_mode:
                    server_proxy.update()
                    client.save_config()
                module_result['changed'] = True
            else:
                module_result['changed'] = False

            # Sanity check for result
            if not module.check_mode:
                if not server_exists():
                    module.fail_json(msg='Server does not seem to exist', **module_result)
                if not server_identical():
                    module.fail_json(
                        msg='Server is not configured according to parameters given',
                        diff=diff_list(),
                        **module_result
                    )

        elif module.params['operation'] == 'absent':
            if server_exists():
                if not module.check_mode:
                    server_proxy.delete()
                    client.save_config()
                module_result['changed'] = True
            else:
                module_result['changed'] = False

            # Sanity check for result
            if not module.check_mode:
                if server_exists():
                    module.fail_json(msg='Server seems to be present', **module_result)

        module_result['actual_attributes'] = server_proxy.get_actual_rw_attributes()
    except nitro_exception as e:
        msg = "nitro exception errorcode=" + str(e.errorcode) + ",message=" + e.message
        module.fail_json(msg=msg, **module_result)

    client.logout()

    module.exit_json(**module_result)

if __name__ == "__main__":
    main()
