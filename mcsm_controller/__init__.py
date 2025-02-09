import mcdreforged.api.all  as MCDR
import os
import configparser
from mcsm_controller import daemon
from mcsm_controller import instance

version = '1.0.0'

def check_config(server: MCDR.PluginServerInterface):

    config_folder = server.get_data_folder()
    config_ini = os.path.join(config_folder, 'config.ini')

    if not os.path.exists(config_folder):
        os.makedirs(config_folder)

    if not os.path.exists(config_ini):
        config = configparser.ConfigParser()
        config['MCSM'] = {}
        config['MCSM']['API_URL'] = ''
        config['MCSM']['API_KEY'] = ''
        config['MCSM']['VERIFY_SSL'] = 'false'
        config['CMD'] = {}
        config['CMD']['PERMISSION'] = '3'
        with open(config_ini, 'w') as configfile:
            config.write(configfile)

def welc(source: MCDR.CommandSource):

    config_folder = source.get_server().as_plugin_server_interface().get_data_folder()
    config_ini = os.path.join(config_folder, 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_ini)

    source.reply(MCDR.RText(source.get_server().rtr('mcsm_controller.cmd.welc'), color=MCDR.RColor.gold).h(version))
    if not source.has_permission(int(config['CMD']['PERMISSION'])):
        return
    source.reply(MCDR.RText(source.get_server().rtr('mcsm_controller.cmd.root'), color=MCDR.RColor.gray).h('!!mcsm list').c(MCDR.RAction.suggest_command, '!!mcsm list'))

def on_load(server: MCDR.PluginServerInterface, prev_module):

    check_config(server)

    builder = MCDR.SimpleCommandBuilder()

    builder.command('!!mcsm', welc)
    builder.command('!!mcsm list', daemon.list)
    builder.command('!!mcsm list <daemon_name>', instance.list)
    builder.command('!!mcsm list <daemon_name> <page>', instance.list)
    builder.command('!!mcsm open <daemon_name> <instance_id>', instance.open)
    builder.command('!!mcsm stop <daemon_name> <instance_id>', instance.stop)
    builder.command('!!mcsm restart <daemon_name> <instance_id>', instance.restart)
    builder.command('!!mcsm kill <daemon_name> <instance_id>', instance.kill)

    builder.arg('daemon_name', MCDR.Text)
    builder.arg('page', MCDR.Integer)
    builder.arg('instance_id', MCDR.Text)

    builder.register(server)