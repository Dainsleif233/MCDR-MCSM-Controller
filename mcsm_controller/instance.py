import mcdreforged.api.all  as MCDR
import os
import configparser
import requests
from urllib3.exceptions import InsecureRequestWarning
from mcsm_controller.daemon import get_daemons

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

def get_instances(daemon_name: str, page: int):
    
    daemons = get_daemons()
    if daemons is None:
        return None
    daemon = next((daemon for daemon in daemons if daemon_name == daemon_name), None)
    if daemon is None:
        return None

    url = api_url + '/service/remote_service_instances'
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json; charset=utf-8"
    }
    params = {
        "apikey": api_key,
        "daemonId": daemon['uuid'],
        "page": page,
        "page_size": 10,
        "instance_name": "",
        "status": ""
    }

    try:
        response = requests.get(url, headers=headers, params=params, verify=verify_ssl)
        response.raise_for_status()
        response_data = response.json()['data']
    except requests.exceptions.RequestException as e:
        server.logger.error(e)
        return

    data = {}
    data['total'] = daemon['instance']['total']
    data['maxPage'] = response_data['maxPage']
    data['instances'] = []
    for instance_data in response_data['data']:
        temp = {}
        temp['name'] = instance_data['config']['nickname']
        temp['uuid'] = instance_data['instanceUuid']
        temp['status'] = instance_data['status']
        data['instances'].append(temp)

    return data

def protected_instance(action: str, context: MCDR.CommandContext):
    
    daemon_name = context['daemon_name']
    instance_id = context['instance_id']
    daemons = get_daemons()
    daemon = next((daemon for daemon in daemons if daemon_name == daemon_name), None)
    if daemon is None:
        return server.rtr('mcsm_controller.cmd.list.notfound')

    url = api_url + '/protected_instance/' + action
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json; charset=utf-8"
    }
    params = {
        "apikey": api_key,
        "uuid": instance_id,
        "daemonId": daemon['uuid']
    }

    try:
        response = requests.get(url, headers=headers, params=params, verify=verify_ssl)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        server.logger.error(e)
        return
    
    if action == 'restart':
        return server.rtr('mcsm_controller.cmd.restart').h('!!mcsm kill {} {}'.format(daemon_name, instance_id)).c(MCDR.RAction.suggest_command, '!!mcsm kill {} {}'.format(daemon_name, instance_id))
    elif action == 'stop':
        return server.rtr('mcsm_controller.cmd.stop').h('!!mcsm kill {} {}'.format(daemon_name, instance_id)).c(MCDR.RAction.suggest_command, '!!mcsm kill {} {}'.format(daemon_name, instance_id))
    else:
        return

def list(source: MCDR.CommandSource, context: MCDR.CommandContext):

    reload_config()
    if not source.has_permission(permission):
        source.reply(server.rtr('mcsm_controller.cmd.perm'))
        return
    
    daemon_name = context['daemon_name']
    page = context.get('page', 1)
    instances = get_instances(daemon_name, page)
    if instances is None:
        source.reply(server.rtr('mcsm_controller.cmd.list.notfound'))
        return

    total = instances['total']
    maxPage = instances['maxPage']
    source.reply(server.rtr('mcsm_controller.cmd.list.instance.root', daemon_name, total))

    for instance_data in instances['instances']:
        info = MCDR.RTextList()
        if instance_data['status'] == -1:
            info.append(MCDR.RText('[_] [_] [_]', color=MCDR.RColor.dark_gray), ' ')
            info.append(MCDR.RText(instance_data['name'] + ' ' + instance_data['uuid'], color=MCDR.RColor.dark_gray).h(server.rtr('mcsm_controller.cmd.list.instance.busy')))
        elif instance_data['status'] == 0:
            info.append(MCDR.RText('[+]', color=MCDR.RColor.dark_green).h(server.rtr('mcsm_controller.cmd.list.instance.msg.open')).c(MCDR.RAction.suggest_command, '!!mcsm open {} {}'.format(daemon_name, instance_data['uuid'])), ' ')
            info.append(MCDR.RText('[_] [_]', color=MCDR.RColor.dark_gray), ' ')
            info.append(MCDR.RText(instance_data['name'] + ' ' + instance_data['uuid'], color=MCDR.RColor.white).h(server.rtr('mcsm_controller.cmd.list.instance.stop')))
        elif instance_data['status'] == 1:
            info.append(MCDR.RText('[_] [_]', color=MCDR.RColor.dark_gray), ' ')
            info.append(MCDR.RText('[x]', color=MCDR.RColor.dark_red).h(server.rtr('mcsm_controller.cmd.list.instance.msg.kill')).c(MCDR.RAction.suggest_command, '!!mcsm kill {} {}'.format(daemon_name, instance_data['uuid'])), ' ')
            info.append(MCDR.RText(instance_data['name'] + ' ' + instance_data['uuid'], color=MCDR.RColor.red).h(server.rtr('mcsm_controller.cmd.list.instance.stopping')))
        elif instance_data['status'] == 2:
            info.append(MCDR.RText('[_] [_]', color=MCDR.RColor.dark_gray), ' ')
            info.append(MCDR.RText('[x]', color=MCDR.RColor.dark_red).h(server.rtr('mcsm_controller.cmd.list.instance.msg.kill')).c(MCDR.RAction.suggest_command, '!!mcsm kill {} {}'.format(daemon_name, instance_data['uuid'])), ' ')
            info.append(MCDR.RText(instance_data['name'] + ' ' + instance_data['uuid'], color=MCDR.RColor.dark_green).h(server.rtr('mcsm_controller.cmd.list.instance.openning')))
        elif instance_data['status'] == 3:
            info.append(MCDR.RText('[o]', color=MCDR.RColor.red).h(server.rtr('mcsm_controller.cmd.list.instance.msg.stop')).c(MCDR.RAction.suggest_command, '!!mcsm stop {} {}'.format(daemon_name, instance_data['uuid'])), ' ')
            info.append(MCDR.RText('[r]', color=MCDR.RColor.yellow).h(server.rtr('mcsm_controller.cmd.list.instance.msg.restart')).c(MCDR.RAction.suggest_command, '!!mcsm restart {} {}'.format(daemon_name, instance_data['uuid'])), ' ')
            info.append(MCDR.RText('[x]', color=MCDR.RColor.dark_red).h(server.rtr('mcsm_controller.cmd.list.instance.msg.kill')).c(MCDR.RAction.suggest_command, '!!mcsm kill {} {}'.format(daemon_name, instance_data['uuid'])), ' ')
            info.append(MCDR.RText(instance_data['name'] + ' ' + instance_data['uuid'], color=MCDR.RColor.green).h(server.rtr('mcsm_controller.cmd.list.instance.running')))
        
        source.reply(info)

    button = MCDR.RTextList()
    if page == 1:
        button.append(MCDR.RText('<<', color=MCDR.RColor.dark_gray), ' ')
    else:
        button.append(MCDR.RText('<<', color=MCDR.RColor.white).c(MCDR.RAction.suggest_command, '!!mcsm list {} {}'.format(daemon_name, page - 1)), ' ')
    button.append(MCDR.RText(page, color=MCDR.RColor.yellow), ' ')
    if page == maxPage:
        button.append(MCDR.RText('>>', color=MCDR.RColor.dark_gray))
    else:
        button.append(MCDR.RText('>>', color=MCDR.RColor.white).c(MCDR.RAction.suggest_command, '!!mcsm list {} {}'.format(daemon_name, page + 1)))

    source.reply(button)

def open(source: MCDR.CommandSource, context: MCDR.CommandContext):

    reload_config()
    if not source.has_permission(permission):
        source.reply(server.rtr('mcsm_controller.cmd.perm'))
        return
    
    response = protected_instance('open', context)
    if response is None:
        source.reply(server.rtr('mcsm_controller.cmd.open'))
    else:
        source.reply(response)

def stop(source: MCDR.CommandSource, context: MCDR.CommandContext):

    reload_config()
    if not source.has_permission(permission):
        source.reply(server.rtr('mcsm_controller.cmd.perm'))
        return
    
    response = protected_instance('stop', context)
    source.reply(response)

def restart(source: MCDR.CommandSource, context: MCDR.CommandContext):

    reload_config()
    if not source.has_permission(permission):
        source.reply(server.rtr('mcsm_controller.cmd.perm'))
        return
    
    response = protected_instance('restart', context)
    source.reply(response)

def kill(source: MCDR.CommandSource,context: MCDR.CommandContext):

    reload_config()
    if not source.has_permission(permission):
        source.reply(server.rtr('mcsm_controller.cmd.perm'))
        return
    
    response = protected_instance('kill', context)
    if response is None:
        source.reply(server.rtr('mcsm_controller.cmd.kill'))
    else:
        source.reply(response)