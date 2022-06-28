from scrapli import Scrapli
from scrapli.exceptions import ScrapliException
from concurrent.futures import ThreadPoolExecutor, as_completed


def single_net_connection(hostname, username, password):
    """
    That function connects to a network device thru ssh

    :param hostname: where
    :param username: who
    :param password: how
    :return: it returns parsed 'show cdp neighbors' command output in the form of dicrionary
    """
    connection_params = {
        "host": hostname,
        "auth_username": username,
        "auth_password": password,
        "auth_strict_key": False,
        "platform": "cisco_iosxe",
        "transport": "ssh2"
    }
    host_nei = {hostname: []}
    try:
        with Scrapli(**connection_params) as ssh:
            sh_cdp_nei = ssh.send_command('show cdp neighbors')
            for nei in sh_cdp_nei.textfsm_parse_output():
                if '.tech.invalid' in nei["neighbor"]:
                    host_nei[hostname].append(
                    (nei['neighbor'].lower(),
                    hostname.split('.')[0] + ' - ' +
                    nei['local_interface'],
                    nei['neighbor'].split('.')[0] + ' - ' +
                    nei['neighbor_interface'])
                    )
    except ScrapliException as err:
        host_nei = {hostname: None}
        print('Host', hostname, 'is not available')
        print(err)
    return host_nei


def net_connection(hostips, username, password):
    """
    Multithreading connection to a pool of devices to gather neighbor information
    'show cdp neighbors'

    :param hostips: where to conenct list
    :param username: who
    :param password: how
    :return: it returns a list of dictinaries whith gathered info and from whom gathered
    """
    future_list = []
    nei_dicts = []
    with ThreadPoolExecutor(max_workers=20) as exe:
        for host in hostips:
            future = exe.submit(single_net_connection, host['name'], username, password)
            future_list.append(future)
        for f in as_completed(future_list):
            nei_dicts.append(f.result())
    return nei_dicts

