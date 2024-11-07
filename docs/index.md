# Welcome to OpenStack Controller documentation

## Introduction

The OpenStack Controller is a [Kubernetes operator](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
that implements lifecycle management for OpenStack deployment.

The OpenStack Controller is written in Python using [Kopf](https://github.com/nolar/kopf) as a Python framework to build
Kubernetes operators, and [Pykube](https://pykube.readthedocs.io/en/latest/).

The controller subscribes to changes to OpenStackDeployment [Kubernetes custom resource](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)
and then reacts to these changes by creating, updating, or deleting appropriate resources in Kubernetes.

## Getting Help

* File a bug: [https://github.com/Mirantis/openstack-operator/issues](https://github.com/Mirantis/openstack-operator/issues)

## Developer: 

* Contributing: [https://TODO]()
* Reference Architecture:  [https://TODO]()
