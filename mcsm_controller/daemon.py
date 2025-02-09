import mcdreforged.api.all  as MCDR
import os
import configparser
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
server = MCDR.ServerInterface.get_instance().as_plugin_server_interface()

def reload_config():

    global api_url, api_key, verify_ssl, permission

    config_ini = os.path.join(server.get_data_folder(), 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_ini)
    if 'MCSM' in config:
        api_url = config['MCSM'].get('API_URL', '')
        api_key = config['MCSM'].get('API_KEY', '')
        verify_ssl = config['MCSM'].getboolean('VERIFY_SSL', False)
    else:
        api_url = ''
        api_key = ''
        verify_ssl = False
    if 'CMD' in config:
        permission = config['CMD'].getint('PERMISSION', 3)
    else:
        permission = 3

def get_daemons():

    reload_config()
    
    url = api_url + '/overview'
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json; charset=utf-8"
    }
    params = {
        "apikey": api_key
    }

    try:
        response = requests.get(url, headers=headers, params=params, verify=verify_ssl)
        response.raise_for_status()
        response_data = response.json()['data']
    except requests.exceptions.RequestException as e:
        server.logger.error(e)
        return
    
    daemon_list = response_data['remote']
    daemons = []
    for daemon_data in daemon_list:
        if not daemon_data['available']:
            continue
        temp = {}
        temp['name'] = daemon_data['remarks'] or daemon_data['ip']
        temp['uuid'] = daemon_data['uuid']
        temp['instance'] = daemon_data['instance']
        daemons.append(temp)
        
    return daemons

def list(source: MCDR.CommandSource):

    reload_config()
    if not source.has_permission(permission):
        source.reply(server.rtr('mcsm_controller.cmd.perm'))
        return
    
    daemons = get_daemons()
        
    source.reply(server.rtr('mcsm_controller.cmd.list.root', len(daemons)))
    for daemon in daemons:
        source.reply(server.rtr('mcsm_controller.cmd.list.daemon', daemon['name'], daemon['instance']['running'], daemon['instance']['total']).h('!!mcsm list {}'.format(daemon['name'])).c(MCDR.RAction.suggest_command, '!!mcsm list {}'.format(daemon['name'])))