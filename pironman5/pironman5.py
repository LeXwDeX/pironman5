import json
import time
import os
from importlib.resources import files as resource_files

from pm_auto.pm_auto import PMAuto
from pm_auto import __version__ as pm_auto_version
from .logger import create_get_child_logger
from .utils import merge_dict, log_error
from .version import __version__ as pironman5_version
from .variants import NAME, ID, PRODUCT_VERSION, PERIPHERALS, SYSTEM_DEFAULT_CONFIG

get_child_logger = create_get_child_logger('pironman5')
log = get_child_logger('main')
__package_name__ = __name__.split('.')[0]
CONFIG_PATH = str(resource_files(__package_name__).joinpath('config.json'))

PMDashboard = None
try:
    from pm_dashboard.pm_dashboard import PMDashboard
    from pm_dashboard import __version__ as pm_dashboard_version
except ImportError:
    pass

class Pironman5:
    # @log_error
    def __init__(self):
        self.log = get_child_logger('main')
        self.config = {
            'system': SYSTEM_DEFAULT_CONFIG,
        }
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            self.config = self.upgrade_config(config)
            merge_dict(self.config, config)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.config, f, indent=4)

        device_info = {
            'name': NAME,
            'id': ID,
            'peripherals': PERIPHERALS,
            'version': pironman5_version,
        }

        self.log.debug(f"Pironman5 version: {pironman5_version}")
        self.log.debug(f"Variant: {NAME} {PRODUCT_VERSION}")
        self.log.debug(f"PM_Auto version: {pm_auto_version}")
        if PMDashboard is not None:
            self.log.debug(f"PM_Dashboard version: {pm_dashboard_version}")
        self.pm_auto = PMAuto(self.config['system'],
                              peripherals=PERIPHERALS,
                              get_logger=get_child_logger)
        if PMDashboard is None:
            self.pm_dashboard = None
            self.log.warning('PM Dashboard not found skipping')
        else:
            self.pm_dashboard = PMDashboard(device_info=device_info,
                                            database=ID,
                                            spc_enabled=True if 'spc' in PERIPHERALS else False,
                                            config=self.config,
                                            get_logger=get_child_logger)
            self.pm_auto.set_on_state_changed(self.pm_dashboard.update_status)
            self.pm_dashboard.set_on_config_changed(self.update_config)

    @log_error
    def set_debug_level(self, level):
        self.log.setLevel(level)
        self.pm_auto.set_debug_level(level)
        if self.pm_dashboard:
            self.pm_dashboard.set_debug_level(level)

    @log_error
    def upgrade_config(self, config):
        ''' upgrade old config to new config converting 'auto' to'system' '''
        if 'auto' in config:
            return {'system': config['auto']}
        return config

    @log_error
    def update_config(self, config):
        self.pm_auto.update_config(config['system'])
        merge_dict(self.config, config)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.config, f, indent=4)

    @log_error
    @staticmethod
    def update_config_file(config):
        current = None
        with open(CONFIG_PATH, 'r') as f:
            current = json.load(f)
        merge_dict(current, config)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(current, f, indent=4)

    @log_error
    def start(self):
        self.pm_auto.start()
        self.log.info('PMAuto started')
        if self.pm_dashboard:
            self.pm_dashboard.start()
            self.log.info('PmDashboard started')

        # Display GIF instead of system information
        from pm_auto.pm_auto.oled import OLED
        oled = OLED()
        if oled.is_ready():
            gif_path = "/opt/pironman5/mgunnp.gif"
            self.log.info(f"Attempting to display GIF: {gif_path}")
            try:
                oled.display_gif(gif_path)
                self.log.info("GIF displayed successfully.")
            except Exception as e:
                self.log.error(f"Failed to display GIF: {e}")
        else:
            self.log.error("OLED is not ready. Cannot display GIF.")

    @log_error
    def stop(self):
        self.pm_auto.stop()
        if self.pm_dashboard:
            self.pm_dashboard.stop()
