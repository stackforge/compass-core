# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module to delete a given cluster
"""
import logging

from compass.actions import util
from compass.db.api import cluster as cluster_api
from compass.db.api import host as host_api
from compass.db.api import user as user_db
from compass.deployment.deploy_manager import DeployManager
from compass.deployment.utils import constants as const


def delete_cluster(
    cluster_id, host_id_list,
    username=None, delete_underlying_host=False
):
    """Delete cluster.

    :param cluster_id: id of the cluster.
    :type cluster_id: int

    .. note::
        The function should be called out of database session.
    """
    with util.lock('serialized_action', timeout=100) as lock:
        if not lock:
            raise Exception('failed to acquire lock to delete cluster')

        user = user_db.get_user_object(username)

        for host_id in host_id_list:
            cluster_api.update_cluster_host_state(
                user, cluster_id, host_id, state='ERROR'
            )
            host_api.update_host_state(
                user, host_id, state='ERROR'
            )
        cluster_api.update_cluster_state(
            user, cluster_id, state='ERROR'
        )

        cluster_api.update_cluster(
            user, cluster_id, reinstall_distributed_system=True
        )
        for host_id in host_id_list:
            cluster_api.update_cluster_host(
                user, cluster_id, host_id, reinstall_os=True
            )

        cluster_info = util.ActionHelper.get_cluster_info(cluster_id, user)
        adapter_id = cluster_info[const.ADAPTER_ID]

        adapter_info = util.ActionHelper.get_adapter_info(
            adapter_id, cluster_id, user)
        hosts_info = util.ActionHelper.get_hosts_info(
            cluster_id, host_id_list, user)

        logging.debug('adapter info: %s', adapter_info)
        logging.debug('cluster info: %s', cluster_info)
        logging.debug('hosts info: %s', hosts_info)
        deploy_manager = DeployManager(adapter_info, cluster_info, hosts_info)

        deploy_manager.remove_hosts(
            package_only=not delete_underlying_host,
            delete_cluster=True
        )
        util.ActionHelper.delete_cluster(
            cluster_id, host_id_list, user,
            delete_underlying_host
        )


def delete_cluster_host(
    cluster_id, host_id,
    username=None, delete_underlying_host=False
):
    with util.lock('serialized_action', timeout=100) as lock:
        if not lock:
            raise Exception('failed to acquire lock to delete clusterhost')

        user = user_db.get_user_object(username)
        cluster_info = util.ActionHelper.get_cluster_info(cluster_id, user)
        adapter_id = cluster_info[const.ADAPTER_ID]

        adapter_info = util.ActionHelper.get_adapter_info(
            adapter_id, cluster_id, user)
        hosts_info = util.ActionHelper.get_hosts_info(
            cluster_id, [host_id], user)

        deploy_manager = DeployManager(adapter_info, cluster_info, hosts_info)
        logging.debug('Created deploy manager with %s %s %s'
                      % (adapter_info, cluster_info, hosts_info))

        deploy_manager.remove_hosts(
            package_only=not delete_underlying_host,
            delete_cluster=False
        )
        util.ActionHelper.delete_cluster_host(
            cluster_id, host_id, user,
            delete_underlying_host
        )


def delete_host(
    host_id, cluster_id_list, username=None
):
    with util.lock('serialized_action', timeout=100) as lock:
        if not lock:
            raise Exception('failed to acquire lock to delete host')

        user = user_db.get_user_object(username)
        for cluster_id in cluster_id_list:
            cluster_info = util.ActionHelper.get_cluster_info(
                cluster_id, user)
            adapter_id = cluster_info[const.ADAPTER_ID]

            adapter_info = util.ActionHelper.get_adapter_info(
                adapter_id, cluster_id, user)
            hosts_info = util.ActionHelper.get_hosts_info(
                cluster_id, [host_id], user)

            deploy_manager = DeployManager(
                adapter_info, cluster_info, hosts_info)
            logging.debug('Created deploy manager with %s %s %s'
                          % (adapter_info, cluster_info, hosts_info))

            deploy_manager.remove_hosts(
                package_only=True,
                delete_cluster=False
            )

        util.ActionHelper.delete_host(
            host_id, user
        )


ActionHelper = util.ActionHelper
