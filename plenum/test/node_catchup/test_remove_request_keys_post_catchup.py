import pytest

from plenum.common.constants import DOMAIN_LEDGER_ID
from plenum.test.delayers import delay_3pc_messages, pDelay, cDelay, ppDelay
from plenum.test.helper import send_reqs_batches_and_get_suff_replies, \
    check_last_ordered_3pc
from plenum.test.node_catchup.helper import ensure_all_nodes_have_same_data
from plenum.test.test_node import getNonPrimaryReplicas, ensureElectionsDone
from plenum.test.view_change.helper import ensure_view_change


@pytest.fixture(scope='module', params=['some', 'all'])
def setup(request, looper, txnPoolNodeSet, client1, wallet1,
          client1Connected):
    slow_node = getNonPrimaryReplicas(txnPoolNodeSet, 0)[1].node
    fast_nodes = [n for n in txnPoolNodeSet if n != slow_node]
    slow_node.nodeIbStasher.delay(pDelay(100, 0))
    slow_node.nodeIbStasher.delay(cDelay(100, 0))
    if request.param == 'all':
        slow_node.nodeIbStasher.delay(ppDelay(100, 0))
    return slow_node, fast_nodes


def test_nodes_removes_request_keys_for_ordered(setup, looper, txnPoolNodeSet,
                                                client1, wallet1):
    """
    A node does not order requests since it is missing some 3PC messages,
    gets them from catchup. It then clears them from its request queues
    """
    slow_node, fast_nodes = setup

    reqs = send_reqs_batches_and_get_suff_replies(
        looper, wallet1, client1, 10, 5)
    ensure_all_nodes_have_same_data(looper, fast_nodes)
    assert slow_node.master_replica.last_ordered_3pc != \
        fast_nodes[0].master_replica.last_ordered_3pc

    def chk(key, nodes, present):
        for node in nodes:
            assert (
                key in node.master_replica.requestQueues[DOMAIN_LEDGER_ID]) == present

    for req in reqs:
        chk(req.key, fast_nodes, False)
        chk(req.key, [slow_node], True)

    ensure_view_change(looper, txnPoolNodeSet)
    ensureElectionsDone(looper, txnPoolNodeSet)

    ensure_all_nodes_have_same_data(looper, txnPoolNodeSet)
    for req in reqs:
        chk(req.key, txnPoolNodeSet, False)