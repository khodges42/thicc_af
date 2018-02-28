# thicc_af
"Thin Provisioning" functionality for EC2 instances using Ansible.

## Introduction
Fun fact, AWS doesn't seem to allow thin provisioning of EC2 drives. This is a pain, because you're paying for the entire drive instead of what you're actually using. 

If this saves you some money, feel free to buy me an orange 1986 BMW M3, like Frank Ocean.

## Setup
Run AWS Credentials on the terminal and set your secret key and so on.

Add the following tags to each EC2 instance you would like to monitor

- (required) "thin" set to "1"
- "thin_threshold_free" set to minimum percentage free space left. Example "0.10"
- "thin_increment_size" set to maximum increment, in gb, to grow drive. Example "10"
- "thin_max_size" set to maximum volume size, in gb. Example "500"

Add hosts to /etc/ansible/hosts, in the following format: hostname.or.ip ansible_user=gorillabiscuits ansible_ssh_private_key_file=/home/falken/.ssh/joshua

## Todo
Need to add the following plays:
- Resize EBS
- Resize OS Partition

Want the following features:
- Correlate mount points w/ ebs volumes
- Email alerting

