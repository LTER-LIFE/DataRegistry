import unittest

from test.db import init_db, remove_tables


class TestResult(object):
    def startTestRun(self):
        init_db()

    def stopTestRun(self):
        # remove application tables after every test run, so the tables
        # are recreated on the start of every test run (see above)
        remove_tables()


setattr(unittest.TestResult, 'startTestRun', TestResult.startTestRun)
setattr(unittest.TestResult, 'stopTestRun', TestResult.stopTestRun)
