"""Health Check module for Apache service"""

import os
import re
import commands
import urllib2

from socket import *

import utils as health_check_utils
import base
import logging

class ApacheCheck(base.BaseCheck):

    NAME = "Apache Check"
    def run(self):
        if self.dist in ("centos", "redhat", "fedora", "scientific linux"):
            apache_service = 'httpd'
        else:
            apache_service = 'apache2'
        self.check_apache_conf(apache_service)
        print "[Done]"
        self.check_apache_running(apache_service)
        print "[Done]"
        if self.code == 1:
            self.messages.append("[%s]Info: Apache health check has completed. No problems found, all systems go." % self.NAME)
        return (self.code, self.messages)

    def check_apache_conf(self, apache_service):
        """
        Validates if Apache settings.

        :param apache_service  : service type of apache, os dependent. e.g. httpd or apache2
        :type apache_service   : string

        """
        print "Checking Apache Config......",
        conf_err_msg = health_check_utils.check_path(self.NAME, '/etc/%s/conf.d/ods-server.conf' % apache_service)
        if not conf_err_msg == "":
            self._set_status(0, conf_err_msg)

        wsgi_err_msg = health_check_utils.check_path(self.NAME, '/var/www/compass/compass.wsgi')
        if not wsgi_err_msg == "":
            self._set_status(0, wsgi_err_msg)

        return True

    def check_apache_running(self, apache_service):
        """Checks if Apache service is running on port 80"""

        print "Checking Apache service......",
        serv_err_msg = health_check_utils.check_service_running(self.NAME, apache_service)
        if not serv_err_msg == "":
            self._set_status(0, serv_err_msg)
        if 'http' != getservbyport(80):
            self._set_status(0, "[%s]Error: Apache is not listening on port 80." % self.NAME)
        try:
            html = urllib2.urlopen('http://localhost')
            content = html.geturl()
            if "http://localhost/ods/ods.html" != content:
                self._set_status(0, "[%s]Error: Compass web is not redirected by Apache.")
        except:
            self._set_status(0, "[%s]Error: Unable to check localhost:80, Apache is not running or not listening on Port 80" % self.NAME)

        return True
