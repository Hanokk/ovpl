""" 
VMPool manages a pool of VMs and the resources available for use by the VMs.
Resources may include RAM, diskspace, IPs, etc.  For now, these resources 
are handled by the platform adapters.  VMPool does this by maintaining a
list of VMs via corresponding VMProxy objects.

"""

__all__ = [
    'VMProxy',
    'VMPool',
    ]

import json
import requests
from exceptions import Exception

import Logging
from State import State

#Globals
CREATE_PATH = "/api/1.0/vm/create"
DESTROY_PATH = "/api/1.0/vm/destroy"


class VMPool:
    """ Manages a pool of VMs or VMProxy's """

    def __init__(self, adapter_ip, adapter_port, vmpool_id=0):
        self.system = State.Instance()
        #self.vms = []       # List of VMProxy objects
        self.vmpool_id = vmpool_id
        self.adapter_ip = adapter_ip
        self.adapter_port = adapter_port

    def create_vm(self, lab_spec):
        # vm_spec is a json string
        # Allocate a vm_id: not required as platform adapter will allocate it.
        # Invoke platform adapter server (POST)

        def construct_state():
            return {
                "lab_spec": lab_spec,
                "vm_info": {
                    "vm_id": vm_id,
                    "vm_ip": vm_ip,
                    "vmm_port": vmm_port
                },
                "vmpool_info": {
                    "vmpool_id": 0,
                    "adapter_ip": self.adapter_ip,
                    "adapter_port": self.adapter_port
                },
                "vm_status": {
                    "last_known_status": None,
                    "last_successful_connection": None,
                    "reconnect_attempts": None,
                    "disk_usage": None,
                    "mem_usage": None
                },
                "lab_history": {
                    "released_by": None,
                    "released_on": None,
                    "destroyed_by": None,
                    "destroyed_on": None
                }
            }
        Logging.LOGGER.debug("VMPool.create_vm()")
        adapter_url = "%s:%s%s" % (self.adapter_ip, self.adapter_port, CREATE_PATH)
        payload = {'lab_spec': json.dumps(lab_spec)}
        try:
            result = requests.post(url=adapter_url, data=payload)
            Logging.LOGGER.debug("Response text from adapter: " + result.text)
            if result.status_code == requests.codes.ok:
                vm_id = result.json()["vm_id"]
                vm_ip = result.json()["vm_ip"]
                vmm_port = result.json()["vmm_port"]
                return construct_state()
            else:
                raise Exception("Error creating VM: " + result.text)
        except Exception, e:
            Logging.LOGGER.error("Error communicating with adapter: " + str(e))
            raise Exception("Error creating VM: " + str(e))

    def destroy_vm(self, vm_id):
        # Invoke platform adapter
        # Delete entry from VMs list
        Logging.LOGGER.debug("VMPool.destroy_vm()")
        adapter_url = "%s:%s%s" % (self.adapter_ip, self.adapter_port, DESTROY_PATH)
        payload = {'vm_id': vm_id}
        try:
            result = requests.post(url=adapter_url, data=payload)
            Logging.LOGGER.debug("Response text from adapter: " + result.text)
            if result.status_code == requests.codes.ok and "Success" in result.text:
                Logging.LOGGER.debug("VMPool.destroy_vm()")
                return True
            else:
                Logging.LOGGER.error("Error destroying vm: " + result.text)
        except Exception, e:
            Logging.LOGGER.error("Error communicating with adapter: " + str(e))

    def save_state(self, lab_id, vm_id):
        for r in self.system.state:
            if r['lab_spec']['lab_id'] == lab_id and r['vm_info']['vm_id'] == vm_id and r['vmpool_info']['vmpool_id'] == self.vmpool_id:
                self.system.state.remove(r)
                self.system.save()
                break

    def destroy_and_save(self, lab_id, vm_id):
        if self.destroy_vm(vm_id):
            self.save_state(lab_id, vm_id)

    def undeploy_lab(self, lab_id):
        Logging.LOGGER.debug("VMPool.undeploy_lab()")
        map(lambda vm_id: self.destroy_and_save(lab_id, vm_id), self.dedicated_vms(lab_id))

    def dedicated_vms(self, lab_id):
        this_lab_vms = set([r['vm_info']['vm_id'] for r in self.system.state if r['lab_spec']['lab_id']==lab_id and r['vmpool_info']['vmpool_id']==self.vmpool_id])
        other_lab_vms = set([r['vm_info']['vm_id'] for r in self.system.state if r['lab_spec']['lab_id']!=lab_id and r['vmpool_info']['vmpool_id']==self.vmpool_id])
        return list(this_lab_vms - other_lab_vms)


if __name__ == "__main__":
    pool = VMPool("http://10.4.12.24", "8000")
    pool.create_vm(None)
