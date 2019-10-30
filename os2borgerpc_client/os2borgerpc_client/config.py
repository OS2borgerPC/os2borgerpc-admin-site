import os
import yaml
import sys
import stat

DEFAULT_CONFIG_FILE = "/etc/os2borgerpc/os2borgerpc.conf"

DEBUG = True  # TODO: Get from settings file.


def get_config(key, filename=DEFAULT_CONFIG_FILE):
    """Get value of a known config key."""
    conf = OS2borgerPCConfig(filename)
    return conf.get_value(key)


def has_config(key, filename=DEFAULT_CONFIG_FILE):
    """Return True if config key exists, False otherwise."""
    conf = OS2borgerPCConfig(filename)
    exists = False
    try:
        # TODO: It would be more elegant to determine this without computing
        # the value.
        val = conf.get_value(key)
        exists = True
    except KeyError:
        pass
    return exists


def set_config(key, value, filename=DEFAULT_CONFIG_FILE):
    """Set value of a config key."""
    conf = OS2borgerPCConfig(filename)
    val = conf.set_value(key, value)
    conf.save()


class OS2borgerPCConfig():
    def __init__(self, filename=DEFAULT_CONFIG_FILE):
        """Create new configuration object. Each configuration object is
        defined by its ownership of exactly one configuration file."""
        self.filename = filename
        self.yamldata = {}
        # Do not catch exceptions here, let them pass from load function
        self.load()

    def load(self):
        """Load a configuration - initialize to empty configuration if file
        does not exist."""
        try:
            stream = open(self.filename, "r")
            self.yamldata = yaml.safe_load(stream)
            # safe_load returns None when the file is empty, but we need a dict
            if self.yamldata is None:
                self.yamldata = {}
        except IOError as e:
            if e.errno == 2:
                # File does not exist -> empty YAML dictionary.
                self.yamldata = {}
            else:
                # Something else is wrong, e.g. errno 13 = permission denied.
                # Pass the buck.
                raise

    # When save() creates or updates directories, it masks off the following
    # permission bits, corresponding to g-w o-rwx (0o027)
    MASK = stat.S_IWGRP + stat.S_IROTH + stat.S_IWOTH + stat.S_IXOTH

    def save(self):
        try:
            d = os.path.dirname(self.filename)
            if len(d) > 0:
                if not os.path.exists(d):
                    # Set the umask to make sure that every folder we create
                    # has an appropriately restrictive mode
                    old_mask = os.umask(OS2borgerPCConfig.MASK)
                    try:
                        os.makedirs(d)
                    finally:
                        os.umask(old_mask)
                else:
                    # Set the mode of the existing leaf directory with good
                    # old-fashioned C-style bit twiddling
                    s = os.stat(d)
                    os.chmod(d, s.st_mode & ~OS2borgerPCConfig.MASK)

            # Make sure we overwrite the settings file atomically -- a failed
            # write operation here would essentially unregister this client
            with open(self.filename + ".new", "w") as stream:
                yaml.dump(self.yamldata, stream, default_flow_style=False)
            os.rename(self.filename + ".new", self.filename)
        except IOError as e:
            print("Error opening OS2borgerPCConfig file for writing: ", str(e))
            raise

    def set_value(self, key, value):
        current = self.yamldata

        i = key.find(".")
        while (i != -1):
            subkey = key[:i]
            try:
                current = current[subkey]
            except (KeyError, TypeError):
                current[subkey] = {}
                current = current[subkey]
            key = key[i + 1:]
            i = key.find(".")

        try:
            current[key] = value
        except TypeError:
            current = {}
            current[key] = value

    def get_value(self, key):
        current = self.yamldata
        try:
            i = key.find(".")
            while (i != -1):
                subkey = key[:i]
                current = current[subkey]
                key = key[i + 1:]
                i = key.find(".")
        except:
            raise

        return current[key]

    def remove_key(self, key):
        current = self.yamldata
        try:
            i = key.find(".")
            while (i != -1):
                subkey = key[:i]
                current = current[subkey]
                key = key[i + 1:]
                i = key.find(".")
        except:
            raise

        if key in current:
            del current[key]

    def get_data(self):
        def _get_at(node, prefix):
            for k, v in node.items():
                here = prefix + [k]
                if isinstance(v, dict):
                    yield from _get_at(v, here)
                else:
                    yield (".".join(here), v)
        return dict(_get_at(self.yamldata, []))
