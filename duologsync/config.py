"""
Definition of the Config class
"""

from datetime import datetime, timedelta
from cerberus import Validator
import yaml
from yaml import YAMLError

DEFAULT_DIRECTORY = '/tmp'
DEFAULT_DAYS_IN_PAST = 180

# How many seconds to wait between API requests
MINIMUM_POLLING_DURATION = 120
VALID_ENDPOINTS = ['adminaction', 'auth', 'telephony']

# Duo credentials used to access a client's logs
DUOCLIENT = {
    'type': 'dict',
    'required': True,
    'schema': {
        'skey': {'type': 'string', 'required': True, 'empty': False},
        'ikey': {'type': 'string', 'required': True, 'empty': False},
        'host': {'type': 'string', 'required': True, 'empty': False}
    }
}

# What types of logs to fetch, how often to fetch, from what point in
# time logs should begin to be fetched
LOGS = {
    'type': 'dict',
    'required': True,
    'schema': {
        'logDir': {'type': 'string', 'empty': False},
        'endpoints': {
            'type': 'dict',
            'required': True,
            'schema': {
                'enabled': {
                    'type': ['string', 'list'],
                    'required': True,
                    'empty': False,
                    'allowed': VALID_ENDPOINTS,
                }
            }
        },
        'polling': {
            'type': 'dict',
            'schema': {
                'duration': {
                    'type': 'number'
                },
                'daysinpast': {'type': 'integer', 'min': 0}
            }
        },
        'checkpointDir': {'type': 'string', 'empty': False}
    }
}

# How and where fetched logs should be sent
TRANSPORT = {
    'type': 'dict',
    'required': True,
    'schema': {
        'protocol': {
            'type': 'string',
            'required': True,
            'oneof': [
                {
                    'allowed': ['TCPSSL'],
                    'dependencies': ['certFileDir', 'certFileName']
                },
                {'allowed': ['TCP', 'UDP']}
            ]
        },
        'host': {'type': 'string', 'required': True, 'empty': False},
        'port': {
            'type': 'integer',
            'min': 0,
            'max': 65535,
            'required': True
        },
        'certFileDir': {'type': 'string', 'empty': False},
        'certFileName': {'type': 'string', 'empty': False}
    }
}

# Whether or not log-specific checkpoint files should be used in the
# case of an error or crash
RECOVER_FROM_CHECKPOINT = {
    'type': 'dict',
    'schema': {
        'enabled': {'type': 'boolean'}
    }
}

# Schema for validating the structure of a config dictionary generated from
# a user-provided YAML file
SCHEMA = {
    'duoclient': DUOCLIENT,
    'logs': LOGS,
    'transport': TRANSPORT,
    'recoverFromCheckpoint': RECOVER_FROM_CHECKPOINT
}

class Config:
    """
    This class is unique in that no instances of it should be created. It is
    used as a wrapper around a Dictionary object named config that is contains
    important values used throughout DuoLogSync. The _config class variable
    should only be accessed through getter and setter methods and should only
    be set once. There are useful methods defined in this class for generating
    a config Dictionary from a YAML file, validating the config against a
    Schema and setting defaults for a config Dictionary when optional fields
    are not given values.
    """

    # Private class variable, should not be accessed directly, only through
    # getter and setter methods
    _config = None

    # Used to ensure that the _config variable is set once and only once
    _config_is_set = False

    @classmethod
    def check_config_is_set(cls):
        """
        Used to check that this Config object is set before trying to access
        or set values
        """
        if cls._config_is_set:
            return

        raise RuntimeError('Cannot access values of config before setting it')

    @classmethod
    def set_config(cls, config):
        """
        Function used to set the config of a Config object once and only once.

        @param config   Dictionary used to set a Config object's 'config'
                        instance variable
        """
        if cls._config_is_set:
            raise RuntimeError('Config object already set. Cannot set Config '
                               'object more than once')

        cls._config = config
        cls._config_is_set = True

    @classmethod
    def get_value(cls, keys):
        """
        Getter for a Config object's 'config' instance variable
        """

        cls.check_config_is_set()
        curr_value = cls._config
        for key in keys:
            curr_value = curr_value.get(key)

            if curr_value is None:
                raise ValueError(f"{key} is an invalid key for this Config")

        return curr_value

    @classmethod
    def get_enabled_endpoints(cls):
        """
        @return the list of log_types for which logs should be fetched
        """

        return cls.get_value(['logs', 'endpoints', 'enabled'])

    @classmethod
    def get_polling_duration(cls):
        """
        @return the seconds to wait before fetching logs from an endpoint
        """

        return cls.get_value(['logs', 'polling', 'duration'])

    @classmethod
    def get_checkpoint_directory(cls):
        """
        @return the directory where log offset checkpoint files are saved
        """

        return cls.get_value(['logs', 'checkpointDir'])

    @classmethod
    def get_ikey(cls):
        """
        @return the ikey used by Duo to identify a customer
        """

        return cls.get_value(['duoclient', 'ikey'])

    @classmethod
    def get_skey(cls):
        """
        @return the skey used by Duo to authenticate access to a customer's logs
        """

        return cls.get_value(['duoclient', 'skey'])

    @classmethod
    def get_host(cls):
        """
        @return the host where a customer's logs are stored
        """

        return cls.get_value(['duoclient', 'host'])

    @classmethod
    def get_recover_log_offset(cls):
        """
        @return boolean indicating if checkpoint files should be used to
                recover log offsets
        """

        return cls.get_value(['recoverFromCheckpoint', 'enabled'])

    @classmethod
    def get_log_directory(cls):
        """
        @return the directory where DuoLogSync's logs should be saved
        """

        return cls.get_value(['logs', 'logDir'])

    @staticmethod
    def create_config(config_filepath):
        """
        Attemp to read the file at config_filepath and generate a config
        Dictionary object based on a defined JSON schema

        @param config_filepath  File from which to generate a config object
        """

        try:
            with open(config_filepath) as config_file:
                # PyYAML gives better error messages for streams than for files
                config_file_data = config_file.read()
                config = yaml.full_load(config_file_data)

        # Will occur when given a bad filepath or a bad file
        except OSError:
            print('An error occurred while opening the config file. Check '
                  'that the filename and filepath are correct')
            # Re-raise exception to be re-handled and for stopping the program
            raise

        # Will occur if the config file does not contain valid YAML
        except YAMLError:
            print('An error occurred while reading the config file. Check '
                  'that the file has valid YAML.')
            # Re-raise exception to be re-handled and for stopping the program
            raise

        # If no exception was raised during the try block, return config
        else:
            return config

    @staticmethod
    def validate_config(config):
        """
        Use a schema and the cerberus library to validate that the given config
        dictionary has a valid structure

        @param config   Dictionary for which to validate the structure
        """

        # Generate a Validator object with the given schema
        schema = Validator(SCHEMA)

        # Config is not a valid structure
        if schema.validate(config) is False:
            raise RuntimeError("While validating the config, the following "
                               f"error(s) occurred: {schema.errors}")

    @staticmethod
    def set_config_defaults(config):
        """
        Check if optional fields within a config are empty. If they are empty
        or if they have a bad value, set those values to a default and log a
        message about the decision to set a default.

        @param config   Config dict for which to set defaults
        """

        # Message format for informing a user that an optional field in their
        # config file was not set and thus a default value is being used
        default_msg = "Config: No value given for %s, using default value of %s"

        if config.get('logs').get('polling') is None:
            config['logs']['polling'] = {}

        if config.get('recoverFromCheckpoint') is None:
            config['recoverFromCheckpoint'] = {}

        if config.get('logs').get('logDir') is None:
            print(default_msg % ('logs.logDir', DEFAULT_DIRECTORY))
            config['logs']['logDir'] = DEFAULT_DIRECTORY

        polling_duration = config.get('logs').get('polling').get('duration')
        if polling_duration is None:
            print(default_msg %
                  ('logs.polling.duration', MINIMUM_POLLING_DURATION))
            config['logs']['polling']['duration'] = MINIMUM_POLLING_DURATION

        elif polling_duration < MINIMUM_POLLING_DURATION:
            print("Config: Value given for logs.polling.duration was too "
                  "low. Set to default value of %s" % MINIMUM_POLLING_DURATION)
            config['logs']['polling']['duration'] = MINIMUM_POLLING_DURATION

        if config.get('logs').get('polling').get('daysinpast') is None:
            print(default_msg %
                  ('logs.polling.daysinpast', DEFAULT_DAYS_IN_PAST))
            config['logs']['polling']['daysinpast'] = DEFAULT_DAYS_IN_PAST

        if config.get('logs').get('checkpointDir') is None:
            print(default_msg % ('logs.checkpointDir', DEFAULT_DIRECTORY))
            config['logs']['checkpointDir'] = DEFAULT_DIRECTORY

        if config.get('recoverFromCheckpoint').get('enabled') is None:
            print(default_msg % ('recoverFromCheckpoint.enabled', False))
            config['recoverFromCheckpoint']['enabled'] = False

        # Add a default offset from which to fetch logs
        # The maximum amount of days in the past that a log may be fetched from
        days_in_past = config['logs']['polling']['daysinpast']

        # Create a timestamp for screening logs that are too old
        default_log_offset = datetime.utcnow() - timedelta(days=days_in_past)
        config['logs']['offset'] = int(default_log_offset.timestamp())