import os
try:
    import win32com
except ImportError:
    pass

from scrapy import log
from scrapy.exceptions import NotConfigured
from scrapy.settings import user_conf_file, global_settings

def peril_proceed(display_name):
    response = raw_input("Proceed to start %s? (yes/no, default=no): "
                                           % display_name)
    response = response.strip().lower()
    if response == "yes":
        return True
    else:
        return False

def host_is_local(host):
    return host == "127.0.0.1"

def is_privileged():
    try:
        return os.geteuid() == 0
    except NameError:
        pass
    try:
        return win32com.shell.shell.IsUserAnAdmin()
    except NameError:
        pass
    return True # always assume the worst (for security purposes)

def fail_if_privileged(name, exception_type):
    if is_privileged():
        # Running a server from a privileged account is always dangerous because
        # of the potential that it could be used by an attacker to gain elevated
        # privileges (i.e. privilege escalation).
        log.msg("Refusing to start %s under privileged account" % name,
                level=log.WARNING)
        raise exception_type

def get_effective_security_policy(display_name, setting_name,
                                  display_type, warning_msg):
    # Important: we use global_settings so that a crawler can't inadvertently
    # override the setting (through subclassing CrawlerSettings).
    policy = global_settings.getint(setting_name)
    if policy == 1:
        print
        print "WARNING: About to start %s %s."\
                                       % (display_name, display_type)
        print warning_msg
        print ("Note: to disable this message, set %s\n"
               "in %s.\nSee the docs for further details.")\
               % (setting_name, user_conf_file)
        if peril_proceed(display_name):
            policy = 2
    return policy

def apply_security_policy(display_name, settings_name, host,
                          local_msg, remote_msg,
                          exception_type=NotConfigured):
    fail_if_privileged(display_name, exception_type)
    if host_is_local(host):
        policy = get_effective_security_policy(display_name,
                    'SITE_%s_ALLOW_LOCAL' % settings_name,
                    'for local access only',
                    local_msg)
    else:
        # N.B. The brackets make this more distinctive
        policy = get_effective_security_policy(display_name,
                    'SITE_%s_ALLOW_REMOTE' % settings_name,
                    '(allowing external access)',
                    remote_msg)
    if policy == 0:
        log.msg("Not starting %s - forbidden by site security policy."\
                              % display_name, level=log.WARNING)
    elif policy == 1:
        log.msg("Not starting %s - at user request."\
                              % display_name)

    # Only run if policy == 2.
    # A value of 1 here indicates that the user was prompted and
    # did not type "yes".
    if policy != 2:
        raise exception_type
