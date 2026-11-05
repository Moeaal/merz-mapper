import pytest

from merz_sim.topic_checks import CheckReport, expected_topics, FORBIDDEN_IN_SCAN_MODE


def test_expected_topics_per_mode():
    assert '/odom_scan' in expected_topics('scan', False)
    assert '/wheel/odometry' not in expected_topics('scan', False)
    assert '/wheel/odometry' in expected_topics('wheel', True)
    assert '/map' in expected_topics('wheel', False) and '/sign_cam/image_raw' in expected_topics('scan', True)
    assert not set(FORBIDDEN_IN_SCAN_MODE) & set(expected_topics('scan', True))
    with pytest.raises(ValueError):
        expected_topics('gps', True)


def test_report():
    report = CheckReport(received={'/map': 1, '/scan': 3}, transforms={'map->odom': True})
    assert report.passed and report.lines()[-1] == 'RESULT: PASS'
    report.forbidden_publishers['/wheel/odometry'] = 1
    assert not report.passed
    report.forbidden_publishers['/wheel/odometry'] = 0
    report.received['/map'] = 0
    assert not report.passed and report.lines()[-1] == 'RESULT: FAIL'
