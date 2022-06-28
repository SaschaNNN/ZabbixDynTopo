import zabbix_interaction
import network_interaction

if __name__ == "__main__":
    zabbix_url = input('Enter url to access Zabbix API (for example https://zabbix.local): ')
    zabbix_user = input('Enter user to access Zabbix API: ')
    zabbix_password = input("Enter Zabbix user's password: ")
    host_groupname = input("Enter Zabbix hosts groupname to build map for: ")
    map_name = input("Enter Zabbix name for future map: ")
    network_user_name = input("Enter network admin user to access switches\\\\routers: ")
    network_user_password = input("Enter network admin user's password: ")
    netowrk_domain = input("Enter network domain (for example .comp.local): ")


    if connected := zabbix_interaction.connect_to_Zabbix(zabbix_url,
                                                         zabbix_user,
                                                         zabbix_password):  # create connection to Zabbix
        discovered_hosts = zabbix_interaction.discovered_zabbix_hosts(connected,  # get hosts from particular group
                                                                      host_groupname)
        map_id, x, y = zabbix_interaction.map_creation(connected,  # create map with mentioned name
                                                       len(discovered_hosts),
                                                       map_name)
        map_added_hosts = zabbix_interaction.add_elements_to_map(connected,  # put on the map discovered hosts
                                                                 discovered_hosts,
                                                                 map_id,
                                                                 x,
                                                                 y)
        hosts_with_elementid = zabbix_interaction.add_elem_id_to_hosts(discovered_hosts,
                                                                       map_added_hosts)
        # add corresponding element ids to discovered hosts
        excess_topology = network_interaction.net_connection(discovered_hosts,
                                                             network_user_name,
                                                             network_user_password,
                                                             netowrk_domain)  # gather neighbor info from network devices
        real_links = zabbix_interaction.topo_links(excess_topology,
                                                   hosts_with_elementid)
        # get from gathered info links needed to add on the map
        zabbix_interaction.add_links_to_map(connected,
                                            map_id,
                                            real_links)  # add links to the map
