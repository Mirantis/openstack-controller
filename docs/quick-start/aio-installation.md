# All in One Installation

This paragraph provides a guide how to deploy single node deployment with
[k0s](https://docs.k0sproject.io/stable/) based Kubernetes cluster and
openstack deployed by OpenStack controller.

## Prepare VM

For the deployment we will need Virtual Machine with following minimal requirements.

Minimal VM requirements

| Resource | Amount |
| -------- | ------ |
| RAM  | 16Gb       |
| CPU  | 8          |
| DISK | 100Gb      |


## Trigger Deployment

1. Download repository with openstack-controller
  ```bash
  git clone https://github.com/Mirantis/openstack-controller
  ```

2. Trigger deployment
  ```bash
  cd openstack-controller/virtual_lab/
  bash install.sh
  ```
