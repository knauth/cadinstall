#!/usr/bin/python3
## This script is used to install tools from vendors
## This script has a complete help menu for each of the supported subcommands
## This script has the following subcommands: install
## This script accepts a dry-run switchcalled "pretend" that will print out the command that would be run, but will not actually run the command
## The script accepts the following global switches that impatcs all print statements: verbose, vv, quiet
## The quiet switch will suppress all output to the console except for errors. It will still print out all output to the log file
## The verbose switch will print out all output to both the console and the log file
## The vv switch will print out all output to both the console and the logfile, but it will also print out the commands that are being run
## The install subcommand is used to install a tool and it takes the following switches: vendor, tool, version, src, sites, group
## The install subcommand will generate a command to rsync the src directory to a global installation area with the specified group
## If the script is NOT being run by the "cadtools" faceless account, it will make a call to a jenkins job to run the command that was generated
## If the script IS being run by the "cadtools" faceless account, it will run the command that was generated
## The script will exit with an error if the source directory does not exist, the destination directory already exists, or the destination directory does not exist
## The script will print out the subcommand help menu if no subcommand is provided
## The script will also exit with an error if an invalid subcommand is provided
## The script will print out the actions it is taking as it is running
## The script will also change the group of the destination directory to the specified group and change the permissions of the destination directory to allow both group and world read access

import os
import sys
import argparse
import logging
import subprocess
import getpass
import pwd
import grp
import socket

# Set up the global variable
global verbose
global vv
global quiet
global pretend
global vendor
global tool
global version
global src
global sitesList
global group

# Define the global variables
user = getpass.getuser()
host = socket.getfqdn()
cadtools_user = 'cadtools'
cadtools_group = 'vendor_tools'

## define a hash for machines per site
siteHash = {
    'aus': 'rv-misc-01.aus2.tenstorrent.com',
    'yyz': 'soc-l-01.yyz2.tenstorrent.com'
}

## define the full path to this script
script = os.path.realpath(__file__)

## define the full path to this script along with all of the arguments used in it's invocation
full_command = ' '.join(sys.argv)

## Set up the logging
log_file = '/tmp/cadinstall.' + user + '.log'
formatter = logging.Formatter('-%(levelname)s- %(asctime)s : %(message)s')

## Logfile handler
file_handler = logging.FileHandler(log_file, mode='w')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Different level possible
console_handler.setFormatter(formatter)

## now set up the message logger
log = logging.getLogger(log_file)
log.setLevel(logging.DEBUG) # Set the minimum log level
log.addHandler(file_handler)
log.addHandler(console_handler)

# Set up the argument parser
parser = argparse.ArgumentParser(description='Install tools from vendors')
parser.add_argument('--verbose', '-v', action='store_true', help='Print all output to the console and the log file')
parser.add_argument('--vv', action='store_true', help='Print all output to the console and the log file, but also print out the commands that are being run')
parser.add_argument('--quiet', '-q', action='store_true', help='Suppress all output to the console except for errors. Print all output to the log file')
parser.add_argument('--pretend', '-p', dest="pretend", action='store_true', help='Print out the command that would be run, but do not actually run the command')
subparsers = parser.add_subparsers(dest='subcommand', help='Subcommands')
install_parser = subparsers.add_parser('install', help='Install a tool')
install_parser.add_argument('--vendor', '-v', dest="vendor", required=True, help='The vendor of the tool')
install_parser.add_argument('--tool', '-t', dest="tool", required=True, help='The tool to install')
install_parser.add_argument('--version', '-ver', dest="version", required=True, help='The version of the tool to install')
install_parser.add_argument('--src', dest="src", required=True, help='The source directory of the tool')
install_parser.add_argument('--sites', type=str, required=False, help='The sites to install the tool to. Valid values: aus, yyz')
install_parser.add_argument('--group', dest="group", default=cadtools_group, help='The group to own the destination directory')
args = parser.parse_args()

if args.sites:
    sitesList = args.sites.split(",")
else:
    sitesList = []
    for site in siteHash:
        sitesList.append(site)

# Set up the logging level
if args.verbose:
    log.setLevel(logging.INFO)
elif args.vv:
    log.setLevel(logging.DEBUG)
elif args.quiet:
    log.setLevel(logging.ERROR)

# Set up the pretend switch
if args.pretend:
    pretend = True
else:
    pretend = False

# Set up the global variables for the rsync command
rsync = '/usr/bin/rsync'
mkdir = '/usr/bin/mkdir'
curl = '/usr/bin/curl'
rsync_options = "-av --chmod=u+rwx,g+rx,o=rx"

# Set up the global variables for the jenkins job
curl_cmd = curl + ' -X POST -L'
jenkins_user = "bswan:11ce74b6c978b1484607c6c9168e085b44"
jenkins_url = 'http://aus-rv-l-7:8081'

# Set up the global variables for the destination directory
#dest = '/tmp/tools_vendor'
dest = '/tools_vendor'
dest_group = 'cadtools'
dest_mode = 2755

def run_command(command):
    log.info("Running command: %s" % command)
    if pretend:
        log.info("Because the '-p' switch was thrown, not actually running command: %s" % command)
    else:
        try:
#            subprocess.check_call(command, shell=True)
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.stdout:
                log.info("%s" % result.stdout.decode('utf-8'))
            if result.stderr:
                log.error("%s" % result.stderr.decode('utf-8'))

        except subprocess.CalledProcessError as e:
            log.error("Error running command: %s" % command)
            log.error("Error message: %s" % e)
            sys.exit(1)

def run_command2(command):
    log.info("Running command: %s" % command)
    if isinstance(command, str):
        log.info("Converting command to a list ...")
        command2 = command.split()
        command = command2
    log.info("Running command: %s" % command)

    if pretend:
        log.info("Because the '-p' switch was thrown, not actually running command: %s" % command)
    else:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while process.poll() is None:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()

            if stdout_line:
                log.info(stdout_line.decode().strip())
            if stderr_line:
                log.error(stderr_line.decode().strip())

            # Read any remaining output
            stdout_remaining = process.stdout.read()
            stderr_remaining = process.stderr.read()

            if stdout_remaining:
                log.info(stdout_remaining.decode().strip())
            if stderr_remaining:
                log.error(stderr_remaining.decode().strip())

            return_code = process.returncode
            log.info("Return code: %s" % return_code)

def check_src(src):
    if not os.path.exists(src):
        log.error("Source directory does not exist: %s" % src)
        sys.exit(1)

def check_dest(dest, host=None):
    if host:
        log.info("Checking %s for %s ..." % (host, dest))
        command = "ls -ltrd " + dest
        ssh = subprocess.Popen(["ssh", "%s" % host, command],
                       shell=False,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        result = ssh.stdout.readlines()
        if result:
            log.error("Destination directory already exists on %s : %s" % (host,dest))
            sys.exit(1)
    else:
        if os.path.exists(dest):
            log.error("Destination directory already exists: %s" % dest)
            sys.exit(1)

def install_tool(vendor, tool, version, src, group, dest_host):
    check_src(src)
    final_dest = "%s/%s/%s/%s" % (dest, vendor, tool, version)

    for site in sitesList:
        dest_host = siteHash[site]
        check_dest(final_dest, dest_host)
    
        log.info("Installing %s/%s/%s to %s ..." % (vendor,tool,version,site))

        command = "%s %s --groupmap=\"*:%s\" --rsync-path=\'%s -p %s && %s\' %s/ %s@%s:%s/" % (rsync, rsync_options, cadtools_group, mkdir, final_dest, rsync, src, cadtools_user, dest_host, final_dest)
        run_command(command)
        #run_command2(command)

        ## Now that one site is done, change the source to the installed site so that we are ensuring all sites are equivalent
        src = final_dest

def main():
    ## show the help menu if no subcommand is provided
    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    log.info("User    : %s" % user)
    log.info("Host    : %s" % host)
    log.info("Cmdline : %s" % full_command)
    log.info("Logfile : %s" % log_file)

    # Set up the global variables for the install subcommand
    vendor = args.vendor
    tool = args.tool
    version = args.version
    src = args.src
    if args.sites:
        sites = args.sites
    else:
        sites = 'all'
    if args.group:
        group = args.group
    else:
        group = cadtools_group

    log.info("Running command: %s" % full_command)
    if user != cadtools_user:
        log.info("Submitting job to jenkins ...")
        ## submit the job to jenkins
        command = "%s --user %s '%s/job/cadinstall/buildWithParameters?token=cadinstall&cadinstall_vendor=%s&cadinstall_tool=%s&cadinstall_version=%s&cadinstall_src=%s'" % (curl_cmd, jenkins_user, jenkins_url, vendor, tool, version, src)
    
        run_command(command)
        sys.exit(0)

    if args.subcommand == 'install':
        install_tool(vendor, tool, version, src, group, host)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()










