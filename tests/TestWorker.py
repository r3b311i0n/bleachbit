# vim: ts=4:sw=4:expandtab

# BleachBit
# Copyright (C) 2008-2015 Andrew Ziem
# http://bleachbit.sourceforge.net
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Test case for module Worker
"""


import sys
import tempfile
import unittest

sys.path.append('.')
import TestCleaner
from bleachbit import CLI, Command
from bleachbit.Action import ActionProvider
from bleachbit.Worker import *


class RuntimeErrorAction(ActionProvider):

    action_key = 'runtime'

    def __init__(self, action_element):
        self.pathname = action_element.getAttribute('path')

    def get_commands(self):
        # runtime exception, should fail and continue
        def runtime():
            raise RuntimeError('This is a test exception')

        yield Command.Function(None, runtime, 'Test runtime exception')

        # real file, should succeed
        yield Command.Delete(self.pathname)


class WorkerTestCase(unittest.TestCase):

    """Test case for module Worker"""


    def action_test_helper(self, command, special_expected, errors_expected, bytes_expected_posix, count_deleted_posix, bytes_expected_nt, count_deleted_nt):
        ui = CLI.CliCallback()
        (fd, filename) = tempfile.mkstemp(prefix='bleachbit-test-worker')
        os.write(fd, '123')
        os.close(fd)
        self.assert_(os.path.exists(filename))
        astr = '<action command="%s" path="%s"/>' % (command, filename)
        cleaner = TestCleaner.action_to_cleaner(astr)
        backends['test'] = cleaner
        operations = {'test': ['option1']}
        worker = Worker(ui, True, operations)
        run = worker.run()
        while run.next():
            pass
        self.assert_(not os.path.exists(filename),
                     "Path still exists '%s'" % filename)
        self.assertEqual(worker.total_special, special_expected)
        self.assertEqual(worker.total_errors, errors_expected)
        if 'posix' == os.name:
            self.assertEqual(worker.total_bytes, bytes_expected_posix)
            self.assertEqual(worker.total_deleted, count_deleted_posix)
        elif 'nt' == os.name:
            self.assertEqual(worker.total_bytes, bytes_expected_nt)
            self.assertEqual(worker.total_deleted, count_deleted_nt)


    def test_TestRuntimeError(self):
        """Test Worker using Action.RuntimeErrorAction
        The Worker module handles these differently than
        access denied exceptions
        """
        self.action_test_helper('runtime', 0, 1, 4096, 1, 3, 1)

    def test_TestActionProvider(self):
        """Test Worker using Action.TestActionProvider"""
        self.action_test_helper('test', 3, 2, 4096+10+10, 3, 3+3+10+10, 4)

    def test_deep_scan(self):
        """Test for deep scan"""

        # load cleaners from XML
        import bleachbit.CleanerML
        bleachbit.CleanerML.load_cleaners()

        # DeepScan itself is tested elsewhere, so replace it here
        import bleachbit.DeepScan
        SaveDeepScan = bleachbit.DeepScan.DeepScan
        self.scanned = 0
        self_assertequal = self.assertEqual
        self_assert = self.assert_

        def increment_count():
            self.scanned = self.scanned + 1

        class MyDeepScan:

            def add_search(self, dirname, regex):
                self_assertequal(dirname, os.path.expanduser('~'))
                self_assert(
                    regex in ('^Thumbs\\.db$', '^Thumbs\\.db:encryptable$'))

            def scan(self):
                increment_count()
                yield True
        bleachbit.DeepScan.DeepScan = MyDeepScan

        # test
        operations = {'deepscan': ['thumbs_db']}
        ui = CLI.CliCallback()
        worker = Worker(ui, False, operations).run()
        while worker.next():
            pass
        self.assertEqual(1, self.scanned)

        # clean up
        bleachbit.DeepScan.DeepScan = SaveDeepScan

    def test_multiple_options(self):
        """Test one cleaner with two options"""
        ui = CLI.CliCallback()
        (fd, filename1) = tempfile.mkstemp(prefix='bleachbit-test-worker')
        os.close(fd)
        self.assert_(os.path.exists(filename1))
        (fd, filename2) = tempfile.mkstemp(prefix='bleachbit-test-worker')
        os.close(fd)
        self.assert_(os.path.exists(filename2))

        astr1 = '<action command="delete" search="file" path="%s"/>' % filename1
        astr2 = '<action command="delete" search="file" path="%s"/>' % filename2
        cleaner = TestCleaner.actions_to_cleaner([astr1, astr2])
        backends['test'] = cleaner
        operations = {'test': ['option1', 'option2']}
        worker = Worker(ui, True, operations)
        run = worker.run()
        while run.next():
            pass
        self.assert_(not os.path.exists(filename1),
                     "Path still exists '%s'" % filename1)
        self.assert_(not os.path.exists(filename2),
                     "Path still exists '%s'" % filename2)
        self.assertEqual(worker.total_special, 0)
        self.assertEqual(worker.total_errors, 0)
        self.assertEqual(worker.total_deleted, 2)


def suite():
    return unittest.makeSuite(WorkerTestCase)


if __name__ == '__main__':
    unittest.main()
