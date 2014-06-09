import json
import re
import os
import os.path
import subprocess
import shlex
from exceptions import Exception
import requests
import time
import math

import Logging

#GIT_CLONE_LOC = "./lab-repo-cache/"
#LAB_SPEC_LOC = "/scripts/labspec.json"
#TEST_LAB_API_URI = '/api/1.0/test-lab'

class LabSpecInvalid(Exception):
    def __init__(self, msg):
        Exception(self, msg)

def get_lab_reqs(lab_id, lab_src_url, version=None):

    Logging.LOGGER.debug("LabManager: get_lab_reqs():  Invoked from Controller")
    current_file_path = os.path.dirname(os.path.abspath(__file__))
    config_spec = json.loads(open(current_file_path + "/../config/config.json").read())
    GIT_CLONE_LOC =  config_spec["LABMANAGER_CONFIG"]["GIT_CLONE_LOC"]
    LAB_SPEC_LOC =  config_spec["LABMANAGER_CONFIG"]["LAB_SPEC_LOC"]
    Logging.LOGGER.debug("LabManager: GIT_CLONE_LOC = %s" % str(GIT_CLONE_LOC))
    Logging.LOGGER.debug("LabManager: LAB_SPEC_LOC = %s" % str(LAB_SPEC_LOC))

    # sample lab_src_url: git@github.com:vlead/ovpl.git
    def construct_repo_name(lab_id, lab_src_url):
        Logging.LOGGER.debug("LabManager: construct_repo_name()")
        repo = lab_src_url.split('/')[-1]
        repo_name = lab_id + (repo[:-4] if repo[-4:] == ".git" else repo)
        return repo_name

    def repo_exists(repo_name):
        Logging.LOGGER.debug("LabManager: repo_exists()")
        return os.path.isdir(GIT_CLONE_LOC+repo_name)

    def clone_repo(repo_name):

        Logging.LOGGER.debug("LabManager, clone_repo(): git clone %s %s%s" % (lab_src_url, GIT_CLONE_LOC, repo_name))
        git_clone_str = "git clone %s %s%s" % (lab_src_url, GIT_CLONE_LOC, repo_name) # To avoid null at the end
        clone_cmd = shlex.split(git_clone_str.encode('ascii'))
        Logging.LOGGER.debug("LabManager, clone_repo(): clone_cmd = %s" % (clone_cmd))

        try:
            subprocess.check_call(clone_cmd, stdout=Logging.LOG_FD, stderr=Logging.LOG_FD)
        except Exception, e:
            Logging.LOGGER.error("LabManager: clone_repo(): git clone failed: %s %s" % (repo_name, str(e)))
            raise e

    def pull_repo(repo_name):
        Logging.LOGGER.error("LabManager: pull_repo(), pull_cmd = %s" % (GIT_CLONE_LOC + repo_name))
        pull_cmd = "git --git-dir=%s/.git pull" % (GIT_CLONE_LOC + repo_name)
        Logging.LOGGER.debug(pull_cmd)
        try:
            subprocess.check_call(pull_cmd, stdout=Logging.LOG_FD, stderr=Logging.LOG_FD, shell=True)
        except Exception, e:
            Logging.LOGGER.error("LabManager: pull_repo(), git pull failed: %s %s" % (repo_name, str(e)))
            raise e

    def reset_repo(repo_name):
        Logging.LOGGER.error("LabManager: reset_repo(), reset_cmd = %s" % (GIT_CLONE_LOC + repo_name))
        reset_cmd = "git --git-dir=%s/.git reset --hard" % (GIT_CLONE_LOC + repo_name)
        Logging.LOGGER.debug(reset_cmd)
        try:
            subprocess.check_call(reset_cmd, stdout=Logging.LOG_FD, stderr=Logging.LOG_FD, shell=True)
        except Exception, e:
            Logging.LOGGER.error("LabManager: reset_repo(), git reset failed: %s %s" % (repo_name, str(e)))
            raise e

    def checkout_version(repo_name):
        Logging.LOGGER.error("LabManager: checkout_version(), repo_name = %s" % (repo_name))
        if version:
            try:
                checkout_cmd = shlex.split("git --git-dir=%s checkout %s" \
                                    % ((GIT_CLONE_LOC + repo_name), version))
                subprocess.check_call(checkout_cmd, stdout=Logging.LOG_FD, stderr=Logging.LOG_FD)
            except Exception, e:
                Logging.LOGGER.error("git checkout failed for repo %s tag %s: %s" \
                                    % (repo_name, version, str(e)))
                raise e

    def get_lab_spec(repo_name):
        Logging.LOGGER.error("LabManager: get_lab_spec(); repo_name = %s" % (repo_name))
        # Allow no lab spec but not an invalid json as a lab spec
        spec_path = GIT_CLONE_LOC + repo_name + LAB_SPEC_LOC
        if not os.path.exists(spec_path):
            Logging.LOGGER.error("LabManager: get_lab_spec(); Lab spec file not found")
            raise LabSpecInvalid("Lab spec file not found")
        try:
            return json.loads(open(spec_path).read())
        except Exception, e:
            Logging.LOGGER.error("LabManager: get_lab_spec(); Lab spec JSON invalid: " + str(e))
            raise LabSpecInvalid("Lab spec JSON invalid: " + str(e))

    repo_name = construct_repo_name(lab_id, lab_src_url)
    
    if repo_exists(repo_name):
        reset_repo(repo_name)
        pull_repo(repo_name)
    else:
        clone_repo(repo_name)

    checkout_version(repo_name)
    return get_lab_spec(repo_name)
    #vm_spec = json.loads(open("vmspec.json", "r").read())

def test_lab(vmmgr_ip, port, lab_src_url, version=None):
    # make sure VM Manager is running
    # the target VM should have LabActionRunner scripts 
    # VM Manager should do the following?
    # or better it should invoke another script which should
        # clone the repo in the VM
        # get the lab_spec
        # run Lab Action Runner
    Logging.LOGGER.debug("LabManager.test_lab(): vmmgr_ip = %s, port = %s, lab_src_url = %s" % (vmmgr_ip, port, lab_src_url))
    payload = {"lab_src_url": lab_src_url, "version": version}
    current_file_path = os.path.dirname(os.path.abspath(__file__))
    config_spec = json.loads(open(current_file_path + "/../config/config.json").read())
    TEST_LAB_API_URI = config_spec["VMMANAGER_CONFIG"]["TEST_LAB_URI"]
    url = '%s:%s%s' % (vmmgr_ip, port, TEST_LAB_API_URI)
    Logging.LOGGER.debug("LabManager.test_lab(): url = %s, payload = %s" % (url, str(payload)))

    exception_str = ""
    for i in (1,2,4,8,16):
        time.sleep(i)
        try:
            response = requests.post(url=url, data=payload)
            Logging.LOGGER.debug("LabManager.test_lab(): response = %s" % response)
            return (response.status_code is 200, "Success")
        except Exception, e:
            exception_str = str(e)
            attempts = {0:'first', 1:'second', 2:'third', 3:'fourth'}
            Logging.LOGGER.error("LabManager.test_lab(): Error installing lab on VM for the %s attempt with error: %s" % \
                                 (attempts[math.log(i)/math.log(2)], str(e)))
    return (False, exception_str)
    
if __name__ == '__main__':
    (ret_val, ret_str) = test_lab('http://10.2.59.2', '8089', 'git@bitbucket.org:virtuallabs/cse02-programming.git')
    if (ret_val):
        print "Test Successful"
    else:
        print "Test Unsuccessful"


