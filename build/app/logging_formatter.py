#!/usr/bin/env python3
import re
import logging

reg=r'[0-9]{9}:[a-zA-Z0-9_-]{35}'

class SensitiveFormatter(logging.Formatter):
    """ Formatter, removes sensitive data from logs """

    @staticmethod
    def _filter(_str):
        return re.sub(reg, r'********', _str)

    def format(self, record):
        original = logging.Formatter.format(self, record)
        return self._filter(original)
