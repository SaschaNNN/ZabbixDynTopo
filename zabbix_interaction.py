from pyzabbix import ZabbixAPI, api
from urllib import error


def connect_to_Zabbix(zabbix_url, username, password):
    """
    That function creates a coonection to Zabbix

    :param zabbix_url: Zabbix API link
    :param username:
    :param password:
    :return: authorized connection object
    """
    try:
        connection = ZabbixAPI(zabbix_url, user=username, password=password)
    except error.URLError as te:
        print('No connection: ', te)
    except ValueError as ve:
        print('Bad url: ', ve)
    except api.ZabbixAPIException as ruop:
        print('Wrong username or password: ', ruop)
    else:
        return connection
    return False


def discovered_zabbix_hosts(connection, group_name):
    """
    That function leverages connection and host's groupname
     to get list of hosts with its hostid, ip, name

    :param connection: authorized connection object
    :param group_name: Zabbix group with discovered hosts
    :return: list of dictinaries with hosts and its parameters (hostid, ip, name)
    """
    try:
        groupid = connection.hostgroup.get(output='groupid', filter={'name': [group_name]})[-1]['groupid']
    except IndexError as ie:
        print('Wrong group: ', ie)
    else:
        hosts = connection.host.get(output=['name', 'hostid'], groupids=[groupid])
        for host in hosts:
            hostip = connection.hostinterface.get(output=['ip'], hostids=[host['hostid']])
            host.update({'ip': hostip[0]['ip'], 'name': host['name'].lower()})
        return hosts
    return 'No data returned'


def map_creation(connection, amount_of_hosts, map_name):
    """
    That function checks if mentioned map exists,
    if not it creates a map with mentioned name and size.
    It returns sysmapid given by Zabbix server

    :param connection: authorized connection object
    :param amount_of_hosts: amount of hosts need to put on the map
    :param map_name: custom map name
    :return: id of the map and its size
    """
    create_map_needed = False
    if amount_of_hosts < 10:
        x = 800
        y = 600
    elif amount_of_hosts < 25:
        x = 2000
        y = 1200
    else:
        x = 4000
        y = 2000
    maps = connection.map.get(output=['name'])
    for zmap in maps:
        if zmap['name'] == map_name:
            create_map_needed = False
            sysmapid = zmap['sysmapid']
            break
        else:
            create_map_needed = True
    if create_map_needed:
        connection.map.create(name=map_name, width=x, height=y)
        maps = connection.map.get(output=['name'])
        for zmap in maps:
            if zmap['name'] == map_name:
                sysmapid = zmap['sysmapid']
    return sysmapid, x, y


def add_elements_to_map(connection, hosts, sysmapid, x, y):
    """
    That function add on the map hosts. Host with ds1 (core switch in our company)
    it puts in the center of the map, other switches around it.
    It returns Zabbix host id map element id mapping.

    :param connection: authorized connection object
    :param hosts: list of dictinaries with hosts and its parameters
    :param sysmapid: id of the map where we put hosts
    :param x: x-axis length
    :param y: y-axis length
    :return: mapping of host id and element id on the map
    """
    elements_to_add = []
    exising_hosts = []
    added_hosts = []
    existing_elem_host_id = connection.map.get(filter={'sysmapid': sysmapid},
                                      selectSelements='extend')
    for element in existing_elem_host_id[0]['selements']:
        exising_hosts.append({'hostid': element['elements'][0]['hostid'], 'selementid': element['selementid']})

    def _add_to_map(hostid, x, y):
        if hostid in [host['hostid'] for host in exising_hosts]:
            pass
        else:
            elements_to_add.append({'elements': [{'hostid': hostid}],
                                    'elementtype': '0',
                                    'iconid_off': '152',
                                    'x': f'{x}',
                                    'y': f'{y}',
                                    'label': '{HOSTNAME}\r\n{HOST.CONN}'})


    i = j = k = 0
    for host in hosts:
        if 'ds1' in host['name']:
            _add_to_map(host['hostid'], x // 2, y // 2)
            continue
        else:
            if i < x*0.9 and j == 0 and k < 8:
                i += x // 10
                _add_to_map(host['hostid'], i, j)
            elif i >= x*0.9 and j <= y*0.8:
                j += y // 10
                _add_to_map(host['hostid'], 0, j)
            elif i <= x*0.9 and j >= y*0.8:
                i -= x // 10
                _add_to_map(host['hostid'], i, j)
            else:
                j -= x // 10
                _add_to_map(host['hostid'], x, j)
    if elements_to_add:
        connection.map.update(sysmapid=sysmapid, selements=elements_to_add)
        host_id_elem_id = connection.map.get(filter={'sysmapid': [sysmapid]},
                                             output=['elements', 'selementid'],
                                             selectSelements=["elements", "selementid"])
        for selem in host_id_elem_id[0]['selements']:
            added_hosts.append({'hostid': selem['elements'][0]['hostid'], 'selementid': selem['selementid']})
        return added_hosts
    print('No new hosts')
    return exising_hosts


def add_elem_id_to_hosts(hosts, elements):
    """
    That function add to hosts lists memebers (dicts) 1 more parameter elementid on the map.

    :param hosts: list of dictinaries with hosts and its parameters (hostid, ip, name)
    :param elements:  mapping of host id and element id on the map
    :return: list of dictinaries with hosts and its parameters (hostid, ip, name, selementid)
    """
    for host in hosts:
        for elem in elements:
            if elem['hostid'] == host['hostid']:
                host.update({'selementid': elem['selementid']})
    return hosts


def topo_links(nei_dicts, host_elem_mapping):
    """
    That function takes nighborhood relationships in form of
    list of dictionaries where key is an every switch\router and
    value is a list of tuples (nighbor, local_link, neighbor_link)
    [{'roch-ss3.tech.invalid': [('roch-ds1.tech.invalid',
                             'roch-ss3 - Ten 1/0/2',
                             'ROCH-DS1 - Ten 6/11'),
                            ('roch-ds1.tech.invalid',
                             'roch-ss3 - Ten 1/0/1',
                             'ROCH-DS1 - Ten 5/11')]},...]

    :param nei_dicts: dict of the neighbors of hosts (switches\routers)
    :param host_elem_mapping: hosts with elementid (id on the map)
    :return: links need to add on the map in the form of a list element id 1 on the map
    element id 2 on the map and interfaces in the description
    """
    host_mapping = []
    host_mapping_existing = []
    host_mapping_not_existing = []
    for dev in host_elem_mapping:
        for nei_dict in nei_dicts:
            for loc_dev, nei_param in nei_dict.items():
                if loc_dev == dev['name']:
                    if type(nei_param) == list:
                        for nei in nei_param:
                            host_mapping.append([dev['selementid'], nei[0], nei[1], nei[2]])
                    elif nei_param:
                        host_mapping.append([dev['selementid'], nei_param[0], nei_param[1], nei_param[2]])
    for dev in host_elem_mapping:
        for link in host_mapping:
            for param in link:
                if param == dev['name']:
                    link.remove(param)
                    link.insert(1, dev['selementid'])
    for index, link in enumerate(host_mapping):
        if link[1].isdigit():
            host_mapping_existing.append(link)
        else:
            host_mapping_not_existing.append(link)
    return host_mapping_existing


def add_links_to_map(connection, sysmapid, links):
    """
    That function adds links to the map created before

    :param connection: authorized connection object
    :param sysmapid: map id
    :param links: needed parameters for the links in the form of list (selementid1, selementid2, label)
    :return: it returns nothing. The result see on the Zabbix map =)
    """
    links_to_add = []
    for link in links:
        links_to_add.append({'selementid1': link[0],
                             'selementid2': link[1],
                             'label': link[2].lower() + link[3].lower()})

    connection.map.update(sysmapid=sysmapid, links=links_to_add)

