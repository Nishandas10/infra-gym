"""Check logic that needs no cluster (gym/checks.py)."""
from __future__ import annotations

from gym import checks

HEADER = "GROUP           TOPIC   PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG   CONSUMER-ID  HOST  CLIENT-ID\n"


def test_kafka_lag_sums_partitions():
    text = HEADER + "fraud-detection orders 0 4932 4934 2 c1 /10.0.0.1 c1\nfraud-detection orders 1 10 30 20 c1 /x c1\n"
    assert checks.kafka_lag_status("fraud-detection", text, 50) == (checks.PASS, "consumer group fraud-detection lag 22 (max 50)")


def test_kafka_lag_without_a_committed_offset_is_the_whole_log():
    """kafka-backlog-010 passed with the fault still on: '-' (nothing committed) had counted as lag 0."""
    text = HEADER + "fraud-detection orders 0 - 1414 - consumer-fraud-detection-1 /10.0.0.2 c1\n"
    status, detail = checks.kafka_lag_status("fraud-detection", text, 50)
    assert status == checks.FAIL and "lag 1414" in detail


def test_kafka_lag_ignores_other_groups_and_reports_no_members():
    text = HEADER + "accounting orders 0 1 900 899 a /x a\n\nConsumer group 'fraud-detection' has no active members.\n"
    assert checks.kafka_lag_status("fraud-detection", text, 50)[0] == checks.FAIL
