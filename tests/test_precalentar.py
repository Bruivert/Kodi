from resources.lib import precalentar as pc


def test_targets_movies_first_then_last_episodes_without_repeats():
    got = pc.targets(['10', 10, '11', 'x'], [(5, 2, 7), (6, None, None), (5, 2, 7)])
    assert got == [('peliculas', '10', None, None), ('peliculas', '11', None, None), ('series', '5', 2, 7)]
    assert len(pc.targets([str(i) for i in range(100)], [])) == pc.MAX_PER_NIGHT


def test_once_a_week_per_title():
    t = ('peliculas', '10', None, None)
    record = {pc.key(t): {'time': 1000}}
    assert not pc.due(record, t, 1000 + 3600) and pc.due(record, t, 1000 + pc.AGAIN_AFTER)
    assert pc.due({}, ('series', '5', 2, 7), 0)


def test_last_aired_episode():
    assert pc.last_episode({'last_episode_to_air': {'season_number': 4, 'episode_number': 2}}) == (4, 2)
    assert pc.last_episode({}) is None and pc.last_episode(None) is None


def test_cleanup_after_two_weeks():
    record = {'a': {'time': 0, 'id': 11}, 'b': {'time': pc.KEEP, 'id': 12}, 'c': {'time': 0, 'id': None}}
    assert pc.to_delete(record, pc.KEEP) == [11]
    assert pc.forget(record, [11])['a'] == {'time': 0, 'id': None}
