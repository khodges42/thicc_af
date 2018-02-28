import boto3
import os
import json
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase

from tempfile import NamedTemporaryFile

class InstanceCallback(CallbackBase):
    def __init__(self, instance, drive_threshold, increment_size, max_size):
        self.drive_threshold = drive_threshold
        self.instance = instance
        self.increment_size = increment_size
        self.max_size = max_size
        
    def bytes_to_gb(self,by, bsize=1024):
        r = float(by)
        for i in range(3):
            r = r / bsize
        return(r)
        
    def v2_runner_on_ok(self, result, **kwargs):
        for mount in result._result["ansible_facts"]["ansible_mounts"]:
            percent_free = float(mount["size_available"]) / float(mount["size_total"])
            drive_size_gb = self.bytes_to_gb(mount["size_total"])
            if percent_free < self.drive_threshold:
                print mount["mount"] + " is " + str(100-(percent_free*100))[0:2] + "% full on " + self.instance \
                    +". This is above the threshold of " + str(100-(self.drive_threshold*100))[0:2] + "% capacity"

                # Either Increment_Size or as much as possible.
                amount_to_increase = min(self.increment_size, max(0, (self.max_size - drive_size_gb)))
                if (drive_size_gb + amount_to_increase) <= self.max_size:
                    try:
                        self.resize_ebs(self.instance, amount_to_increase)
                        self.resize_os(self.instance)
                    except Exception as e:
                        print e
                else:
                    print "Drive is already at max size"
                        
    def resize_ebs(self, instance, increment_size):
        print instance

    def resize_os(self, host):
        print host


class ResultCallback(CallbackBase):
    def v2_runner_on_ok(self, result, **kwargs):
        for instance in result._result["instances"]:
            if "thin" in instance["tags"] and instance["tags"]["thin"] == '1':

                #If there are settings set in the tags, we grab them, otherwise defaults
                if "thin_threshold_free" in instance["tags"]:
                    drive_threshold = float(instance["tags"]["thin_threshold_free"])
                else:
                    drive_threshold = 0.25
                if "thin_increment_size" in instance["tags"]:
                    increment_size = int(instance["tags"]["thin_increment_size"])
                else:
                    invrement_size = 1 #Change this when we go to prod
                if "thin_max_size" in instance["tags"]:
                    max_size = int(instance["tags"]["thin_max_size"])
                else:
                    max_size = 10 #Change this in prod
                
                instance_id = instance["instance_id"]
                instance_ip = instance["network_interfaces"][0]["association"]["public_ip"]
                instance_callback = InstanceCallback(instance_id, drive_threshold, increment_size, max_size)
                remote_drives =  dict(
                    name = "remote_drives",
                    hosts = "*", #Specify localhost because we will call the host explicitly below
                    gather_facts = 'no',
                    tasks=[
                        dict(action=dict(module='setup', args=dict(filter='ansible_mounts')), register='my_output'),
                    ]
                )
                play = Play().load(remote_drives,variable_manager=variable_manager, loader=loader)
                tq = None
                try:
                        tq = TaskQueueManager(
                            inventory=self.load_temporary_inventory(instance_ip),
                            variable_manager=variable_manager,
                            loader=loader,
                            options=options,
                            passwords=passwords,
                            stdout_callback=instance_callback,
                        )
                        result = tq.run(play)
                finally:
                    if tq is not None:
                        tq.cleanup()

    def find_host_in_inventory(self,host):
        with open(inventory_file) as f:
            for line in f:
                if host in line:
                    return line
        return False
    
    def load_temporary_inventory(self,host):
        host_line = self.find_host_in_inventory(host)
        if (host_line):
            tmpfile = NamedTemporaryFile()
            try:
                tmpfile.write(host_line)
                tmpfile.seek(0)
                tmp_inv = InventoryManager(loader=loader, sources=[tmpfile.name])
            finally:
                tmpfile.close()
            return tmp_inv
                



# Set Ansible Configurations
inventory_file = '/etc/ansible/hosts'
Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check', 'diff'])
loader = DataLoader()
options = Options(connection='ssh', module_path='/path/to/mymodules', forks=100, become=None, become_method=None, become_user=None, check=False,
                  diff=False)
passwords = dict(vault_pass='secret')
results_callback = ResultCallback()

inventory = InventoryManager(loader=loader, sources=[inventory_file])
variable_manager = VariableManager(loader=loader, inventory=inventory)

ec2_instances =  dict(
        name = "ec2_instances",
        hosts = 'localhost',
        gather_facts = 'no',
        tasks=[
            dict(action=dict(module='ec2_instance_facts',), register='my_output'),
        ]
    )

play = Play().load(ec2_instances, variable_manager=variable_manager, loader=loader)
tqm = None
try:
    tqm = TaskQueueManager(
              inventory=inventory,
              variable_manager=variable_manager,
              loader=loader,
              options=options,
              passwords=passwords,
              stdout_callback=results_callback,
          )
    result = tqm.run(play)
finally:
    if tqm is not None:
        tqm.cleanup()
