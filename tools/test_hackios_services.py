"""Check the adopted HackiOS job recipe without starting any target process."""
import unittest
from hackios_services import console_job


class ConsoleRecipeTest(unittest.TestCase):
    def test_selected_job_retains_policy_and_existing_environment(self):
        job = {'Label': 'com.apple.cfprefsd.xpc.daemon',
               'ProgramArguments': ['/usr/sbin/cfprefsd', 'daemon'],
               'MachServices': {'com.apple.cfprefsd.daemon': True},
               'Disabled': {'#IfFeatureFlagDisabled': 'CoreFoundation/CFPreferencesSystemSession', '#Then': True},
               'LimitLoadToSessionType': 'System', 'RunAtLoad': True,
               'EnvironmentVariables': {'EXISTING': 'retained'}}
        result = console_job(job, oslog=True)
        self.assertNotIn('OS_ACTIVITY_DT_MODE', job['EnvironmentVariables'])
        self.assertEqual(result['EnvironmentVariables'], {'EXISTING': 'retained', 'OS_ACTIVITY_DT_MODE': 'YES'})
        for key in job:
            if key != 'EnvironmentVariables':
                self.assertEqual(result[key], job[key])
        self.assertEqual(result['StandardOutPath'], '/dev/console')
        self.assertEqual(result['StandardErrorPath'], '/dev/console')

    def test_console_does_not_enable_logging_by_default(self):
        result = console_job({'Label': 'other'})
        self.assertNotIn('EnvironmentVariables', result)
        self.assertNotIn('RunAtLoad', result)
        self.assertNotIn('KeepAlive', result)


if __name__ == '__main__':
    unittest.main()
