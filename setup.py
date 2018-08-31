from setuptools import setup

# Get configuration information from all of the various subpackages.
# See the docstring for setup_helpers.update_package_files for more
# details.


# Add the project-global data

setup(
    name='SpOT',
    version='0.2dev',
    author='Shelbe Timothy',
    author_email='shelbe@lmsal.com',
    packages=['spot'],
    scripts=['bin/Dome_startup.py','bin/Dome_shutdown.py', 'bin/WeatherWatchdog.py'],
    license='MIT'
)