from resources.lib import historial as hi

MOVIE = {'kind': 'peliculas', 'tmdb': '1', 'title': 'Gigante', 'fuente': 'F', 'time': 100}


def test_key_tells_movies_and_each_episode_apart():
    assert hi.key(MOVIE) == 'peliculas:1'
    assert hi.key({'kind': 'series', 'tmdb': '9', 'season': 2, 'episode': 5}) == 'series:9:2:5'


def _tracker(pending, now):
    box = {'pending': pending, 'ok': []}

    def take():
        p, box['pending'] = box['pending'], None
        return p
    return hi.Tracker(take, lambda p: box['ok'].append(p['fuente']), lambda: now), box


def test_what_the_assistant_launched_marks_its_source_good():
    tr, box = _tracker(dict(MOVIE), 120)
    assert tr.started()['tmdb'] == '1' and box['ok'] == ['F'] and box['pending'] is None


def test_trailers_and_stale_clicks_mark_nothing():
    tr, box = _tracker(None, 10)
    assert tr.started() is None and box['ok'] == []
    tr, box = _tracker(dict(MOVIE), 100 + hi.PENDING_MAX + 1)
    assert tr.started() is None and box['ok'] == []
