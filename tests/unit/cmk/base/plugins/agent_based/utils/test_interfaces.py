#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from cmk.base.plugins.agent_based.agent_based_api.v0 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    state,
    type_defs,
)
from cmk.base.plugins.agent_based.utils import interfaces


@pytest.fixture(name="value_store")
def value_store_fixture(monkeypatch):
    value_store: type_defs.ValueStore = {}
    monkeypatch.setattr(interfaces, 'get_value_store', lambda: value_store)
    yield value_store


def _create_interfaces(bandwidth_change, **kwargs):
    return [
        interfaces.finalize_interface(interfaces.PreInterface(*data, **kwargs)) for data in [
            [
                '1', 'lo', '24', '', '1', 266045395, 97385, 0, 0, 0, 0, 266045395, 97385, 0, 0, 0,
                0, 0, 'lo', '\x00\x00\x00\x00\x00\x00'
            ],
            [
                '2', 'docker0', '6', '', '2', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 'docker0',
                '\x02B\x9d\xa42/'
            ],
            [
                '3', 'enp0s31f6', '6', '', '2', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 'enp0s31f6',
                '\xe4\xb9z6\x93\xad'
            ],
            [
                '4', 'enxe4b97ab99f99', '6', '10000000', '2', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                'enxe4b97ab99f99', '\xe4\xb9z\xb9\x9f\x99'
            ],
            [
                '5', 'vboxnet0', '6', '10000000', '1', 0, 0, 0, 0, 0, 0, 20171, 113, 0, 0, 0, 0, 0,
                'vboxnet0', "\n\x00'\x00\x00\x00"
            ],
            [
                '6', 'wlp2s0', '6', '', '1', 346922243 +
                bandwidth_change, 244867, 0, 0, 0, 0, 6570143 +
                4 * bandwidth_change, 55994, 0, 0, 0, 0, 0, 'wlp2s0', 'd]\x86\xe4P/'
            ],
        ]
    ]


def _add_node_name_to_results(results, node_name):
    return [
        Result(
            state=results[0].state,
            summary=results[0].summary.replace(' ', ' on %s: ' % node_name, 1),
        )
    ] + results[1:]


def _add_group_info_to_results(results, members):
    return [
        Result(
            state=state.OK,
            summary='Group Status (up)',
        ),
        Result(
            state=state.OK,
            summary=members,
        )
    ] + results[1:]


DEFAULT_DISCOVERY_PARAMS = type_defs.Parameters(interfaces.DISCOVERY_DEFAULT_PARAMETERS)

SINGLE_SERVICES = [
    Service(item='5', parameters={
        'discovered_state': ['1'],
        'discovered_speed': 10000000
    }),
    Service(item='6', parameters={
        'discovered_state': ['1'],
        'discovered_speed': 0
    }),
]


def test_discovery_ungrouped_all():
    assert list(interfaces.discover_interfaces(
        [DEFAULT_DISCOVERY_PARAMS],
        _create_interfaces(0),
    )) == SINGLE_SERVICES


def test_discovery_ungrouped_one():
    assert list(
        interfaces.discover_interfaces(
            [
                type_defs.Parameters({
                    'matching_conditions': (
                        False,
                        {
                            'match_index': ['5'],
                        },
                    ),
                    'discovery_single': (False, {}),
                }),
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )) == SINGLE_SERVICES[1:]


def test_discovery_ungrouped_off():
    assert list(
        interfaces.discover_interfaces(
            [
                type_defs.Parameters({
                    'matching_conditions': (True, {}),
                    'discovery_single': (False, {}),
                }),
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )) == []


def test_discovery_legacy_parameters():
    assert list(
        interfaces.discover_interfaces(
            [
                type_defs.Parameters({
                    'pad_portnumbers': False,
                    'item_appearance': 'alias',
                    'match_desc': ['enxe4b97ab99f99', 'vboxnet0', 'lo'],
                    'portstates': ['1', '2', '3'],
                    'porttypes': ['6'],
                    'match_alias': ['enxe4b97ab99f99', 'vboxnet0', 'lo'],
                }),
                type_defs.Parameters({
                    'matching_conditions': (True, {}),
                    'discovery_single': (False, {}),
                }),
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )) == [
            Service(
                item='enxe4b97ab99f99',
                parameters={
                    'discovered_state': ['2'],
                    'discovered_speed': 10000000,
                },
                labels=[],
            ),
            Service(
                item='vboxnet0',
                parameters={
                    'discovered_state': ['1'],
                    'discovered_speed': 10000000,
                },
                labels=[],
            ),
        ]


def test_discovery_grouped_simple():
    assert list(
        interfaces.discover_interfaces(
            [
                type_defs.Parameters({
                    'matching_conditions': (True, {}),
                    "grouping": (
                        True,
                        [{
                            'group_name': 'group',
                            'member_appearance': 'index',
                        }],
                    ),
                }),
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )) == SINGLE_SERVICES + [
            Service(
                item='group',
                parameters={
                    'aggregate': {
                        'member_appearance': 'index',
                        'inclusion_condition': {},
                        'exclusion_conditions': [],
                    },
                    'discovered_state': ['1'],
                    'discovered_speed': 20000000,
                },
                labels=[],
            ),
        ]


def test_discovery_grouped_hierarchy():
    assert list(
        interfaces.discover_interfaces(
            [
                type_defs.Parameters({
                    'matching_conditions': (
                        False,
                        {
                            'portstates': ['1', '2'],
                        },
                    ),
                    "grouping": (
                        True,
                        [{
                            'group_name': 'group',
                            'member_appearance': 'alias',
                        }],
                    ),
                }),
                type_defs.Parameters({
                    'matching_conditions': (True, {}),
                    "grouping": (
                        True,
                        [{
                            'group_name': 'group',
                            'member_appearance': 'index',
                        }],
                    ),
                }),
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )) == SINGLE_SERVICES + [
            Service(
                item='group',
                parameters={
                    'aggregate': {
                        'member_appearance': 'alias',
                        'inclusion_condition': {
                            'portstates': ['1', '2']
                        },
                        'exclusion_conditions': [],
                    },
                    'discovered_state': ['1'],
                    'discovered_speed': 20000000,
                },
                labels=[],
            ),
        ]


def test_discovery_grouped_exclusion_condition():
    assert list(
        interfaces.discover_interfaces(
            [
                type_defs.Parameters({
                    'matching_conditions': (
                        False,
                        {
                            'match_desc': ['eth'],
                        },
                    ),
                    "grouping": (
                        False,
                        [],
                    ),
                }),
                type_defs.Parameters({
                    'matching_conditions': (True, {}),
                    "grouping": (
                        True,
                        [{
                            'group_name': 'group',
                            'member_appearance': 'index',
                        }],
                    ),
                }),
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )) == SINGLE_SERVICES + [
            Service(
                item='group',
                parameters={
                    'aggregate': {
                        'member_appearance': 'index',
                        'inclusion_condition': {},
                        'exclusion_conditions': [{
                            'match_desc': ['eth']
                        }],
                    },
                    'discovered_state': ['1'],
                    'discovered_speed': 20000000,
                },
                labels=[],
            ),
        ]


def test_discovery_grouped_empty():
    assert list(
        interfaces.discover_interfaces(
            [
                type_defs.Parameters({
                    'matching_conditions': (
                        False,
                        {
                            'match_desc': ['non_existing'],
                        },
                    ),
                    "grouping": (
                        True,
                        [{
                            'group_name': 'group',
                            'member_appearance': 'index',
                        }],
                    ),
                }),
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )) == SINGLE_SERVICES


def test_discovery_grouped_by_agent():
    ifaces = _create_interfaces(0)
    ifaces[0].group = 'group'
    ifaces[1].group = 'group'
    assert list(interfaces.discover_interfaces(
        [DEFAULT_DISCOVERY_PARAMS],
        ifaces,
    )) == SINGLE_SERVICES + [
        Service(
            item='group',
            parameters={
                'aggregate': {
                    'member_appearance': 'index',
                },
                'discovered_state': ['1'],
                'discovered_speed': 0.0,
            },
            labels=[],
        ),
    ]


def test_discovery_grouped_by_agent_and_in_rules():
    ifaces = _create_interfaces(0)
    ifaces[0].group = 'group'
    ifaces[1].group = 'group'
    assert list(
        interfaces.discover_interfaces(
            [
                type_defs.Parameters({
                    'matching_conditions': (True, {}),
                    "grouping": (
                        True,
                        [{
                            'group_name': 'group',
                            'member_appearance': 'index',
                        }],
                    ),
                }),
                DEFAULT_DISCOVERY_PARAMS,
            ],
            ifaces,
        )) == SINGLE_SERVICES + [
            Service(
                item='group',
                parameters={
                    'aggregate': {
                        'member_appearance': 'index',
                        'inclusion_condition': {},
                        'exclusion_conditions': [],
                    },
                    'discovered_state': ['1'],
                    'discovered_speed': 20000000.0,
                },
                labels=[],
            ),
        ]


ITEM_PARAMS_RESULTS = (
    (
        '5',
        type_defs.Parameters({
            'errors': (0.01, 0.1),
            'speed': 10000000,
            'traffic': [('both', ('upper', ('perc', (5.0, 20.0))))],
            'state': ['1'],
        }),
        [
            Result(state=state.OK, summary='[vboxnet0] (up)'),
            Result(state=state.OK, summary='MAC: 0A:00:27:00:00:00'),
            Result(state=state.OK, summary='10 MBit/s'),
            Metric('in', 0.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
            Metric('inmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('innucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('indisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
            Metric('out', 0.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
            Metric('outmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outnucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outdisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
            Metric('outqlen', 0.0, levels=(None, None), boundaries=(None, None)),
            Result(state=state.OK, summary='In: 0.00 B/s (0.0%)'),
            Result(state=state.OK, summary='Out: 0.00 B/s (0.0%)'),
        ],
    ),
    (
        '6',
        type_defs.Parameters({
            'errors': (0.01, 0.1),
            'speed': 100000000,
            'traffic': [('both', ('upper', ('perc', (5.0, 20.0))))],
            'state': ['1'],
        }),
        [
            Result(state=state.OK, summary='[wlp2s0] (up)'),
            Result(state=state.OK, summary='MAC: 64:5D:86:E4:50:2F'),
            Result(state=state.OK, summary='assuming 100 MBit/s'),
            Metric('in', 800000.0, levels=(625000.0, 2500000.0), boundaries=(0.0, 12500000.0)),
            Metric('inmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('innucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('indisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
            Metric('out', 3200000.0, levels=(625000.0, 2500000.0), boundaries=(0.0, 12500000.0)),
            Metric('outmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outnucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outdisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
            Metric('outqlen', 0.0, levels=(None, None), boundaries=(None, None)),
            Result(state=state.WARN,
                   summary='In: 800 kB/s (warn/crit at 625 kB/s/2.50 MB/s) (6.4%)'),
            Result(state=state.CRIT,
                   summary='Out: 3.20 MB/s (warn/crit at 625 kB/s/2.50 MB/s) (25.6%)'),
        ],
    ),
)


@pytest.mark.parametrize('item, params, result', ITEM_PARAMS_RESULTS)
def test_check_single_interface(value_store, item, params, result):
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0)[int(item) - 1],
                timestamp=0,
            ))
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(4000000)[int(item) - 1],
            timestamp=5,
        )) == result


@pytest.mark.parametrize('item, params, result', [
    (
        ITEM_PARAMS_RESULTS[0][0],
        ITEM_PARAMS_RESULTS[0][1],
        ITEM_PARAMS_RESULTS[0][2][:-2] + [
            Metric('in_avg_5', 0.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
            Result(state=state.OK, summary='In average 5min: 0.00 B/s (0.0%)'),
            Metric('out_avg_5', 0.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
            Result(state=state.OK, summary='Out average 5min: 0.00 B/s (0.0%)'),
        ],
    ),
    (
        ITEM_PARAMS_RESULTS[1][0],
        ITEM_PARAMS_RESULTS[1][1],
        ITEM_PARAMS_RESULTS[1][2][:-2] + [
            Metric('in_avg_5', 800000.0, levels=(625000.0, 2500000.0),
                   boundaries=(0.0, 12500000.0)),
            Result(state=state.WARN,
                   summary='In average 5min: 800 kB/s (warn/crit at 625 kB/s/2.50 MB/s) (6.4%)'),
            Metric(
                'out_avg_5', 3200000.0, levels=(625000.0, 2500000.0), boundaries=(0.0, 12500000.0)),
            Result(state=state.CRIT,
                   summary='Out average 5min: 3.20 MB/s (warn/crit at 625 kB/s/2.50 MB/s) (25.6%)'),
        ],
    ),
])
def test_check_single_interface_averaging(value_store, item, params, result):
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0)[int(item) - 1],
                timestamp=0,
            ))
    assert list(
        interfaces.check_single_interface(
            item,
            type_defs.Parameters({
                **params,
                'average': 5,
            }),
            _create_interfaces(4000000)[int(item) - 1],
            timestamp=5,
        )) == result


@pytest.mark.parametrize('item, params, result', ITEM_PARAMS_RESULTS)
def test_check_single_interface_group(value_store, item, params, result):
    group_members: interfaces.GroupMembers = {
        None: [
            {
                'name': 'vboxnet0',
                'state_name': 'up'
            },
            {
                'name': 'wlp2s0',
                'state_name': 'up'
            },
        ]
    }
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0)[int(item) - 1],
                group_members=group_members,
                timestamp=0,
            ))
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(4000000)[int(item) - 1],
            group_members=group_members,
            timestamp=5,
        )) == _add_group_info_to_results(result, 'Members: [vboxnet0 (up), wlp2s0 (up)]')


@pytest.mark.parametrize('item, params, result', ITEM_PARAMS_RESULTS)
def test_check_single_interface_w_node(value_store, item, params, result):
    node_name = 'node'
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0, node=node_name)[int(item) - 1],
                timestamp=0,
            ))
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(4000000, node=node_name)[int(item) - 1],
            timestamp=5,
        )) == _add_node_name_to_results(result, node_name)


@pytest.mark.parametrize('item, params, result', ITEM_PARAMS_RESULTS)
def test_check_single_interface_group_w_nodes(value_store, item, params, result):
    group_members: interfaces.GroupMembers = {
        'node1': [
            {
                'name': 'vboxnet0',
                'state_name': 'up'
            },
            {
                'name': 'wlp2s0',
                'state_name': 'up'
            },
        ],
        'node2': [
            {
                'name': 'vboxnet0',
                'state_name': 'up'
            },
            {
                'name': 'wlp2s0',
                'state_name': 'up'
            },
        ]
    }
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0)[int(item) - 1],
                group_members=group_members,
                timestamp=0,
            ))
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(4000000)[int(item) - 1],
            group_members=group_members,
            timestamp=5,
        )
    ) == _add_group_info_to_results(
        result,
        'Members: [vboxnet0 (up), wlp2s0 (up) on node node1] [vboxnet0 (up), wlp2s0 (up) on node node2]'
    )


@pytest.mark.parametrize('item, params, result', ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces(value_store, item, params, result):
    with pytest.raises(IgnoreResultsError):
        list(interfaces.check_multiple_interfaces(
            item,
            params,
            _create_interfaces(0),
            timestamp=0,
        ))
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            _create_interfaces(4000000),
            timestamp=5,
        )) == result


def test_check_multiple_interfaces_group_simple(value_store):
    params = type_defs.Parameters({
        'errors': (0.01, 0.1),
        'traffic': [('both', ('upper', ('perc', (5.0, 20.0))))],
        'aggregate': {
            'member_appearance': 'index',
            'inclusion_condition': {},
            'exclusion_conditions': [],
        },
        'discovered_state': ['1'],
        'discovered_speed': 20000000,
        'state': ['8'],
        'speed': 123456,
    })
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                'group',
                params,
                _create_interfaces(0),
                timestamp=0,
            ))
    assert list(
        interfaces.check_multiple_interfaces(
            'group',
            params,
            _create_interfaces(4000000),
            timestamp=5,
        )) == [
            Result(state=state.OK, summary='Group Status (degraded)'),
            Result(state=state.OK,
                   summary='Members: [1 (up), 2 (down), 3 (down), 4 (down), 5 (up), 6 (up)]'),
            Result(state=state.WARN, summary='10 MBit/s (wrong speed, expected: 123 kBit/s)'),
            Metric('in', 800000.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
            Metric('inmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('innucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('indisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
            Metric('out', 3200000.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
            Metric('outmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outnucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outdisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
            Metric('outqlen', 0.0, levels=(None, None), boundaries=(None, None)),
            Result(state=state.CRIT,
                   summary='In: 800 kB/s (warn/crit at 62.5 kB/s/250 kB/s) (64.0%)'),
            Result(state=state.CRIT,
                   summary='Out: 3.20 MB/s (warn/crit at 62.5 kB/s/250 kB/s) (256.0%)'),
        ]


def test_check_multiple_interfaces_group_exclude(value_store):
    params = type_defs.Parameters({
        'errors': (0.01, 0.1),
        'traffic': [('both', ('upper', ('perc', (5.0, 20.0))))],
        'aggregate': {
            'member_appearance': 'index',
            'inclusion_condition': {},
            'exclusion_conditions': [{
                'match_index': ['4', '5']
            }],
        },
        'discovered_state': ['1'],
        'discovered_speed': 20000000,
    })
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                'group',
                params,
                _create_interfaces(0),
                timestamp=0,
            ))
    assert list(
        interfaces.check_multiple_interfaces(
            'group',
            params,
            _create_interfaces(4000000),
            timestamp=5,
        )) == [
            Result(state=state.CRIT,
                   summary='Group Status (degraded)',
                   details='Group Status (degraded)'),
            Result(state=state.OK,
                   summary='Members: [1 (up), 2 (down), 3 (down), 6 (up)]',
                   details='Members: [1 (up), 2 (down), 3 (down), 6 (up)]'),
            Result(state=state.OK, summary='assuming 20 MBit/s', details='assuming 20 MBit/s'),
            Metric('in', 800000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
            Metric('inmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('innucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('indisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
            Metric('out', 3200000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
            Metric('outmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outnucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outdisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
            Metric('outqlen', 0.0, levels=(None, None), boundaries=(None, None)),
            Result(state=state.CRIT,
                   summary='In: 800 kB/s (warn/crit at 125 kB/s/500 kB/s) (32.0%)',
                   details='In: 800 kB/s (warn/crit at 125 kB/s/500 kB/s) (32.0%)'),
            Result(state=state.CRIT,
                   summary='Out: 3.20 MB/s (warn/crit at 125 kB/s/500 kB/s) (128.0%)',
                   details='Out: 3.20 MB/s (warn/crit at 125 kB/s/500 kB/s) (128.0%)'),
        ]


def test_check_multiple_interfaces_group_by_agent(value_store):
    params = type_defs.Parameters({
        'errors': (0.01, 0.1),
        'traffic': [('both', ('upper', ('perc', (5.0, 20.0))))],
        'aggregate': {
            'member_appearance': 'index',
        },
        'discovered_state': ['1'],
        'discovered_speed': 20000000
    })
    with pytest.raises(IgnoreResultsError):
        ifaces = _create_interfaces(0)
        ifaces[3].group = 'group'
        ifaces[5].group = 'group'
        list(interfaces.check_multiple_interfaces(
            'group',
            params,
            ifaces,
            timestamp=0,
        ))

    ifaces = _create_interfaces(4000000)
    ifaces[3].group = 'group'
    ifaces[5].group = 'group'
    assert list(interfaces.check_multiple_interfaces(
        'group',
        params,
        ifaces,
        timestamp=5,
    )) == [
        Result(state=state.CRIT,
               summary='Group Status (degraded)',
               details='Group Status (degraded)'),
        Result(state=state.OK,
               summary='Members: [4 (down), 6 (up)]',
               details='Members: [4 (down), 6 (up)]'),
        Result(state=state.OK, summary='assuming 20 MBit/s', details='assuming 20 MBit/s'),
        Metric('in', 800000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
        Metric('inmcast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('inbcast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('inucast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('innucast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('indisc', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('inerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
        Metric('out', 3200000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
        Metric('outmcast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outbcast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outucast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outnucast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outdisc', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
        Metric('outqlen', 0.0, levels=(None, None), boundaries=(None, None)),
        Result(state=state.CRIT,
               summary='In: 800 kB/s (warn/crit at 125 kB/s/500 kB/s) (32.0%)',
               details='In: 800 kB/s (warn/crit at 125 kB/s/500 kB/s) (32.0%)'),
        Result(state=state.CRIT,
               summary='Out: 3.20 MB/s (warn/crit at 125 kB/s/500 kB/s) (128.0%)',
               details='Out: 3.20 MB/s (warn/crit at 125 kB/s/500 kB/s) (128.0%)'),
    ]


@pytest.mark.parametrize('item, params, result', ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_w_node(value_store, item, params, result):
    node_name = 'node'
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                _create_interfaces(0, node=node_name),
                timestamp=0,
            ))
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            _create_interfaces(4000000, node=node_name),
            timestamp=5,
        )) == _add_node_name_to_results(result, node_name)


@pytest.mark.parametrize('item, params, result', ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_same_item_twice_cluster(value_store, item, params, result):
    node_name_1 = 'node1'
    node_name_2 = 'node2'
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                _create_interfaces(0, node=node_name_1) + _create_interfaces(0, node=node_name_2),
                timestamp=0,
            ))
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            _create_interfaces(4000000, node=node_name_1) +
            _create_interfaces(4000000, node=node_name_2),
            timestamp=5,
        )) == _add_node_name_to_results(result, node_name_1)


def test_check_multiple_interfaces_group_multiple_nodes(value_store):
    params = type_defs.Parameters({
        'errors': (0.01, 0.1),
        'traffic': [('both', ('upper', ('perc', (5.0, 20.0))))],
        'aggregate': {
            'member_appearance': 'index',
            'inclusion_condition': {
                'match_index': ['5', '6']
            },
            'exclusion_conditions': [],
        },
        'discovered_state': ['1'],
        'discovered_speed': 20000000,
    })
    node_names = ['node1', 'node2', 'node3']
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                'group',
                params,
                sum((_create_interfaces(0, node=node_name) for node_name in node_names), []),
                timestamp=0,
            ))
    assert list(
        interfaces.check_multiple_interfaces(
            'group',
            params,
            sum((_create_interfaces(4000000, node=node_name) for node_name in node_names), []),
            timestamp=5,
        )
    ) == [
        Result(state=state.OK, summary='Group Status (up)'),
        Result(
            state=state.OK,
            summary=
            'Members: [5 (up), 6 (up) on node node1] [5 (up), 6 (up) on node node2] [5 (up), 6 (up) on node node3]'
        ),
        Result(state=state.OK, summary='30 MBit/s'),
        Metric('in', 2400000.0, levels=(187500.0, 750000.0), boundaries=(0.0, 3750000.0)),
        Metric('inmcast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('inbcast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('inucast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('innucast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('indisc', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('inerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
        Metric('out', 9600000.0, levels=(187500.0, 750000.0), boundaries=(0.0, 3750000.0)),
        Metric('outmcast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outbcast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outucast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outnucast', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outdisc', 0.0, levels=(None, None), boundaries=(None, None)),
        Metric('outerr', 0.0, levels=(0.01, 0.1), boundaries=(None, None)),
        Metric('outqlen', 0.0, levels=(None, None), boundaries=(None, None)),
        Result(state=state.CRIT, summary='In: 2.40 MB/s (warn/crit at 188 kB/s/750 kB/s) (64.0%)'),
        Result(state=state.CRIT,
               summary='Out: 9.60 MB/s (warn/crit at 188 kB/s/750 kB/s) (256.0%)'),
    ]
