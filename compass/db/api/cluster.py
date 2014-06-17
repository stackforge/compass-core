# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Cluster database operations."""
import logging

from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models
from compass.utils import util


SUPPORTED_FIELDS = [
    'name', 'os_name', 'distributed_system_name', 'owner', 'adapter_id'
]
RESP_FIELDS = [
    'id', 'name', 'os_name', 'os_installed'
    'distributed_system_name', 'distributed_system_installed',
    'owner', 'adapter_id',
    'created_at', 'updated_at'
]
RESP_CONFIG_FIELDS = [
    'os_config',
    'package_config',
    'config_step'
]
RESP_REVIEW_FIELDS = [
    'cluster', 'hosts'
]
RESP_ACTION_FIELDS = [
    'status', 'details'
]
ADDED_FIELDS = ['name', 'adapter_id']
UPDATED_FIELDS = ['name']
UPDATED_CONFIG_FIELDS = [
    'put_os_config', 'put_package_config', 'config_step'
]
UPDATED_CLUSTERHOST_FIELDS = [
    'add_hosts', 'replace_hosts', 'set_hosts'
]
PATCHED_CONFIG_FIELDS = [
    'patched_os_config', 'patched_package_config', 'config_step'
]
RESP_CLUSTERHOST_FIELDS = [
    'id', 'host_id', 'machine_id', 'name', 'cluster_id',
    'mac', 'os_installed', 'distributed_system_installed',
    'os_name', 'distributed_system_name',
    'owner', 'networks', 'cluster_id'
]
RESP_STATE_FIELDS = [
    'id', 'state', 'progress', 'message'
]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_clusters(lister, **filters):
    """List clusters."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_CLUSTERS)
        return [
            cluster.to_dict()
            for cluster in utils.list_db_objects(
                session, models.Cluster, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def get_cluster(getter, cluster_id, **kwargs):
    """Get cluster info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTERS)
        return utils.get_db_object(
            session, models.Cluster, id=cluster_id
        ).to_dict()


def _conditional_exception(cluster, exception_when_not_editable):
    if exception_when_not_editable:
        raise exception.Forbidden(
            'cluster %s is not editable' % cluster.name
        )
    else:
        return False


def is_cluster_editable(
    session, cluster, user,
    reinstall_distributed_system_set=False,
    exception_when_not_editable=True
):
    with session.begin(subtransactions=True):
        if reinstall_distributed_system_set:
            if cluster.state.state == 'INSTALLING':
                return _conditional_exception(
                    cluster, exception_when_not_editable
                )
        elif not cluster.reinstall_distributed_system:
            return _conditional_exception(
                cluster, exception_when_not_editable
            )
        if not user.is_admin and cluster.creator_id != user.id:
            return _conditional_exception(
                cluster, exception_when_not_editable
            )
    return True


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(ADDED_FIELDS)
def add_cluster(creator, name, adapter_id, **kwargs):
    """Create a cluster."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, creator, permission.PERMISSION_ADD_CLUSTER)
        cluster = utils.add_db_object(
            session, models.Cluster, True,
            name, adapter_id=adapter_id, creator_id=creator.id, **kwargs
        )
        return cluster.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(UPDATED_FIELDS)
def update_cluster(updater, cluster_id, **kwargs):
    """Update a cluster."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTER)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(
            session, cluster, updater,
            reinstall_distributed_system_set=(
                kwargs.get('reinstall_distributed_system', False)
            )
        )
        utils.update_db_object(session, cluster, **kwargs)
        return cluster.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def del_cluster(deleter, cluster_id, **kwargs):
    """Delete a cluster."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_CLUSTER)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, deleter)
        utils.del_db_object(session, cluster)
        return cluster.to_dict()


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters([])
def get_cluster_config(getter, cluster_id, **kwargs):
    """Get cluster config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTER_CONFIG)
        return utils.get_db_object(
            session, models.Cluster, id=cluster_id
        ).to_dict()


def _update_cluster_config(updater, cluster_id, **kwargs):
    """Update a cluster config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTER_CONFIG)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, updater)
        utils.update_db_object(
            session, cluster, config_validated=False, **kwargs
        )
        os_config = cluster.os_config
        if os_config:
            metadata_api.validate_os_config(
                os_config, cluster.adapter_id
            )
        package_config = cluster.package_config
        if package_config:
            metadata_api.validate_package_config(
                package_config, cluster.adapter_id
            )
        return cluster.to_dict()


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters(UPDATED_CONFIG_FIELDS)
def update_cluster_config(updater, cluster_id, **kwargs):
    return _update_cluster_config(updater, cluster_id, **kwargs)


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters(PATCHED_CONFIG_FIELDS)
def patch_cluster_config(updater, cluster_id, **kwargs):
    return _update_cluster_config(updater, cluster_id, **kwargs)


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters([])
def del_cluster_config(deleter, cluster_id):
    """Delete a cluster config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_CLUSTER_CONFIG)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, deleter)
        utils.update_db_object(
            session, cluster, os_config={},
            package_config={}, config_validated=False
        )
        return cluster.to_dict()


def _add_host(session, cluster, machine_id, machine_attrs):
    from compass.db.api import host as host_api
    with session.begin(subtransactions=True):
        host = utils.get_db_object(
            session, models.Host, False, id=machine_id
        )
        if host:
            if host_api.is_host_editable(
                session, host, cluster.creator,
                reinstall_os_set=machine_attrs.get('reinstall_os', False),
                exception_when_not_editable=False
            ):
                utils.update_db_object(
                    session, host, adapter=cluster.adapter.os_adapter,
                    **machine_attrs
                )
            else:
                logging.info('host %s is not editable', host.name)
        else:
            utils.add_db_object(
                session, models.Host, machine_id,
                os=cluster.os,
                adapter=cluster.adapter.os_adapter,
                creator=cluster.creator,
                **machine_attrs
            )


def _add_clusterhosts(session, cluster, machines):
    from compass.db.api import host as host_api
    with session.begin(subtransactions=True):
        for machine_id, machine_attrs in machines.items():
            _add_host(session, cluster, machine_id, machine_attrs)
            utils.add_db_object(
                session, models.ClusterHost, False, cluster.id, machine_id
            )


def _remove_clusterhosts(session, cluster, hosts):
    with session.begin(subtransactions=True):
        for host_id in hosts:
            utils.del_db_objects(
                session, models.ClusterHost,
                cluster_id=cluster.id, host_id=host_id
            )


def _set_clusterhosts(session, cluster, machines):
    with session.begin(subtransactions=True):
        utils.del_db_objects(
            session, models.ClusterHost,
            cluster_id=cluster.id
        )
        for machine_id, machine_attrs in machines.items():
            _add_host(session, cluster, machine_id, machine_attrs)
            utils.add_db_object(
                session, models.ClusterHost,
                True, cluster.id, machine_id
            )


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters([])
def get_clusterhosts(getter, cluster_id, **kwargs):
    """Get cluster host info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTERHOSTS)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        return [clusterhost.to_dict() for clusterhost in cluster.clusterhosts]


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters(UPDATED_CLUSTERHOST_FIELDS)
def update_clusterhosts(
    updater, cluster_id, add_hosts={}, set_hosts=None,
    remove_hosts=[]
):
    """Get subnet info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_UPDATE_CLUSTER_HOSTS)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, updater)
        if remove_hosts:
            _remove_clusterhosts(session, cluster, remove_hosts)
        if add_hosts:
            _add_clusterhosts(session, cluster, add_hosts)
        if set_hosts is not None:
            _set_clusterhosts(session, cluster, set_hosts)
        return [host.to_dict() for host in cluster.clusterhosts]


@utils.wrap_to_dict(RESP_REVIEW_FIELDS)
@utils.supported_filters([])
def review_cluster(reviewer, cluster_id):
    """review cluster."""
    from compass.db.api import host as host_api
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, reviewer, permission.PERMISSION_REVIEW_CLUSTER)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, reviewer)
        os_config = cluster.os_config
        if os_config:
            metadata_api.validate_os_config(
                os_config, cluster.apdater_id, True
            )
            for clusterhost in cluster.clusterhosts:
                host = clusterhost.host
                if not host_api.is_cluster_editable(
                    session, host, reviewer, False
                ):
                    logging.info(
                        'ignore update host %s config '
                        'since it is not editable' % host.name
                    )
                    continue
                host_os_config = host.os_config
                deployed_os_config = util.merge_dict(
                    os_config, host_os_config
                )
                metadata_api.validate_os_config(
                    deployed_os_config, host.apdater_id, True
                )
                host.deployed_os_config = deployed_os_config
                host.config_validated = True
        package_config = cluster.package_config
        if package_config:
            metadata_api.validate_package_config(
                package_config, cluster.adapter_id, True
            )
            for clusterhost in cluster.clusterhosts:
                clusterhost_package_config = clusterhost.package_config
                deployed_package_config = util.mrege_dict(
                    package_config, clusterhost_package_config
                )
                metadata_api.validate_os_config(
                    deployed_package_config,
                    cluster.apdater_id, True
                )
                clusterhost.deployed_package_config = deployed_package_config
                clusterhost.config_validated = True
        cluster.config_validated = True
        return {
            'cluster': cluster.to_dict(),
            'clusterhosts': [
                clusterhost.to_dict()
                for clusterhost in cluster.clusterhosts
            ]
        }


@utils.wrap_to_dict(RESP_ACTION_FIELDS)
@utils.supported_filters([])
def deploy_cluster(deployer, cluster_id, clusterhosts=[], **kwargs):
    """deploy cluster."""
    from compass.tasks import client as celery_client
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deployer, permission.PERMISSION_DEPLOY_CLUSTER)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, deployer)
        celery_client.celery.send_task(
            'compass.tasks.deploy',
            (cluster_id, clusterhosts)
        )
        return {
            'status': 'deploy action sent',
            'details': {
            }
        }


@utils.wrap_to_dict(RESP_STATE_FIELDS)
@utils.supported_filters([])
def get_cluster_state(getter, cluster_id, **kwargs):
    """Get cluster state info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_GET_CLUSTER_STATE)
        return utils.get_db_object(
            session, models.Cluster, id=cluster_id
        ).state_dict()
